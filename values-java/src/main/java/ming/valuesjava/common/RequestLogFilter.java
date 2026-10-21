package ming.valuesjava.common;

import java.io.IOException;
import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * 业务接口的请求日志：入口记录方法、路径、查询参数，出口记录状态码与耗时。
 *
 * 为什么放在过滤器而不是各个 controller：
 * 出入口日志与业务无关，集中一处可以保证所有接口口径一致，controller 也不必承担日志职责。
 *
 * 每次请求生成 traceId 写入 MDC 并回传到响应头 X-Trace-Id，
 * 排查时可以用它把同一次请求的多行日志串起来，也方便用户报错时提供可检索的编号。
 */
@Component
public class RequestLogFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(RequestLogFilter.class);

    /** 只记录业务接口，避免静态资源等请求污染日志 */
    private static final String API_PREFIX = "/api/";

    private static final String TRACE_ID_KEY = "traceId";

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !request.getRequestURI().startsWith(API_PREFIX);
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String traceId = UUID.randomUUID().toString().replace("-", "").substring(0, 16);
        MDC.put(TRACE_ID_KEY, traceId);
        response.setHeader("X-Trace-Id", traceId);

        long start = System.currentTimeMillis();
        // 本项目的接口都是 GET，入参全部体现在路径与查询串里，因此不额外记录请求体
        log.info("请求开始 method={} uri={} query={}", request.getMethod(), request.getRequestURI(),
                request.getQueryString());

        try {
            chain.doFilter(request, response);
        } finally {
            // 出口放在 finally，异常路径同样能留下状态码与耗时
            log.info("请求结束 method={} uri={} status={} cost={}ms", request.getMethod(), request.getRequestURI(),
                    response.getStatus(), System.currentTimeMillis() - start);
            // Tomcat 线程会复用，必须清理 MDC，否则 traceId 会串到下一个请求
            MDC.remove(TRACE_ID_KEY);
        }
    }
}