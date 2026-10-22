package ming.valuesjava.service;

import ming.valuesjava.dto.AssistantChatRequest;
import ming.valuesjava.dto.AssistantChatResponse;

/** AI 问答入口：会话校验、消息落库、调用 Python 与降级。 */
public interface AssistantService {

    AssistantChatResponse chat(AssistantChatRequest request, String userId);
}