package ming.valuesjava.repository;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import org.springframework.stereotype.Repository;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import ming.valuesjava.entity.AiMessage;
import ming.valuesjava.mapper.AiMessageMapper;

/** AI 消息数据访问。 */
@Repository
public class MessageRepository {

    private final AiMessageMapper mapper;

    public MessageRepository(AiMessageMapper mapper) {
        this.mapper = mapper;
    }

    public AiMessage insert(long conversationId, String role, String content,
                            String citationsJson, String mode, String status) {
        AiMessage entity = new AiMessage();
        entity.setConversationId(conversationId);
        entity.setRole(role);
        entity.setContent(content);
        entity.setCitationsJson(citationsJson);
        entity.setMode(mode);
        entity.setStatus(status);
        entity.setCreatedAt(LocalDateTime.now());
        mapper.insert(entity);
        return mapper.selectById(entity.getId());
    }

    public Page<AiMessage> findPage(long conversationId, int page, int size) {
        return mapper.selectPage(
                new Page<>(page, size),
                new LambdaQueryWrapper<AiMessage>()
                        .eq(AiMessage::getConversationId, conversationId)
                        .orderByDesc(AiMessage::getId));
    }

    /** 最近 N 条，按时间正序返回，便于直接作为模型历史。 */
    public List<AiMessage> findRecent(long conversationId, int limit) {
        List<AiMessage> rows = mapper.selectList(
                new LambdaQueryWrapper<AiMessage>()
                        .eq(AiMessage::getConversationId, conversationId)
                        .orderByDesc(AiMessage::getId)
                        .last("LIMIT " + Math.max(1, limit)));
        List<AiMessage> result = new ArrayList<>(rows);
        Collections.reverse(result);
        return result;
    }
}