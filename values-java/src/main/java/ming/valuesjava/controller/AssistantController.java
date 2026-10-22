package ming.valuesjava.controller;

import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import ming.valuesjava.common.ApiException;
import ming.valuesjava.dto.AssistantChatRequest;
import ming.valuesjava.dto.AssistantChatResponse;

/**
 * AI 助手接口：把请求转发给 Python AI 服务。
 *
 * 为什么不让前端直接调 Python：
 * 浏览器只认识 8080 上的 Java 服务，鉴权、CORS 与输入长度校验都集中在这里；
 * 换模型或改 Python 端口时前端不需要重新发版。
 *
 * 降级策略：Python 服务未启动或调用失败时返回 mode=placeholder，
 * 前端沿用「演示模式」提示，而不是让请求直接报错、把页面变成不可用。
 */
@RestController
@RequestMapping("/api/assistant")
public class AssistantController {

    private static final Logger log = LoggerFactory.getLogger(AssistantController.class);

    /** 与前端输入框上限一致：过长的输入既无意义，也会放大后续模型调用的成本 */
    private static final int MAX_MESSAGE_LENGTH = 1000;

    /** 只接受最近若干轮，避免请求体被无限放大 */
    private static final int MAX_HISTORY_SIZE = 20;

    private static final String PLACEHOLDER_REPLY = """
            AI 营养服务暂时不可用。

            请确认 Python AI 服务已启动（默认 http://127.0.0.1:8000），然后再试一次。
            你也可以先回到首页，查看每种食物每 100g 的营养成分与营养亮点。""";

    private final RestClient pythonClient;

    public AssistantController(
            @Value("${app.assistant.python-base-url:http://127.0.0.1:8000}") String pythonBaseUrl) {
        // 本机调用，连接超时给短一些；模型生成可能较慢，读超时留足 30 秒
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(2_000);
        requestFactory.setReadTimeout(30_000);

        this.pythonClient = RestClient.builder()
                .baseUrl(pythonBaseUrl)
                .requestFactory(requestFactory)
                .build();
    }

    private static final List<String> SUGGESTIONS = List.of(
            "西兰花有哪些营养亮点？",
            "高蛋白的食物有哪些？",
            "苹果的维生素 C 算高吗？");

    @PostMapping("/chat")
    public AssistantChatResponse chat(@RequestBody AssistantChatRequest request) {
        validate(request);

        try {
            AssistantChatResponse response = pythonClient.post()
                    .uri("/api/assistant/chat")
                    .body(request)
                    .retrieve()
                    .body(AssistantChatResponse.class);
            if (response != null) {
                return response;
            }
            log.warn("Python AI 服务返回空响应，使用占位回复");
        } catch (RestClientException ex) {
            log.warn("调用 Python AI 服务失败，使用占位回复：{}", ex.getMessage());
        }

        return new AssistantChatResponse(PLACEHOLDER_REPLY, "placeholder", SUGGESTIONS);
    }

    private void validate(AssistantChatRequest request) {
        if (request == null || request.message() == null || request.message().isBlank()) {
            throw ApiException.badRequest("message 不能为空");
        }
        if (request.message().length() > MAX_MESSAGE_LENGTH) {
            throw ApiException.badRequest("message 长度不能超过 " + MAX_MESSAGE_LENGTH + " 个字符");
        }

        List<AssistantChatRequest.AssistantMessage> history = request.history();
        if (history == null) {
            return;
        }
        if (history.size() > MAX_HISTORY_SIZE) {
            throw ApiException.badRequest("history 最多 " + MAX_HISTORY_SIZE + " 条");
        }
        for (AssistantChatRequest.AssistantMessage item : history) {
            if (item == null || item.role() == null
                    || !("user".equals(item.role()) || "assistant".equals(item.role()))) {
                throw ApiException.badRequest("history.role 只能是 user 或 assistant");
            }
        }
    }
}