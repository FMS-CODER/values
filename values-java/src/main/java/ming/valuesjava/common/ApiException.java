package ming.valuesjava.common;

import org.springframework.http.HttpStatus;

/**
 * 业务异常：把「该返回哪个状态码」从 service 里显式带出来。
 *
 * 为什么不直接抛 ResponseStatusException：
 * 那是 Web 层类型，service 一旦依赖它，后续被定时任务或命令行复用时会凭空引入 MVC 依赖；
 * 这里只保留状态码 + 文案，由 GlobalExceptionHandler 统一翻译成响应体。
 */
public class ApiException extends RuntimeException {

    private final HttpStatus status;

    public ApiException(HttpStatus status, String message) {
        super(message);
        this.status = status;
    }

    public HttpStatus getStatus() {
        return status;
    }

    public static ApiException badRequest(String message) {
        return new ApiException(HttpStatus.BAD_REQUEST, message);
    }

    public static ApiException notFound(String message) {
        return new ApiException(HttpStatus.NOT_FOUND, message);
    }

    public static ApiException forbidden(String message) {
        return new ApiException(HttpStatus.FORBIDDEN, message);
    }

    public static ApiException conflict(String message) {
        return new ApiException(HttpStatus.CONFLICT, message);
    }

    public static ApiException internal(String message) {
        return new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, message);
    }
}