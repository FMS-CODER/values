package ming.valuesjava.service;

import java.util.List;

import ming.valuesjava.dto.AssistantChatRequest;
import ming.valuesjava.dto.CitationDto;
import ming.valuesjava.dto.MessageDto;
import ming.valuesjava.dto.PageResult;

/** AI 消息持久化与历史查询。 */
public interface MessageService {

    MessageDto saveUser(long conversationId, String content);

    MessageDto saveAssistant(long conversationId, String content, List<CitationDto> citations,
                             String mode, String status);

    PageResult<MessageDto> list(long conversationId, int page, int size);

    List<AssistantChatRequest.AssistantMessage> recentHistory(long conversationId, int limit);
}