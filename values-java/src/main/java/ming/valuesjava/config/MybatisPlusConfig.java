package ming.valuesjava.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import com.baomidou.mybatisplus.annotation.DbType;
import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;

/**
 * MyBatis-Plus 插件配置。
 *
 * 分页插件必须注册：BaseMapper.selectPage 只有在拦截器存在时才会拼 LIMIT 并执行 count，
 * 漏注册时不会报错，而是静默返回全表数据且 total 为 0，属于最难排查的一类问题。
 * 方言固定为 MySQL，与数据源一致。
 */
@Configuration
public class MybatisPlusConfig {

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        interceptor.addInnerInterceptor(new PaginationInnerInterceptor(DbType.MYSQL));
        return interceptor;
    }
}