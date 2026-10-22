package ming.valuesjava.service.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.stream.IntStream;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpStatus;

import ming.valuesjava.common.ApiException;
import ming.valuesjava.dto.AssistantChatRequest;
import ming.valuesjava.dto.AssistantChatResponse;
import ming.valuesjava.dto.ConversationDto;
import ming.valuesjava.dto.MessageDto;
import ming.valuesjava.service.ConversationService;
import ming.valuesjava.service.MessageService;

/**
 * 旧接口兼容与降级：
 * - 不带 conversationId 的请求必须自动建会话，并仍然返回旧字段 reply/mode/suggestions；
 * - Python 不可用时保存占位回答，而不是把异常抛给前端。
 */
class AssistantServiceImplTest {

    private final ConversationService conversationService = mock(ConversationService.class);
    private final MessageService messageService = mock(MessageService.class);
    private final AssistantServiceImpl service =
            new AssistantServiceImpl(conversationService, messageService, "http://127.0.0.1:1");

    @Test
    void chat_rejectsBlankMessage() {
        assertThatThrownBy(() -> service.chat(new AssistantChatRequest("   ", null, null), "user-1"))
                .isInstanceOfSatisfying(ApiException.class,
                        ex -> assertThat(ex.getStatus()).isEqualTo(HttpStatus.BAD_REQUEST));
    }

    @Test
    void chat_rejectsTooLongMessage() {
        String message = "营".repeat(1001);

        assertThatThrownBy(() -> service.chat(new AssistantChatRequest(message, null, null), "user-1"))
                .isInstanceOf(ApiException.class)
                .hasMessageContaining("1000");
    }

    @Test
    void chat_rejectsTooManyHistoryItems() {
        List<AssistantChatRequest.AssistantMessage> history = IntStream.range(0, 21)
                .mapToObj(index -> new AssistantChatRequest.AssistantMessage("user", "第 " + index + " 条"))
                .toList();

        assertThatThrownBy(() -> service.chat(new AssistantChatRequest("问题", history, null), "user-1"))
                .isInstanceOf(ApiException.class)
                .hasMessageContaining("20");
    }

    @Test
    void chat_rejectsNonPositiveConversationId() {
        assertThatThrownBy(() -> service.chat(new AssistantChatRequest("问题", null, 0L), "user-1"))
                .isInstanceOf(ApiException.class)
                .hasMessageContaining("conversationId");
    }

    @Test
    void chat_withoutConversationIdCreatesOneAndFallsBackWhenPythonIsDown() {
        when(conversationService.create(eq("user-1"), anyString()))
                .thenReturn(new ConversationDto(7L, "西兰花的热量", null, null));
        when(messageService.recentHistory(7L, 20)).thenReturn(List.of());
        when(messageService.saveAssistant(anyLong(), anyString(), anyList(), eq("placeholder"), eq("done")))
                .thenReturn(new MessageDto(11L, "assistant", "占位", List.of(), "placeholder", "done", null));

        AssistantChatResponse response = service.chat(
                new AssistantChatRequest("西兰花的热量", null, null), "user-1");

        assertThat(response.conversationId()).isEqualTo(7L);
        assertThat(response.assistantMessageId()).isEqualTo(11L);
        assertThat(response.mode()).isEqualTo("placeholder");
        assertThat(response.reply()).contains("Python AI 服务");
        verify(messageService).saveUser(7L, "西兰花的热量");
    }

    @Test
    void chat_truncatesLongMessageForConversationTitle() {
        when(conversationService.create(eq("user-1"), anyString()))
                .thenReturn(new ConversationDto(8L, "标题", null, null));
        when(messageService.recentHistory(8L, 20)).thenReturn(List.of());
        when(messageService.saveAssistant(anyLong(), anyString(), anyList(), anyString(), anyString()))
                .thenReturn(new MessageDto(12L, "assistant", "占位", List.of(), "placeholder", "done", null));

        service.chat(new AssistantChatRequest("营".repeat(80), null, null), "user-1");

        ArgumentCaptor<String> title = ArgumentCaptor.forClass(String.class);
        verify(conversationService).create(eq("user-1"), title.capture());
        assertThat(title.getValue()).hasSize(61).endsWith("…");
    }

    @Test
    void chat_renamesDefaultTitleOnFirstMessage() {
        when(conversationService.requireOwned(9L, "user-1"))
                .thenReturn(new ConversationDto(9L, "新对话", null, null));
        when(messageService.recentHistory(9L, 20)).thenReturn(List.of());
        when(messageService.saveAssistant(anyLong(), anyString(), anyList(), anyString(), anyString()))
                .thenReturn(new MessageDto(14L, "assistant", "占位", List.of(), "placeholder", "done", null));

        service.chat(new AssistantChatRequest("维生素 C 有哪些营养作用？", null, 9L), "user-1");

        verify(conversationService).rename(9L, "维生素 C 有哪些营养作用？");
    }

    @Test
    void chat_keepsCustomConversationTitle() {
        when(conversationService.requireOwned(5L, "user-1"))
                .thenReturn(new ConversationDto(5L, "已有会话", null, null));
        when(messageService.recentHistory(5L, 20)).thenReturn(List.of());
        when(messageService.saveAssistant(anyLong(), anyString(), anyList(), anyString(), anyString()))
                .thenReturn(new MessageDto(13L, "assistant", "占位", List.of(), "placeholder", "done", null));

        service.chat(new AssistantChatRequest("继续问", null, 5L), "user-1");

        verify(conversationService, never()).rename(anyLong(), anyString());
    }

    @Test
    void chat_withExistingConversationSkipsCreation() {
        when(conversationService.requireOwned(5L, "user-1"))
                .thenReturn(new ConversationDto(5L, "已有会话", null, null));
        when(messageService.recentHistory(5L, 20)).thenReturn(List.of(
                new AssistantChatRequest.AssistantMessage("user", "上一轮问题")));
        when(messageService.saveAssistant(anyLong(), anyString(), anyList(), anyString(), anyString()))
                .thenReturn(new MessageDto(13L, "assistant", "占位", List.of(), "placeholder", "done", null));

        AssistantChatResponse response = service.chat(
                new AssistantChatRequest("继续问", null, 5L), "user-1");

        assertThat(response.conversationId()).isEqualTo(5L);
        verify(conversationService, never()).create(anyString(), anyString());
        verify(messageService).saveUser(5L, "继续问");
    }
}