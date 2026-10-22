package ming.valuesjava.repository;

import java.time.LocalDateTime;
import java.util.Optional;

import org.springframework.stereotype.Repository;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import ming.valuesjava.entity.AiConversation;
import ming.valuesjava.mapper.AiConversationMapper;

/** AI 会话数据访问。 */
@Repository
public class ConversationRepository {

    private final AiConversationMapper mapper;

    public ConversationRepository(AiConversationMapper mapper) {
        this.mapper = mapper;
    }

    public AiConversation insert(String userId, String title) {
        AiConversation entity = new AiConversation();
        entity.setUserId(userId);
        entity.setTitle(title);
        mapper.insert(entity);
        // 时间字段由数据库默认值生成，回读一次拿到 createdAt/updatedAt
        return mapper.selectById(entity.getId());
    }

    public Optional<AiConversation> findById(long id) {
        return Optional.ofNullable(mapper.selectById(id));
    }

    public Page<AiConversation> findPage(String userId, int page, int size) {
        return mapper.selectPage(
                new Page<>(page, size),
                new LambdaQueryWrapper<AiConversation>()
                        .eq(AiConversation::getUserId, userId)
                        .orderByDesc(AiConversation::getUpdatedAt)
                        .orderByDesc(AiConversation::getId));
    }

    public int touch(long id) {
        AiConversation entity = new AiConversation();
        entity.setId(id);
        entity.setUpdatedAt(LocalDateTime.now());
        return mapper.updateById(entity);
    }

    public int rename(long id, String title) {
        AiConversation entity = new AiConversation();
        entity.setId(id);
        entity.setTitle(title);
        entity.setUpdatedAt(LocalDateTime.now());
        return mapper.updateById(entity);
    }

    public int delete(long id, String userId) {
        return mapper.delete(new LambdaQueryWrapper<AiConversation>()
                .eq(AiConversation::getId, id)
                .eq(AiConversation::getUserId, userId));
    }
}