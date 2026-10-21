package ming.valuesjava.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * 跨域配置。
 * 前端开发服务器（Vite）跑在 5173，与后端 8080 端口不同源，需要放行；
 * 只允许本机来源且只允许 GET，避免把只读接口开成任意站点可读。
 */
@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOrigins("http://localhost:5173", "http://127.0.0.1:5173")
                .allowedMethods("GET");
    }
}