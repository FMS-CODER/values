package ming.valuesjava.service.impl;

import java.util.ArrayList;
import java.util.List;

import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import ming.valuesjava.common.ApiException;
import ming.valuesjava.dto.ConversationDto;
import ming.valuesjava.dto.PageResult;
import ming.valuesjava.entity.AiConversation;
import ming.valuesjava.repository.ConversationRepository;
import ming.valuesjava.service.ConversationService;

@Service
public class ConversationServiceImpl implements ConversationService {

    private static final int MAX_TITLE_LENGTH = 120;
    private static final int MAX_PAGE_SIZE = 100;

    private final ConversationRepository repository;

    public ConversationServiceImpl(ConversationRepository repository) {
        this.repository = repository;
    }

    @Override
    public ConversationDto create(String userId, String title) {
        String normalized = normalizeTitle(title);
        return toDto(repository.insert(normalizeUserId(userId), normalized));
    }

    @Override
    public PageResult<ConversationDto> list(String userId, int page, int size) {
        int safePage = Math.max(1, page);
        int safeSize = Math.min(MAX_PAGE_SIZE, Math.max(1, size));
        Page<AiConversation> result = repository.findPage(normalizeUserId(userId), safePage, safeSize);

        List<ConversationDto> items = new ArrayList<>();
        for (AiConversation entity : result.getRecords()) {
            items.add(toDto(entity));
        }
        return PageResult.of(items, result.getTotal(), safePage, safeSize);
    }

    @Override
    public void delete(long id, String userId) {
        requireOwnedEntity(id, userId);
        repository.delete(id, normalizeUserId(userId));
    }

    @Override
    public ConversationDto requireOwned(long id, String userId) {
        return toDto(requireOwnedEntity(id, userId));
    }

    @Override
    public void touch(long id) {
        repository.touch(id);
    }

    @Override
    public void rename(long id, String title) {
        repository.rename(id, normalizeTitle(title));
    }

    private AiConversation requireOwnedEntity(long id, String userId) {
        AiConversation entity = repository.findById(id)
                .orElseThrow(() -> ApiException.notFound("会话不存在：" + id));
        if (!entity.getUserId().equals(normalizeUserId(userId))) {
            throw ApiException.forbidden("无权访问该会话");
        }
        return entity;
    }

    private static ConversationDto toDto(AiConversation entity) {
        return new ConversationDto(
                entity.getId(),
                entity.getTitle(),
                entity.getCreatedAt(),
                entity.getUpdatedAt());
    }

    static String normalizeUserId(String userId) {
        String trimmed = userId == null ? "" : userId.trim();
        if (trimmed.isEmpty()) {
            return "local-user";
        }
        return trimmed.length() > 64 ? trimmed.substring(0, 64) : trimmed;
    }

    private static String normalizeTitle(String title) {
        String trimmed = title == null ? "" : title.trim();
        if (trimmed.isEmpty()) {
            return DEFAULT_TITLE;
        }
        return trimmed.length() > MAX_TITLE_LENGTH ? trimmed.substring(0, MAX_TITLE_LENGTH) : trimmed;
    }
}