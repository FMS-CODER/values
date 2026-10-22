package ming.valuesjava.service.impl;

import java.util.ArrayList;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import ming.valuesjava.common.ApiException;
import ming.valuesjava.dto.AssistantChatRequest;
import ming.valuesjava.dto.AssistantChatResponse;
import ming.valuesjava.dto.CitationDto;
import ming.valuesjava.dto.ConversationDto;
import ming.valuesjava.dto.MessageDto;
import ming.valuesjava.dto.PythonChatResponse;
import ming.valuesjava.service.AssistantService;
import ming.valuesjava.service.ConversationService;
import ming.valuesjava.service.MessageService;

@Service
public class AssistantServiceImpl implements AssistantService {

    private static final Logger log = LoggerFactory.getLogger(AssistantServiceImpl.class);

    private static final int MAX_MESSAGE_LENGTH = 1000;
    private static final int MAX_HISTORY_SIZE = 20;
    private static final int HISTORY_LOAD_SIZE = 20;

    private static final List<String> SUGGESTIONS = List.of(
            "西兰花有哪些营养亮点？",
            "高蛋白的食物有哪些？",
            "维生素 C 有哪些营养作用？");

    private static final String PLACEHOLDER_REPLY = """
            AI 营养服务暂时不可用。

            请确认 Python AI 服务已启动（默认 http://127.0.0.1:8000），然后再试一次。
            你也可以先回到首页，查看每种食物每 100g 的营养成分与营养亮点。""";

    private final ConversationService conversationService;
    private final MessageService messageService;
    private final RestClient pythonClient;

    public AssistantServiceImpl(
            ConversationService conversationService,
            MessageService messageService,
            @Value("${app.assistant.python-base-url:http://127.0.0.1:8000}") String pythonBaseUrl) {
        this.conversationService = conversationService;
        this.messageService = messageService;

        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(2_000);
        requestFactory.setReadTimeout(60_000);

        this.pythonClient = RestClient.builder()
                .baseUrl(pythonBaseUrl)
                .requestFactory(requestFactory)
                .build();
    }

    @Override
    public AssistantChatResponse chat(AssistantChatRequest request, String userId) {
        String message = validateAndNormalize(request);
        String normalizedUserId = ConversationServiceImpl.normalizeUserId(userId);

        ConversationDto conversation = request.conversationId() == null
                ? conversationService.create(normalizedUserId, titleFromMessage(message))
                : conversationService.requireOwned(request.conversationId(), normalizedUserId);

        List<AssistantChatRequest.AssistantMessage> history =
                messageService.recentHistory(conversation.id(), HISTORY_LOAD_SIZE);
        if (history.isEmpty() && request.history() != null) {
            history = sanitizeHistory(request.history());
        }

        messageService.saveUser(conversation.id(), message);
        if (ConversationService.DEFAULT_TITLE.equals(conversation.title())) {
            // 显式新建的空会话先落默认标题，首条消息到达后再生成可识别的摘要
            conversationService.rename(conversation.id(), titleFromMessage(message));
        }

        PythonChatResponse python = callPython(message, history, conversation.id());
        String reply;
        String mode;
        String intent;
        List<CitationDto> citations;
        if (python == null || python.reply() == null || python.reply().isBlank()) {
            reply = PLACEHOLDER_REPLY;
            mode = "placeholder";
            intent = "general";
            citations = List.of();
        } else {
            reply = python.reply();
            mode = python.mode() == null ? "database" : python.mode();
            intent = python.intent() == null ? "general" : python.intent();
            citations = python.citations() == null ? List.of() : python.citations();
        }

        MessageDto assistant = messageService.saveAssistant(
                conversation.id(), reply, citations, mode, "done");
        conversationService.touch(conversation.id());

        return new AssistantChatResponse(
                reply,
                mode,
                SUGGESTIONS,
                citations,
                conversation.id(),
                assistant.id(),
                intent);
    }

    private PythonChatResponse callPython(String message,
                                          List<AssistantChatRequest.AssistantMessage> history,
                                          long conversationId) {
        try {
            return pythonClient.post()
                    .uri("/api/assistant/chat")
                    .body(new AssistantChatRequest(message, history, conversationId))
                    .retrieve()
                    .body(PythonChatResponse.class);
        } catch (RestClientException ex) {
            log.warn("调用 Python AI 服务失败，使用占位回复：{}", ex.getMessage());
            return null;
        }
    }

    private static String validateAndNormalize(AssistantChatRequest request) {
        if (request == null) {
            throw ApiException.badRequest("请求体不能为空");
        }
        String message = request.message() == null ? "" : request.message().trim();
        if (message.isEmpty()) {
            throw ApiException.badRequest("message 不能为空");
        }
        if (message.length() > MAX_MESSAGE_LENGTH) {
            throw ApiException.badRequest("message 长度不能超过 " + MAX_MESSAGE_LENGTH);
        }
        if (request.history() != null && request.history().size() > MAX_HISTORY_SIZE) {
            throw ApiException.badRequest("history 最多 " + MAX_HISTORY_SIZE + " 条");
        }
        if (request.conversationId() != null && request.conversationId() <= 0) {
            throw ApiException.badRequest("conversationId 必须为正整数");
        }
        return message;
    }

    private static List<AssistantChatRequest.AssistantMessage> sanitizeHistory(
            List<AssistantChatRequest.AssistantMessage> history) {
        List<AssistantChatRequest.AssistantMessage> result = new ArrayList<>();
        for (AssistantChatRequest.AssistantMessage item : history) {
            if (item == null) {
                continue;
            }
            String role = item.role();
            String content = item.content() == null ? "" : item.content().trim();
            if (!"user".equals(role) && !"assistant".equals(role)) {
                continue;
            }
            if (content.isEmpty()) {
                continue;
            }
            result.add(new AssistantChatRequest.AssistantMessage(role, content));
        }
        // history 的语义是「最近若干轮」，保留最后 20 条
        int from = Math.max(0, result.size() - MAX_HISTORY_SIZE);
        return new ArrayList<>(result.subList(from, result.size()));
    }

    private static String titleFromMessage(String message) {
        String compact = message.replaceAll("\\s+", " ").trim();
        if (compact.length() <= 60) {
            return compact;
        }
        return compact.substring(0, 60) + "…";
    }
}