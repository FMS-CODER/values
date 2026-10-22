package ming.valuesjava.service.impl;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import ming.valuesjava.common.ApiException;
import ming.valuesjava.dto.AssistantChatRequest;
import ming.valuesjava.dto.CitationDto;
import ming.valuesjava.dto.MessageDto;
import ming.valuesjava.dto.PageResult;
import ming.valuesjava.entity.AiMessage;
import ming.valuesjava.repository.MessageRepository;
import ming.valuesjava.service.MessageService;

@Service
public class MessageServiceImpl implements MessageService {

    private static final Logger log = LoggerFactory.getLogger(MessageServiceImpl.class);
    private static final int MAX_PAGE_SIZE = 200;

    private final MessageRepository repository;
    private final ObjectMapper objectMapper;

    public MessageServiceImpl(MessageRepository repository, ObjectMapper objectMapper) {
        this.repository = repository;
        this.objectMapper = objectMapper;
    }

    @Override
    public MessageDto saveUser(long conversationId, String content) {
        AiMessage entity = repository.insert(conversationId, "user", content, null, null, "done");
        return toDto(entity);
    }

    @Override
    public MessageDto saveAssistant(long conversationId, String content, List<CitationDto> citations,
                                    String mode, String status) {
        AiMessage entity = repository.insert(
                conversationId,
                "assistant",
                content,
                writeCitations(citations),
                mode,
                status);
        return toDto(entity);
    }

    @Override
    public PageResult<MessageDto> list(long conversationId, int page, int size) {
        int safePage = Math.max(1, page);
        int safeSize = Math.min(MAX_PAGE_SIZE, Math.max(1, size));
        Page<AiMessage> result = repository.findPage(conversationId, safePage, safeSize);

        // 查询按 id 倒序拿到最新一页，展示时翻转成时间正序
        List<AiMessage> records = new ArrayList<>(result.getRecords());
        Collections.reverse(records);

        List<MessageDto> items = new ArrayList<>();
        for (AiMessage entity : records) {
            items.add(toDto(entity));
        }
        return PageResult.of(items, result.getTotal(), safePage, safeSize);
    }

    @Override
    public List<AssistantChatRequest.AssistantMessage> recentHistory(long conversationId, int limit) {
        List<AssistantChatRequest.AssistantMessage> history = new ArrayList<>();
        for (AiMessage entity : repository.findRecent(conversationId, limit)) {
            if (!"user".equals(entity.getRole()) && !"assistant".equals(entity.getRole())) {
                continue;
            }
            String content = entity.getContent();
            if (content == null || content.isBlank()) {
                continue;
            }
            history.add(new AssistantChatRequest.AssistantMessage(entity.getRole(), content));
        }
        return history;
    }

    private MessageDto toDto(AiMessage entity) {
        return new MessageDto(
                entity.getId(),
                entity.getRole(),
                entity.getContent(),
                readCitations(entity.getCitationsJson()),
                entity.getMode(),
                entity.getStatus(),
                entity.getCreatedAt());
    }

    private String writeCitations(List<CitationDto> citations) {
        if (citations == null || citations.isEmpty()) {
            return null;
        }
        try {
            return objectMapper.writeValueAsString(citations);
        } catch (JsonProcessingException ex) {
            throw ApiException.internal("引用信息序列化失败");
        }
    }

    private List<CitationDto> readCitations(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<CitationDto>>() {
            });
        } catch (JsonProcessingException ex) {
            log.warn("消息引用 JSON 解析失败：{}", ex.getMessage());
            return List.of();
        }
    }
}