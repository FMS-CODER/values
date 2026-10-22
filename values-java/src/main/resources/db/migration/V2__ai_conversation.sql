-- AI 助手会话与消息持久化
-- 适用：已有 values 库的环境，可重复执行。
-- 说明：
--   1. ai_conversation 的 user_id 是客户端匿名标识（X-User-Id），不是登录用户；
--   2. ai_message.citations_json 保存 Python 返回的引用数组，避免为引用单独建表；
--   3. 删除会话时依赖 ON DELETE CASCADE 一并删除消息。

USE `values`;

CREATE TABLE IF NOT EXISTS `ai_conversation` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '会话主键',
  `user_id`    VARCHAR(64)     NOT NULL COMMENT '客户端匿名用户标识',
  `title`      VARCHAR(120)    NOT NULL COMMENT '会话标题，取首条问题摘要',
  `created_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_ai_conversation_user_updated` (`user_id`, `updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='AI 助手会话';

CREATE TABLE IF NOT EXISTS `ai_message` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '消息主键',
  `conversation_id` BIGINT UNSIGNED NOT NULL COMMENT '所属会话',
  `role`            VARCHAR(16)     NOT NULL COMMENT 'user / assistant',
  `content`         MEDIUMTEXT      NOT NULL COMMENT '消息内容',
  `citations_json`  JSON            NULL COMMENT '引用数组，元素含 documentId/title/source/url/snippet',
  `mode`            VARCHAR(24)     NULL COMMENT 'llm / database / rag / placeholder',
  `status`          VARCHAR(16)     NOT NULL DEFAULT 'done' COMMENT 'done / failed',
  `created_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_ai_message_conversation_created` (`conversation_id`, `created_at`),
  CONSTRAINT `fk_ai_message_conversation`
    FOREIGN KEY (`conversation_id`) REFERENCES `ai_conversation` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='AI 助手消息';