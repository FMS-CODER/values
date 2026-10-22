package ming.valuesjava.service.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpStatus;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import ming.valuesjava.common.ApiException;
import ming.valuesjava.dto.ConversationDto;
import ming.valuesjava.dto.PageResult;
import ming.valuesjava.entity.AiConversation;
import ming.valuesjava.repository.ConversationRepository;

/**
 * 会话归属与分页边界。
 * 归属校验放在 service 而不是 controller：任何调用方（包括以后新增的接口）
 * 都必须经过同一处 403 判断，不能依赖某个 controller 记得传 userId。
 */
class ConversationServiceImplTest {

    private final ConversationRepository repository = mock(ConversationRepository.class);
    private final ConversationServiceImpl service = new ConversationServiceImpl(repository);

    @Test
    void create_usesDefaultTitleWhenBlank() {
        when(repository.insert(anyString(), anyString())).thenAnswer(invocation -> {
            AiConversation entity = conversation(1L, invocation.getArgument(0), invocation.getArgument(1));
            return entity;
        });

        ConversationDto dto = service.create(null, "   ");

        assertThat(dto.title()).isEqualTo("新对话");
        assertThat(dto.id()).isEqualTo(1L);
    }

    @Test
    void create_trimsTitleAndUserId() {
        when(repository.insert(anyString(), anyString())).thenAnswer(invocation ->
                conversation(2L, invocation.getArgument(0), invocation.getArgument(1)));

        service.create("  user-1  ", "  西兰花的热量  ");

        ArgumentCaptor<String> userId = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<String> title = ArgumentCaptor.forClass(String.class);
        verify(repository).insert(userId.capture(), title.capture());
        assertThat(userId.getValue()).isEqualTo("user-1");
        assertThat(title.getValue()).isEqualTo("西兰花的热量");
    }

    @Test
    void create_truncatesTitleToColumnLimit() {
        when(repository.insert(anyString(), anyString())).thenAnswer(invocation ->
                conversation(3L, invocation.getArgument(0), invocation.getArgument(1)));

        service.create("user-1", "营".repeat(200));

        ArgumentCaptor<String> title = ArgumentCaptor.forClass(String.class);
        verify(repository).insert(anyString(), title.capture());
        assertThat(title.getValue()).hasSize(120);
    }

    @Test
    void list_clampsPageAndSize() {
        Page<AiConversation> page = new Page<>(1, 100);
        page.setRecords(List.of(conversation(1L, "user-1", "会话")));
        page.setTotal(1);
        when(repository.findPage("user-1", 1, 100)).thenReturn(page);

        PageResult<ConversationDto> result = service.list("user-1", 0, 1000);

        assertThat(result.page()).isEqualTo(1);
        assertThat(result.size()).isEqualTo(100);
        assertThat(result.total()).isEqualTo(1);
        assertThat(result.items()).hasSize(1);
    }

    @Test
    void requireOwned_rejectsMissingConversation() {
        when(repository.findById(9L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.requireOwned(9L, "user-1"))
                .isInstanceOfSatisfying(ApiException.class,
                        ex -> assertThat(ex.getStatus()).isEqualTo(HttpStatus.NOT_FOUND));
    }

    @Test
    void requireOwned_rejectsAnotherUsersConversation() {
        when(repository.findById(5L)).thenReturn(Optional.of(conversation(5L, "user-2", "别人的会话")));

        assertThatThrownBy(() -> service.requireOwned(5L, "user-1"))
                .isInstanceOfSatisfying(ApiException.class,
                        ex -> assertThat(ex.getStatus()).isEqualTo(HttpStatus.FORBIDDEN));
    }

    @Test
    void delete_onlyRemovesOwnedConversation() {
        when(repository.findById(5L)).thenReturn(Optional.of(conversation(5L, "user-1", "我的会话")));

        service.delete(5L, "user-1");

        verify(repository).delete(5L, "user-1");
    }

    @Test
    void delete_doesNotTouchRepositoryWhenNotOwned() {
        when(repository.findById(5L)).thenReturn(Optional.of(conversation(5L, "user-2", "别人的会话")));

        assertThatThrownBy(() -> service.delete(5L, "user-1"))
                .isInstanceOf(ApiException.class);

        verify(repository, never()).delete(5L, "user-1");
    }

    @Test
    void normalizeUserId_fallsBackToLocalUser() {
        assertThat(ConversationServiceImpl.normalizeUserId(null)).isEqualTo("local-user");
        assertThat(ConversationServiceImpl.normalizeUserId("   ")).isEqualTo("local-user");
        assertThat(ConversationServiceImpl.normalizeUserId("  abc  ")).isEqualTo("abc");
        assertThat(ConversationServiceImpl.normalizeUserId("x".repeat(80))).hasSize(64);
    }

    @Test
    void rename_trimsTitle() {
        service.rename(5L, "  西兰花的热量  ");

        verify(repository).rename(5L, "西兰花的热量");
    }

    @Test
    void rename_fallsBackToDefaultWhenBlank() {
        service.rename(5L, "   ");

        verify(repository).rename(5L, "新对话");
    }

    private static AiConversation conversation(long id, String userId, String title) {
        AiConversation entity = new AiConversation();
        entity.setId(id);
        entity.setUserId(userId);
        entity.setTitle(title);
        entity.setCreatedAt(LocalDateTime.now());
        entity.setUpdatedAt(LocalDateTime.now());
        return entity;
    }
}