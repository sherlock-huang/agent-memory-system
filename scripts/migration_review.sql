-- ============================================
-- Migration: 添加 Review 协作功能
-- 运行方式:
--   mysql -h YOUR_HOST -P YOUR_PORT -u memory_user -p agent_memory < scripts/migration_review.sql
-- ============================================

USE agent_memory;

-- ------------------------------------------------
-- 1. 给 experiences 表添加 reviewer 相关字段
-- ------------------------------------------------
ALTER TABLE experiences
  ADD COLUMN reviewer_id VARCHAR(100) DEFAULT NULL COMMENT '指定审核人ID' AFTER approved_by,
  ADD COLUMN review_requested_at BIGINT DEFAULT NULL COMMENT '请求审核时间戳(ms)' AFTER reviewer_id,
  ADD COLUMN reviewed_at BIGINT DEFAULT NULL COMMENT '审核完成时间戳(ms)' AFTER review_requested_at,
  ADD COLUMN rejection_reason TEXT DEFAULT NULL COMMENT '驳回原因' AFTER reviewed_at,
  ADD COLUMN status ENUM('draft', 'pending_review', 'published', 'revision_requested', 'archived') 
      DEFAULT 'draft' COMMENT '经验状态' AFTER status;

-- 迁移已有数据：将 published 状态的设为 draft（避免状态冲突）
UPDATE experiences SET status = 'draft' WHERE status = 'published';
ALTER TABLE experiences MODIFY COLUMN status ENUM('draft', 'pending_review', 'published', 'revision_requested', 'archived') DEFAULT 'draft';

-- ------------------------------------------------
-- 2. 新建 reviews 表（核心审核表）
-- ------------------------------------------------
DROP TABLE IF EXISTS reviews;

CREATE TABLE reviews (
    -- 唯一标识
    id VARCHAR(50) PRIMARY KEY COMMENT 'Review ID，格式: rev_xxxxxxxxxx',
    
    -- 关联的经验
    experience_code VARCHAR(50) NOT NULL COMMENT '被审核的经验code',
    experience_id VARCHAR(50) NOT NULL COMMENT '被审核的经验内部ID',
    
    -- 审核人
    reviewer_id VARCHAR(100) NOT NULL COMMENT '审核人Agent ID',
    reviewer_name VARCHAR(100) COMMENT '审核人显示名',
    
    -- 审核结果
    status ENUM('requested', 'approved', 'changes_requested') NOT NULL DEFAULT 'requested' COMMENT '审核状态',
    decision ENUM('approve', 'request_changes', 'reject') DEFAULT NULL COMMENT '最终决定',
    
    -- 审核意见
    comment TEXT COMMENT '审核评论/反馈意见',
    line_reviews JSON COMMENT '逐行批注，格式: [{line: N, comment: "..."}]',
    
    -- 版本追踪
    version_at_review INT DEFAULT 1 COMMENT '审核时的经验版本号',
    previous_code VARCHAR(50) COMMENT '如果经验有更新，记录上一版本code',
    
    -- 时间戳
    created_at BIGINT NOT NULL COMMENT '创建时间戳(ms)',
    updated_at BIGINT NOT NULL COMMENT '更新时间戳(ms)',
    resolved_at BIGINT COMMENT '审核解决时间戳(ms)',
    
    -- 关联
    requester_id VARCHAR(100) COMMENT '发起审核请求的Agent',
    
    -- 索引
    INDEX idx_experience (experience_code),
    INDEX idx_reviewer (reviewer_id),
    INDEX idx_status (status),
    INDEX idx_requester (requester_id),
    INDEX idx_created (created_at DESC),
    FULLTEXT INDEX ft_comment (comment)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='审核表 - 经验审核协作';

-- ------------------------------------------------
-- 3. 新建 review_comments 表（批注详情）
-- ------------------------------------------------
DROP TABLE IF EXISTS review_comments;

CREATE TABLE review_comments (
    id VARCHAR(50) PRIMARY KEY COMMENT '批注ID，格式: rcm_xxxxxxxxxx',
    review_id VARCHAR(50) NOT NULL COMMENT '所属Review ID',
    
    -- 批注位置
    line_number INT DEFAULT NULL COMMENT '行号（NULL表示针对全文）',
    field_name VARCHAR(50) DEFAULT NULL COMMENT '字段名（title/content/summary等）',
    
    -- 批注内容
    comment TEXT NOT NULL COMMENT '批注内容',
    severity ENUM('suggestion', 'warning', 'error') DEFAULT 'suggestion' COMMENT '严重程度',
    
    -- 状态
    resolved TINYINT(1) DEFAULT 0 COMMENT '是否已解决',
    resolved_by VARCHAR(100) DEFAULT NULL COMMENT '解决者',
    resolved_at BIGINT DEFAULT NULL COMMENT '解决时间戳',
    
    -- 时间戳
    created_at BIGINT NOT NULL COMMENT '创建时间戳(ms)',
    author_id VARCHAR(100) NOT NULL COMMENT '批注作者',
    author_name VARCHAR(100) COMMENT '批注作者显示名',
    
    -- 索引
    INDEX idx_review (review_id),
    INDEX idx_resolved (resolved),
    INDEX idx_author (author_id)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='审核批注表 - 逐行/逐字段批注';

-- ------------------------------------------------
-- 4. 新建 activity_log 表（操作日志）
-- ------------------------------------------------
DROP TABLE IF EXISTS activity_log;

CREATE TABLE activity_log (
    id VARCHAR(50) PRIMARY KEY COMMENT '日志ID',
    actor_id VARCHAR(100) NOT NULL COMMENT '操作者Agent ID',
    actor_name VARCHAR(100) COMMENT '操作者显示名',
    action ENUM(
        'experience_created', 'experience_updated', 'experience_deleted',
        'review_requested', 'review_approved', 'review_changes_requested',
        'review_commented', 'review_resolved',
        'memory_stored', 'memory_shared', 'memory_deleted'
    ) NOT NULL COMMENT '操作类型',
    target_type ENUM('experience', 'memory', 'review') NOT NULL COMMENT '目标类型',
    target_id VARCHAR(50) NOT NULL COMMENT '目标ID',
    target_title VARCHAR(200) COMMENT '目标标题（便于阅读）',
    detail JSON COMMENT '操作详情',
    created_at BIGINT NOT NULL COMMENT '操作时间戳(ms)',
    
    INDEX idx_actor (actor_id),
    INDEX idx_target (target_type, target_id),
    INDEX idx_action (action),
    INDEX idx_created (created_at DESC)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='活动日志表 - 协作操作记录';

-- ------------------------------------------------
-- 5. 初始化视图：待审核经验
-- ------------------------------------------------
CREATE OR REPLACE VIEW v_pending_reviews AS
SELECT 
    e.id, e.code, e.title, e.summary, e.domain, e.tags,
    e.author_id, e.author_name, e.importance, e.level,
    e.status AS experience_status,
    e.reviewer_id, e.review_requested_at,
    e.version, e.created_at,
    r.id AS review_id, r.status AS review_status, r.reviewer_id,
    r.reviewer_name, r.created_at AS review_created_at
FROM experiences e
LEFT JOIN reviews r ON e.code = r.experience_code AND r.status = 'requested'
WHERE e.status IN ('pending_review', 'revision_requested')
ORDER BY e.review_requested_at ASC;

-- ------------------------------------------------
-- 6. 权限约束函数（防止 reviewer 审核自己的经验）
-- ------------------------------------------------
DELIMITER //

CREATE FUNCTION IF NOT EXISTS can_review(p_reviewer_id VARCHAR(100), p_experience_code VARCHAR(50))
RETURNS TINYINT(1)
BEGIN
    DECLARE author VARCHAR(100);
    SELECT author_id INTO author FROM experiences WHERE code = p_experience_code;
    RETURN p_reviewer_id != author;
END //

DELIMITER ;

-- ------------------------------------------------
-- 完成
-- ------------------------------------------------
SELECT 'Migration completed: Review system added successfully' AS status;
