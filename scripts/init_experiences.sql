-- ============================================
-- Agent Memory System - Experiences 表
-- 经验分享核心表
-- ============================================

CREATE TABLE IF NOT EXISTS experiences (
    -- 唯一标识
    id VARCHAR(50) PRIMARY KEY COMMENT '内部ID (mem_xxx)',
    code VARCHAR(50) UNIQUE COMMENT '可读标识 EXP-DOMAIN-TAG-SEQ',
    
    -- 核心内容
    title VARCHAR(200) NOT NULL COMMENT '经验标题',
    summary VARCHAR(500) COMMENT '一句话摘要',
    tags JSON COMMENT '标签 ["fastapi","性能"]',
    importance DECIMAL(3,1) DEFAULT 5.0 COMMENT '重要性 1-10',
    
    -- 文件
    file_path VARCHAR(500) COMMENT 'MD文件路径',
    file_hash VARCHAR(64) COMMENT 'SHA256校验',
    
    -- 作者
    author_id VARCHAR(100) COMMENT '作者Agent ID',
    author_name VARCHAR(100) COMMENT '作者显示名',
    author_type VARCHAR(20) DEFAULT 'openclaw' COMMENT '来源类型',
    
    -- 分类
    type VARCHAR(20) DEFAULT 'technical' COMMENT '类型：technical/product/operation',
    domain VARCHAR(50) COMMENT '领域：backend/frontend/ai/devops',
    level VARCHAR(20) DEFAULT 'intermediate' COMMENT '难度：beginner/intermediate/advanced',
    
    -- 质量
    quality_score DECIMAL(3,2) DEFAULT 5.00 COMMENT '质量评分 0-10',
    usage_count INT DEFAULT 0 COMMENT '查阅次数',
    helpful_count INT DEFAULT 0 COMMENT '点赞数',
    
    -- 关联
    related_codes JSON COMMENT '相关经验code列表',
    version INT DEFAULT 1 COMMENT '版本号',
    language_code VARCHAR(10) DEFAULT 'zh' COMMENT '语言：zh/en',
    
    -- 状态
    status VARCHAR(20) DEFAULT 'published' COMMENT '状态：draft/published/archived',
    visibility VARCHAR(20) DEFAULT 'shared' COMMENT '可见性：private/shared/global',
    
    -- 协作
    contributors JSON COMMENT '贡献者列表',
    approved_by VARCHAR(100) COMMENT '审批人',
    
    -- 时间
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
    INDEX idx_helpful (helpful_count DESC)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='经验分享表';
