-- ============================================
-- Agent Memory System - MySQL 单一存储方案
-- 只使用 MySQL 存储经验和记忆
-- ============================================
-- MySQL 连接示例:
--   mysql -h YOUR_HOST -P YOUR_PORT -u YOUR_USER -p
-- ============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS agent_memory
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE agent_memory;

-- ============================================
-- 1. 经验表 (experiences)
-- 云端共享的经验，带 MD 格式内容
-- ============================================

DROP TABLE IF EXISTS experiences;
CREATE TABLE experiences (
    -- 唯一标识
    id VARCHAR(50) PRIMARY KEY COMMENT '内部ID (mem_xxx)',
    code VARCHAR(50) UNIQUE COMMENT '可读标识 EXP-DOMAIN-TAG-SEQ',
    
    -- 核心内容
    title VARCHAR(200) NOT NULL COMMENT '经验标题',
    summary VARCHAR(500) COMMENT '一句话摘要',
    importance DECIMAL(3,1) DEFAULT 5.0 COMMENT '重要性 1-10',
    level VARCHAR(20) DEFAULT 'intermediate' COMMENT '难度：beginner/intermediate/advanced',
    
    -- MD 格式正文（核心内容字段）
    content MEDIUMTEXT NOT NULL COMMENT 'MD格式正文，存储完整经验内容',
    
    -- 文件信息（可选，用于本地文件备份）
    file_path VARCHAR(500) COMMENT '本地MD文件路径',
    file_hash VARCHAR(64) COMMENT 'SHA256校验',
    
    -- 作者
    author_id VARCHAR(100) NOT NULL COMMENT '作者Agent ID',
    author_name VARCHAR(100) COMMENT '作者显示名',
    author_type VARCHAR(20) DEFAULT 'openclaw' COMMENT '来源类型',
    
    -- 分类
    domain VARCHAR(50) DEFAULT 'GENERAL' COMMENT '领域：BACKEND/FRONTEND/DEVOPS/AI/DATABASE/GENERAL',
    tags JSON COMMENT '标签列表 ["fastapi","performance"]',
    type VARCHAR(20) DEFAULT 'technical' COMMENT '类型：technical/product/operation',
    
    -- 质量指标
    quality_score DECIMAL(3,2) DEFAULT 5.00 COMMENT '质量评分 0-10',
    usage_count INT DEFAULT 0 COMMENT '查阅次数',
    helpful_count INT DEFAULT 0 COMMENT '点赞数',
    
    -- 关联
    related_codes JSON COMMENT '相关经验code列表',
    version INT DEFAULT 1 COMMENT '版本号',
    language_code VARCHAR(10) DEFAULT 'zh' COMMENT '语言：zh/en',
    
    -- 协作
    contributors JSON COMMENT '贡献者列表',
    approved_by VARCHAR(100) COMMENT '审批人',
    
    -- 状态
    status VARCHAR(20) DEFAULT 'published' COMMENT '状态：draft/published/archived',
    visibility VARCHAR(20) DEFAULT 'shared' COMMENT '可见性：private/shared/global',
    
    -- 时间戳
    created_at BIGINT NOT NULL COMMENT '创建时间戳(ms)',
    updated_at BIGINT NOT NULL COMMENT '更新时间戳(ms)',
    published_at BIGINT COMMENT '发布时间戳(ms)',
    
    -- 索引
    INDEX idx_code (code),
    INDEX idx_author (author_id),
    INDEX idx_domain (domain),
    INDEX idx_type (type),
    INDEX idx_status (status),
    INDEX idx_visibility (visibility),
    INDEX idx_created (created_at DESC),
    INDEX idx_usage (usage_count DESC),
    INDEX idx_helpful (helpful_count DESC),
    INDEX idx_importance (importance DESC),
    FULLTEXT INDEX ft_title_summary (title, summary)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='经验表 - 存储云端共享的经验';


-- ============================================
-- 2. 记忆表 (memories)
-- Agent 本地记忆，支持 private/shared/global
-- ============================================

DROP TABLE IF EXISTS memories;
CREATE TABLE memories (
    -- 唯一标识
    id VARCHAR(50) PRIMARY KEY COMMENT '记忆ID，格式: mem_xxxxxxxxxx',
    
    -- 核心内容
    content TEXT NOT NULL COMMENT '记忆内容',
    summary VARCHAR(500) COMMENT '摘要',
    
    -- MD 格式内容（可选，用于结构化记忆）
    md_content MEDIUMTEXT COMMENT 'MD格式正文（可选）',
    
    -- 分类
    type ENUM('general', 'project', 'preference', 'knowledge', 'team') 
        NOT NULL DEFAULT 'general' COMMENT '记忆类型',
    visibility ENUM('private', 'shared', 'global') 
        NOT NULL DEFAULT 'private' COMMENT '可见性',
    
    -- 来源
    source ENUM('cli', 'openclaw', 'claude_code', 'codex', 'kimi_code', 'cursor', 'other') 
        NOT NULL DEFAULT 'openclaw' COMMENT '来源Agent类型',
    source_agent VARCHAR(100) COMMENT '来源Agent ID',
    source_agent_name VARCHAR(100) COMMENT '来源Agent显示名',
    project_path VARCHAR(500) COMMENT '关联项目路径',
    
    -- 评分
    importance DECIMAL(3,1) DEFAULT 5.0 COMMENT '重要性 1-10',
    
    -- 标签
    tags JSON COMMENT '标签列表 ["project","backend"]',
    
    -- 时间戳
    created_at BIGINT NOT NULL COMMENT '创建时间戳(ms)',
    updated_at BIGINT NOT NULL COMMENT '更新时间戳(ms)',
    
    -- 状态
    is_deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记',
    
    -- 经验关联（如果这条记忆被分享为经验）
    experience_code VARCHAR(50) COMMENT '关联的经验code',
    
    -- 索引
    INDEX idx_type (type),
    INDEX idx_visibility (visibility),
    INDEX idx_source (source),
    INDEX idx_source_agent (source_agent),
    INDEX idx_project (project_path(255)),
    INDEX idx_created (created_at DESC),
    INDEX idx_importance (importance DESC),
    INDEX idx_deleted (is_deleted),
    INDEX idx_experience (experience_code),
    FULLTEXT INDEX ft_content (content, summary)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='记忆表 - Agent本地记忆';


-- ============================================
-- 3. Agent 注册表 (agents)
-- ============================================

DROP TABLE IF EXISTS agents;
CREATE TABLE agents (
    id VARCHAR(100) PRIMARY KEY COMMENT 'Agent ID',
    type ENUM('openclaw', 'claude_code', 'codex', 'kimi_code', 'cursor', 'other') 
        NOT NULL COMMENT 'Agent类型',
    name VARCHAR(100) COMMENT '显示名称',
    description VARCHAR(500) COMMENT '描述',
    version VARCHAR(50) COMMENT '版本',
    capabilities JSON DEFAULT '{}' COMMENT '能力JSON',
    status ENUM('active', 'inactive', 'disconnected') DEFAULT 'active' COMMENT '状态',
    registered_at BIGINT NOT NULL COMMENT '注册时间戳(ms)',
    last_seen BIGINT COMMENT '最后活跃时间戳(ms)',
    
    INDEX idx_type (type),
    INDEX idx_status (status),
    INDEX idx_last_seen (last_seen)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Agent注册表';


-- ============================================
-- 4. 访问控制表 (acl)
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
    INDEX idx_expires (expires_at)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='访问控制表';


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
    results_ids JSON COMMENT '返回的记忆/经验ID列表',
    latency_ms INT COMMENT '响应延迟(ms)',
    searched_at BIGINT NOT NULL COMMENT '搜索时间戳(ms)',
    
    INDEX idx_agent (agent_id),
    INDEX idx_session (session_id),
    INDEX idx_searched (searched_at DESC)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='搜索历史表';


-- ============================================
-- 6. 序列号表 (用于生成经验code)
-- ============================================

DROP TABLE IF EXISTS experience_sequences;
CREATE TABLE experience_sequences (
    domain VARCHAR(50) NOT NULL COMMENT '领域',
    tag VARCHAR(50) NOT NULL COMMENT '标签',
    current_seq INT DEFAULT 0 COMMENT '当前序号',
    
    PRIMARY KEY (domain, tag)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='经验序号表 - 用于生成唯一经验code';


-- ============================================
-- 7. 辅助函数
-- ============================================

DELIMITER //

-- 获取当前时间戳 (毫秒)
CREATE FUNCTION IF NOT EXISTS current_timestamp_ms()
RETURNS BIGINT
BEGIN
    RETURN UNIX_TIMESTAMP() * 1000;
END //

-- 生成记忆ID
CREATE FUNCTION IF NOT EXISTS generate_memory_id()
RETURNS VARCHAR(50)
BEGIN
    DECLARE hash_str VARCHAR(32);
    SET hash_str = MD5(CONCAT(RAND(), NOW(6), UUID()));
    RETURN CONCAT('mem_', SUBSTRING(hash_str, 1, 10));
END //

-- 生成下一个经验序号
CREATE FUNCTION IF NOT EXISTS next_experience_seq(p_domain VARCHAR(50), p_tag VARCHAR(50))
RETURNS INT
BEGIN
    DECLARE next_seq INT;
    
    INSERT INTO experience_sequences (domain, tag, current_seq)
    VALUES (p_domain, p_tag, 1)
    ON DUPLICATE KEY UPDATE current_seq = current_seq + 1;
    
    SELECT current_seq INTO next_seq 
    FROM experience_sequences 
    WHERE domain = p_domain AND tag = p_tag;
    
    RETURN next_seq;
END //

DELIMITER ;


-- ============================================
-- 初始化数据
-- ============================================

-- 初始化默认 Agent（如果需要）
-- INSERT INTO agents (id, type, name, registered_at) 
-- VALUES ('default_openclaw', 'openclaw', 'Default OpenClaw', current_timestamp_ms());
