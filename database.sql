-- 创建数据库
CREATE DATABASE IF NOT EXISTS ai DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE ai;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password VARCHAR(255) NOT NULL COMMENT '密码（建议使用哈希存储）',
    avatar VARCHAR(500) DEFAULT NULL COMMENT '用户头像URL',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    last_login TIMESTAMP NULL COMMENT '最后登录时间',
    status TINYINT DEFAULT 1 COMMENT '用户状态：1-正常，0-禁用',
    is_admin TINYINT DEFAULT 0 COMMENT '是否为管理员：1-是，0-否'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- API服务商表
CREATE TABLE IF NOT EXISTS api_providers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '服务商名称',
    base_url VARCHAR(500) NOT NULL COMMENT 'API基础URL',
    api_key VARCHAR(500) NOT NULL COMMENT 'API密钥',
    description TEXT COMMENT '服务商描述',
    status TINYINT DEFAULT 1 COMMENT '状态：1-启用，0-禁用',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='API服务商表';

-- 模型配置表
CREATE TABLE IF NOT EXISTS model_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    provider_id INT NOT NULL COMMENT '服务商ID',
    model_id VARCHAR(200) NOT NULL COMMENT '模型ID',
    model_name VARCHAR(200) NOT NULL COMMENT '模型显示名称',
    description TEXT COMMENT '模型描述',
    max_tokens INT DEFAULT 4096 COMMENT '最大token数',
    status TINYINT DEFAULT 1 COMMENT '状态：1-启用，0-禁用',
    sort_order INT DEFAULT 0 COMMENT '排序权重',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_provider_id (provider_id),
    INDEX idx_status (status),
    INDEX idx_sort_order (sort_order),
    FOREIGN KEY (provider_id) REFERENCES api_providers(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模型配置表';

-- 会话表（用于管理对话会话）
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL UNIQUE COMMENT '会话ID',
    user_id INT NOT NULL COMMENT '用户ID',
    title VARCHAR(200) DEFAULT '新对话' COMMENT '会话标题',
    model_id VARCHAR(100) NOT NULL COMMENT '当前使用的模型ID',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_active TINYINT DEFAULT 1 COMMENT '是否活跃：1-活跃，0-已结束',
    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id),
    INDEX idx_update_time (update_time),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话会话表';

-- AI对话消息表（存储单条消息记录）
CREATE TABLE IF NOT EXISTS ai_chat_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL COMMENT '会话ID',
    user_id INT NOT NULL COMMENT '用户ID',
    role ENUM('user', 'assistant') NOT NULL COMMENT '消息角色：user-用户，assistant-助手',
    content TEXT NOT NULL COMMENT '消息内容',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_create_time (create_time),
    INDEX idx_session_user (session_id, user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI对话消息表';

-- 插入测试用户（密码为123456的哈希值）
INSERT INTO users (username, password, is_admin) VALUES 
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukXN/8cjC', 1),
('test', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukXN/8cjC', 0)
ON DUPLICATE KEY UPDATE username=username;

-- 插入默认模型配置
INSERT INTO model_configs (provider_id, model_id, model_name, description, sort_order) VALUES 
(1, 'z-ai/glm-4.5-air:free', 'GLM-4.5 Air (免费)', 'GLM-4.5 Air 免费版本', 1),
(1, 'qwen/qwen3-coder:free', 'Qwen3 Coder (免费)', 'Qwen3 代码专用模型免费版', 2),
(1, 'moonshotai/kimi-k2:free', 'Kimi K2 (免费)', 'Kimi K2 免费版本', 3),
(1, 'qwen/qwen3-235b-a22b:free', 'Qwen3 235B (免费)', 'Qwen3 235B 免费版本', 4)
ON DUPLICATE KEY UPDATE model_name=model_name;