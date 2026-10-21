package ming.valuesjava.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * 跨域配置。
 * 前端开发服务器（Vite）跑在 5173，与后端 8080 端口不同源，需要放行；
 *
 * 为什么管理写接口已经「不做鉴权」还要死守来源白名单：
 * CORS 拦不住 curl，但它能拦住用户浏览其他网站时被脚本代发的写请求；
 * 未鉴权阶段这是唯一还有点作用的浏览器侧防线，放宽成 * 等于把增删改直接暴露给任意页面。
 */
@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOrigins("http://localhost:5173", "http://127.0.0.1:5173")
                .allowedMethods("GET", "POST", "PUT", "PATCH", "DELETE");
    }
}