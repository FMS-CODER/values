package ming.valuesjava.controller;

import java.util.List;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import ming.valuesjava.common.ApiException;
import ming.valuesjava.dto.AssistantChatRequest;
import ming.valuesjava.dto.AssistantChatResponse;

/**
 * AI 助手接口（占位实现）。
 *
 * 为什么先给占位而不是直接返回模型答案：
 * Python 侧的 LangGraph 服务尚未接入，此时若编造一段「营养建议」，
 * 用户会把它当成经过核对的数据；这里明确返回 mode=placeholder 与说明文案，
 * 前端据此展示「演示模式」，把「界面已就绪、服务未接入」这件事表达清楚。
 *
 * 接入方式：保持本接口的请求/响应结构不变，把本类的方法体替换为
 * 调用 Python AI 服务（LangGraph）的客户端即可，前端无需改动。
 */
@RestController
@RequestMapping("/api/assistant")
public class AssistantController {

    /** 与前端输入框上限一致：过长的输入既无意义，也会放大后续模型调用的成本 */
    private static final int MAX_MESSAGE_LENGTH = 1000;

    /** 只接受最近若干轮，避免请求体被无限放大 */
    private static final int MAX_HISTORY_SIZE = 20;

    private static final String PLACEHOLDER_REPLY = """
            AI 助手尚未接入服务。

            这个页面目前用于确认交互与布局。等 Python 侧的 LangGraph 服务接入后，\
            会基于食物营养库回答，并给出可核对的营养数值。

            现在可以先浏览「食物」，查看每种食物每 100g 的营养成分与营养亮点。""";

    private static final List<String> SUGGESTIONS = List.of(
            "西兰花有哪些营养亮点？",
            "高蛋白的食物有哪些？",
            "苹果的维生素 C 算高吗？");

    @PostMapping("/chat")
    public AssistantChatResponse chat(@RequestBody AssistantChatRequest request) {
        validate(request);

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