package ming.valuesjava.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

/**
 * data_source 表实体（营养数据来源字典）。
 *
 * 类名带 Entity 后缀是因为 java.sql 与 JDBC 生态里 DataSource 已被占用的名字，
 * 实体与表名一致但避免与 javax.sql.DataSource 混淆。
 * 主键 id 是 SMALLINT AUTO_INCREMENT，故用 AUTO 策略交由数据库分配。
 */
@TableName("data_source")
public class DataSourceEntity {

    @TableId(value = "id", type = IdType.AUTO)
    private Integer id;

    private String code;

    private String name;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }
}