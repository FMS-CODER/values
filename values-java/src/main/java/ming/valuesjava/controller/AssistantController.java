package ming.valuesjava.controller;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import ming.valuesjava.dto.AssistantChatRequest;
import ming.valuesjava.dto.AssistantChatResponse;
import ming.valuesjava.service.AssistantService;

/**
 * AI 助手对话接口。
 *
 * 兼容旧请求：没有 conversationId 时由服务端自动建会话并落库，响应会带回新 ID。
 * 用户标识来自 X-User-Id（前端匿名 UUID）；正式接入登录后应改为服务端登录态。
 */
@RestController
@RequestMapping("/api/assistant")
public class AssistantController {

    private final AssistantService assistantService;

    public AssistantController(AssistantService assistantService) {
        this.assistantService = assistantService;
    }

    @PostMapping("/chat")
    public AssistantChatResponse chat(
            @RequestBody(required = false) AssistantChatRequest request,
            @RequestHeader(name = "X-User-Id", defaultValue = "local-user") String userId) {
        return assistantService.chat(request, userId);
    }
}