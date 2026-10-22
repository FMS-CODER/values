package ming.valuesjava.controller;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import ming.valuesjava.dto.ConversationCreateRequest;
import ming.valuesjava.dto.ConversationDto;
import ming.valuesjava.dto.MessageDto;
import ming.valuesjava.dto.PageResult;
import ming.valuesjava.service.ConversationService;
import ming.valuesjava.service.MessageService;

/** AI 助手历史会话与消息查询。 */
@RestController
@RequestMapping("/api/assistant/conversations")
public class ConversationController {

    private final ConversationService conversationService;
    private final MessageService messageService;

    public ConversationController(ConversationService conversationService,
                                  MessageService messageService) {
        this.conversationService = conversationService;
        this.messageService = messageService;
    }

    @PostMapping
    public ResponseEntity<ConversationDto> create(
            @RequestBody(required = false) ConversationCreateRequest request,
            @RequestHeader(name = "X-User-Id", defaultValue = "local-user") String userId) {
        String title = request == null ? null : request.title();
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(conversationService.create(userId, title));
    }

    @GetMapping
    public PageResult<ConversationDto> list(
            @RequestParam(name = "page", defaultValue = "1") int page,
            @RequestParam(name = "size", defaultValue = "20") int size,
            @RequestHeader(name = "X-User-Id", defaultValue = "local-user") String userId) {
        return conversationService.list(userId, page, size);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(
            @PathVariable("id") long id,
            @RequestHeader(name = "X-User-Id", defaultValue = "local-user") String userId) {
        conversationService.delete(id, userId);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/{id}/messages")
    public PageResult<MessageDto> messages(
            @PathVariable("id") long id,
            @RequestParam(name = "page", defaultValue = "1") int page,
            @RequestParam(name = "size", defaultValue = "50") int size,
            @RequestHeader(name = "X-User-Id", defaultValue = "local-user") String userId) {
        conversationService.requireOwned(id, userId);
        return messageService.list(id, page, size);
    }
}