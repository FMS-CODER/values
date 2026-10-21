package ming.valuesjava;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Mapper 接口集中在 ming.valuesjava.mapper 包，这里统一扫描，
 * 避免每个接口重复写 @Mapper（漏写时只会在运行期报 Invalid bound statement，排查成本高）。
 */
@SpringBootApplication
@MapperScan("ming.valuesjava.mapper")
public class ValuesJavaApplication {

    public static void main(String[] args) {
        SpringApplication.run(ValuesJavaApplication.class, args);
    }

}
