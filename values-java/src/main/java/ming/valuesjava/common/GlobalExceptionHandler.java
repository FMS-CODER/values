package ming.valuesjava.common;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.NoHandlerFoundException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import ming.valuesjava.dto.ApiErrorResponse;

/**
 * 全局异常出口。
 *
 * 为什么必须显式兜住 Exception：
 * 前端按状态码分支，一旦某个未预期异常直接冒泡，Spring 默认返回的 500 页面不是 JSON，
 * 前端解析会二次失败，用户只看到「加载失败」而拿不到任何可操作信息；
 * 这里保证所有响应都是 {"message": "..."}，同时把真实堆栈只写日志、不返回给客户端。
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ApiErrorResponse> handleApiException(ApiException ex) {
        return ResponseEntity.status(ex.getStatus()).body(new ApiErrorResponse(ex.getMessage()));
    }

    /** 保留 FoodController 等既有代码用 ResponseStatusException 表达的 404/400 语义 */
    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<ApiErrorResponse> handleResponseStatus(ResponseStatusException ex) {
        String message = ex.getReason() == null ? "请求处理失败" : ex.getReason();
        return ResponseEntity.status(ex.getStatusCode()).body(new ApiErrorResponse(message));
    }

    /** 请求体 JSON 语法错误、类型不匹配、缺少查询参数都归为 400，避免暴露 Jackson 内部报错文案 */
    @ExceptionHandler({
            HttpMessageNotReadableException.class,
            MethodArgumentTypeMismatchException.class,
            MissingServletRequestParameterException.class
    })
    public ResponseEntity<ApiErrorResponse> handleBadRequest(Exception ex) {
        log.warn("请求参数不合法：{}", ex.getMessage());
        return ResponseEntity.badRequest().body(new ApiErrorResponse("请求参数格式错误"));
    }

    @ExceptionHandler({NoResourceFoundException.class, NoHandlerFoundException.class})
    public ResponseEntity<ApiErrorResponse> handleNoHandler(Exception ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(new ApiErrorResponse("接口不存在"));
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<ApiErrorResponse> handleMethodNotSupported(HttpRequestMethodNotSupportedException ex) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED)
                .body(new ApiErrorResponse("请求方法不支持：" + ex.getMethod()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiErrorResponse> handleUnexpected(Exception ex) {
        // 堆栈只进日志，响应里不给 SQL、类名等实现细节
        log.error("未处理的服务器异常", ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(new ApiErrorResponse("服务器内部错误"));
    }
}