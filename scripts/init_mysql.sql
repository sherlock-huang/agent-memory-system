-- ============================================
-- Agent Memory System - MySQL 5.7/8.0 通用 Schema
-- 兼容 MySQL 5.7 及以上版本
-- ============================================
-- MySQL 连接示例:
--   mysql -h 218.201.18.131 -P 8999 -u root1 -p
-- ============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS agent_memory
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE agent_memory;

-- ============================================
-- 1. 共享记忆表
-- ============================================
-- 注意: MySQL 5.7 不支持原生 JSON，我们用 VARCHAR 存储 JSON 字符串
-- 注意: MySQL 5.7 的 FULLTEXT 只支持 InnoDB/MyISAM，在 VARCHAR/TEXT 上有限制
-- ============================================

DROP TABLE IF EXISTS memories;
CREATE TABLE memories (
    id VARCHAR(50) PRIMARY KEY COMMENT '记忆ID，格式: mem_xxxxxxxxxx',
    content TEXT NOT NULL COMMENT '记忆内容',
    summary VARCHAR(500) COMMENT '摘要',
    
    -- 分类
    type ENUM('general', 'project', 'preference', 'knowledge', 'team') 
        NOT NULL DEFAULT 'general' COMMENT '记忆类型',
    visibility ENUM('private', 'shared', 'global') 
        NOT NULL DEFAULT 'shared' COMMENT '可见性',
    
    -- 来源
    source ENUM('cli', 'openclaw', 'claude_code', 'codex', 'kimi_code', 'cursor', 'other') 
        NOT NULL DEFAULT 'cli' COMMENT '来源Agent类型',
    source_agent VARCHAR(100) COMMENT '来源Agent ID',
    project_path VARCHAR(500) COMMENT '关联项目路径',
    
    -- 评分
    importance DECIMAL(3,1) DEFAULT 5.0 COMMENT '重要性 1-10',
    
    -- 标签 (MySQL 5.7 用 VARCHAR 存储 JSON)
    tags VARCHAR(1000) DEFAULT '{}' COMMENT '标签JSON ["tag1","tag2"]',
    
    -- 时间戳 (毫秒)
    created_at BIGINT NOT NULL COMMENT '创建时间戳(ms)',
    updated_at BIGINT NOT NULL COMMENT '更新时间戳(ms)',
    
    -- 状态
    is_deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记',
    
    -- 经验分享专用字段 (MySQL 5.7 用 VARCHAR 存储)
    share_title VARCHAR(200) COMMENT '经验名称（唯一标题）',
    md_content TEXT COMMENT 'MD格式正文（经验专用）',
    notes VARCHAR(1000) COMMENT '备注（经验专用）',
    
    -- 索引
    INDEX idx_type (type),
    INDEX idx_visibility (visibility),
    INDEX idx_project (project_path(255)),
    INDEX idx_source (source),
    INDEX idx_created (created_at DESC),
    INDEX idx_deleted (is_deleted),
    INDEX idx_importance (importance),
    INDEX idx_share_title (share_title)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='共享记忆表';


-- ============================================
-- 2. Agent 注册表
-- ============================================
DROP TABLE IF EXISTS agents;
CREATE TABLE agents (
    id VARCHAR(100) PRIMARY KEY COMMENT 'Agent ID',
    type ENUM('openclaw', 'claude_code', 'codex', 'kimi_code', 'cursor', 'other') 
        NOT NULL COMMENT 'Agent类型',
    name VARCHAR(100) COMMENT '显示名称',
    description VARCHAR(500) COMMENT '描述',
    api_key_hash VARCHAR(255) COMMENT 'API Key hash',
    version VARCHAR(50) COMMENT '版本',
    capabilities VARCHAR(1000) DEFAULT '{}' COMMENT '能力JSON',
    status ENUM('active', 'inactive', 'disconnected') DEFAULT 'active' COMMENT '状态',
    registered_at BIGINT NOT NULL COMMENT '注册时间戳(ms)',
    last_seen BIGINT COMMENT '最后活跃时间戳(ms)',
    
    INDEX idx_type (type),
    INDEX idx_status (status),
    INDEX idx_last_seen (last_seen)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Agent注册表';


-- ============================================
-- 3. 访问控制表 (ACL)
-- ============================================
DROP TABLE IF EXISTS acl;
CREATE TABLE acl (
    memory_id VARCHAR(50) NOT NULL COMMENT '记忆ID',
    agent_id VARCHAR(100) NOT NULL COMMENT 'Agent ID',
    permission ENUM('read', 'write', 'admin') NOT NULL DEFAULT 'read' COMMENT '权限',
    grant_type ENUM('direct', 'inherited', 'role') DEFAULT 'direct' COMMENT '授权类型',
    granted_by VARCHAR(100) NOT NULL COMMENT '授权者',
    granted_at BIGINT NOT NULL COMMENT '授权时间戳(ms)',
    expires_at BIGINT COMMENT '过期时间戳(ms)',
    
    PRIMARY KEY (memory_id, agent_id),
    INDEX idx_agent (agent_id),
    INDEX idx_expires (expires_at),
    
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='访问控制表';


-- ============================================
-- 4. 向量缓存表
-- ============================================
DROP TABLE IF EXISTS embeddings;
CREATE TABLE embeddings (
    content_hash VARCHAR(64) PRIMARY KEY COMMENT '内容SHA256哈希',
    embedding LONGBLOB COMMENT '向量数据',
    model VARCHAR(50) COMMENT '嵌入模型名称',
    dimension INT COMMENT '向量维度',
    created_at BIGINT COMMENT '创建时间戳(ms)',
    
    INDEX idx_model (model)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='向量缓存表';


-- ============================================
-- 5. 搜索历史表
-- ============================================
DROP TABLE IF EXISTS search_history;
CREATE TABLE search_history (
    id VARCHAR(50) PRIMARY KEY COMMENT '搜索ID',
    query TEXT NOT NULL COMMENT '搜索内容',
    agent_id VARCHAR(100) NOT NULL COMMENT '搜索者Agent ID',
    session_id VARCHAR(100) COMMENT '会话ID',
    results_count INT DEFAULT 0 COMMENT '返回结果数量',
    results_ids VARCHAR(2000) DEFAULT '[]' COMMENT '返回的记忆ID列表(JSON)',
    latency_ms INT COMMENT '响应延迟(ms)',
    searched_at BIGINT NOT NULL COMMENT '搜索时间戳(ms)',
    
    INDEX idx_agent (agent_id),
    INDEX idx_session (session_id),
    INDEX idx_searched (searched_at)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='搜索历史表';


-- ============================================
-- 6. 访问日志表
-- ============================================
DROP TABLE IF EXISTS access_log;
CREATE TABLE access_log (
    id VARCHAR(50) PRIMARY KEY COMMENT '日志ID',
    memory_id VARCHAR(50) COMMENT '记忆ID',
    agent_id VARCHAR(100) NOT NULL COMMENT '操作者Agent ID',
    action ENUM('read', 'write', 'delete', 'share', 'grant', 'revoke') NOT NULL COMMENT '操作类型',
    details VARCHAR(1000) DEFAULT '{}' COMMENT '详细信息(JSON)',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    user_agent VARCHAR(500) COMMENT 'User Agent',
    accessed_at BIGINT NOT NULL COMMENT '操作时间戳(ms)',
    
    INDEX idx_agent (agent_id),
    INDEX idx_memory (memory_id),
    INDEX idx_action (action),
    INDEX idx_accessed (accessed_at)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='访问日志表';


-- ============================================
-- 7. 角色表
-- ============================================
DROP TABLE IF EXISTS agent_roles;
CREATE TABLE agent_roles (
    id VARCHAR(50) PRIMARY KEY COMMENT '角色ID',
    agent_id VARCHAR(100) NOT NULL COMMENT 'Agent ID',
    role_type ENUM('owner', 'admin', 'member', 'guest') DEFAULT 'member' COMMENT '角色类型',
    project_path VARCHAR(500) COMMENT '项目路径(如果是项目级角色)',
    created_at BIGINT NOT NULL COMMENT '创建时间戳(ms)',
    updated_at BIGINT NOT NULL COMMENT '更新时间戳(ms)',
    
    UNIQUE KEY uk_agent_project (agent_id, project_path),
    INDEX idx_role_type (role_type),
    
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Agent角色表';


-- ============================================
-- 8. 辅助函数
-- ============================================

-- 获取当前时间戳 (毫秒)
DELIMITER //
CREATE FUNCTION IF NOT EXISTS current_timestamp_ms()
RETURNS BIGINT
BEGIN
    RETURN UNIX_TIMESTAMP() * 1000;
END //
DELIMITER ;

-- 生成记忆ID
DELIMITER //
CREATE FUNCTION IF NOT EXISTS generate_memory_id()
RETURNS VARCHAR(50)
BEGIN
    DECLARE hash_str VARCHAR(32);
    SET hash_str = MD5(CONCAT(RAND(), NOW(6), UUID()));
    RETURN CONCAT('mem_', SUBSTRING(hash_str, 1, 10));
END //
DELIMITER ;


-- ============================================
-- 初始化默认数据 (可选)
-- ============================================

-- 创建默认 Agent (用于首次使用)
-- INSERT INTO agents (id, type, name, registered_at) 
-- VALUES ('default', 'cli', 'Default CLI', current_timestamp_ms());
