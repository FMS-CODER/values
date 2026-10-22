package ming.valuesjava.service;

import ming.valuesjava.dto.ConversationDto;
import ming.valuesjava.dto.PageResult;

/** AI 会话管理。 */
public interface ConversationService {

    /** 显式新建会话时的默认标题；首条消息落库后会被替换为消息摘要。 */
    String DEFAULT_TITLE = "新对话";

    ConversationDto create(String userId, String title);

    PageResult<ConversationDto> list(String userId, int page, int size);

    void delete(long id, String userId);

    /** 校验归属并返回会话；不存在 404，不属于当前用户 403。 */
    ConversationDto requireOwned(long id, String userId);

    /** 重命名会话；标题为空或超长时按列表展示规则归一化。 */
    void rename(long id, String title);

    void touch(long id);
}