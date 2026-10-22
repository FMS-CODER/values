package ming.valuesjava.service.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.LocalDateTime;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;

import ming.valuesjava.dto.AssistantChatRequest;
import ming.valuesjava.dto.CitationDto;
import ming.valuesjava.dto.MessageDto;
import ming.valuesjava.dto.PageResult;
import ming.valuesjava.entity.AiMessage;
import ming.valuesjava.repository.MessageRepository;

/**
 * 消息持久化的两处关键约定：
 * 1. 引用以 JSON 存在 citations_json，读取失败不能让整个历史接口失败；
 * 2. 查询按 id 倒序取最新一页，返回前必须翻转成正序，否则前端会倒着渲染。
 */
class MessageServiceImplTest {

    private final MessageRepository repository = mock(MessageRepository.class);
    private final MessageServiceImpl service = new MessageServiceImpl(repository, new ObjectMapper());

    @Test
    void saveAssistant_serializesCitations() {
        when(repository.insert(anyLong(), anyString(), anyString(), anyString(), anyString(), anyString()))
                .thenAnswer(invocation -> message(
                        10L,
                        invocation.getArgument(1),
                        invocation.getArgument(2),
                        invocation.getArgument(3),
                        invocation.getArgument(4)));

        service.saveAssistant(7L, "回答", List.of(citation("nutrient:PROTEIN")), "rag", "done");

        ArgumentCaptor<String> json = ArgumentCaptor.forClass(String.class);
        verify(repository).insert(eq(7L), eq("assistant"), eq("回答"), json.capture(), eq("rag"), eq("done"));
        assertThat(json.getValue())
                .contains("\"documentId\":\"nutrient:PROTEIN\"")
                .contains("\"kind\":\"knowledge\"");
    }

    @Test
    void saveAssistant_skipsJsonWhenNoCitations() {
        when(repository.insert(anyLong(), anyString(), anyString(), any(), anyString(), anyString()))
                .thenAnswer(invocation -> message(
                        11L,
                        invocation.getArgument(1),
                        invocation.getArgument(2),
                        invocation.getArgument(3),
                        invocation.getArgument(4)));

        service.saveAssistant(7L, "回答", List.of(), "database", "done");

        verify(repository).insert(eq(7L), eq("assistant"), eq("回答"), eq(null), eq("database"), eq("done"));
    }

    @Test
    void list_reversesDescendingRowsIntoChronologicalOrder() {
        Page<AiMessage> page = new Page<>(1, 20);
        page.setRecords(List.of(
                message(3L, "assistant", "第二条回答", null, "database"),
                message(2L, "user", "第二问", null, null),
                message(1L, "user", "第一问", null, null)));
        page.setTotal(3);
        when(repository.findPage(7L, 1, 20)).thenReturn(page);

        PageResult<MessageDto> result = service.list(7L, 1, 20);

        assertThat(result.items()).extracting(MessageDto::id).containsExactly(1L, 2L, 3L);
    }

    @Test
    void list_clampsSizeToTwoHundred() {
        Page<AiMessage> page = new Page<>(1, 200);
        page.setRecords(List.of());
        page.setTotal(0);
        when(repository.findPage(7L, 1, 200)).thenReturn(page);

        PageResult<MessageDto> result = service.list(7L, 1, 5000);

        assertThat(result.size()).isEqualTo(200);
        verify(repository).findPage(7L, 1, 200);
    }

    @Test
    void list_degradesToEmptyCitationsWhenJsonIsBroken() {
        Page<AiMessage> page = new Page<>(1, 20);
        page.setRecords(List.of(message(1L, "assistant", "回答", "{broken", "rag")));
        page.setTotal(1);
        when(repository.findPage(7L, 1, 20)).thenReturn(page);

        PageResult<MessageDto> result = service.list(7L, 1, 20);

        assertThat(result.items().get(0).citations()).isEmpty();
    }

    @Test
    void list_parsesStoredCitations() {
        Page<AiMessage> page = new Page<>(1, 20);
        page.setRecords(List.of(message(1L, "assistant", "回答",
                "[{\"documentId\":\"nutrient:PROTEIN\",\"title\":\"蛋白质\",\"source\":\"测试\","
                        + "\"url\":\"\",\"snippet\":\"内容\",\"score\":0.8,\"kind\":\"knowledge\","
                        + "\"reviewStatus\":\"approved\",\"version\":\"1\"}]",
                "rag")));
        page.setTotal(1);
        when(repository.findPage(7L, 1, 20)).thenReturn(page);

        PageResult<MessageDto> result = service.list(7L, 1, 20);

        assertThat(result.items().get(0).citations())
                .extracting(CitationDto::documentId)
                .containsExactly("nutrient:PROTEIN");
    }

    @Test
    void recentHistory_skipsInvalidRolesAndBlankContent() {
        when(repository.findRecent(7L, 20)).thenReturn(List.of(
                message(1L, "user", "问题", null, null),
                message(2L, "system", "系统提示", null, null),
                message(3L, "assistant", "   ", null, null),
                message(4L, "assistant", "回答", null, "database")));

        List<AssistantChatRequest.AssistantMessage> history = service.recentHistory(7L, 20);

        assertThat(history).extracting(AssistantChatRequest.AssistantMessage::content)
                .containsExactly("问题", "回答");
    }

    private static CitationDto citation(String documentId) {
        return new CitationDto(documentId, "蛋白质的营养作用", "测试来源", "", "内容",
                0.9, "knowledge", "approved", "1");
    }

    private static AiMessage message(long id, String role, String content, String citationsJson, String mode) {
        AiMessage entity = new AiMessage();
        entity.setId(id);
        entity.setConversationId(7L);
        entity.setRole(role);
        entity.setContent(content);
        entity.setCitationsJson(citationsJson);
        entity.setMode(mode);
        entity.setStatus("done");
        entity.setCreatedAt(LocalDateTime.now());
        return entity;
    }
}