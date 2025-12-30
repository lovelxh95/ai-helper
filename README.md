# AI助手聊天系统项目文档

## 项目概述

AI助手聊天系统是一个基于FastAPI和Vue.js的现代化AI对话平台，支持多模型切换、实时流式对话传输和对话历史管理功能。用户可以通过该系统与各种AI模型进行交互，系统会自动保存对话历史，方便用户随时查看和继续之前的对话。

## 功能特性

+ 🤖 多AI模型支持：系统支持多种AI模型切换，包括GLM-4.5、Qwen3、Kimi等
+ 💬 实时流式对话：采用流式传输技术，提供接近实时的对话体验
+ 📝 对话历史管理：自动保存对话记录，支持按时间查看历史对话
+ 👤 用户管理系统：完整的用户注册、登录和权限管理功能
+ 🎨 现代化界面：响应式设计，适配不同设备屏幕
+ 🔒 数据安全：用户数据隔离，确保隐私安全

## 技术架构

### 后端技术栈

+ **FastAPI**：现代化、快速的Python Web框架，提供异步处理能力
+ **MySQL**：关系型数据库，用于持久化存储用户信息和对话记录
+ **PyMySQL**：Python MySQL数据库连接库
+ **HTTPX**：异步HTTP客户端，用于与AI模型API通信

### 前端技术栈

+ **Vue.js 3**：渐进式JavaScript框架，构建用户界面
+ **Element Plus**：基于Vue 3的组件库，提供丰富的UI组件
+ **原生HTML/CSS/JavaScript**：实现基础页面结构和样式

## 快速开始

### 环境准备

确保系统已安装以下依赖：

+ Python 3.12
+ MySQL 8.0
+ Git

### 安装步骤

1. 克隆项目代码：

```bash
git clone https://github.com/lovelxh95/ai-helper.git
cd ai-helper
```

2. 安装项目依赖：

```bash
pip install -r requirements.txt
```

3. 配置数据库：

创建MySQL数据库并执行初始化脚本：

```sql
source database.sql
```

4. 配置数据库连接信息：

修改 [config.py](file:///D:/CodeProject/PycharmProjects/ai-helper/config.py) 文件中的数据库配置：

```python
MySQL_CONFIG = {
    'host': 'your_host',
    'port': 3306,
    'user': 'your_username',
    'password': 'your_password',
    'db': 'ai',
    'charset': 'utf8mb4'
}
```

5. 启动服务：

```bash
python main.py
```

服务将在 [http://localhost:8000](http://localhost:8000) 启动。

![](https://cdn.nlark.com/yuque/0/2025/png/44843733/1753954926895-7e2aab23-3c68-4092-9b3d-d5ae1d3eb7ed.png)

6. 设置服务商

+ 访问[http://localhost:8000/admin](http://localhost:8000/admin)
+ 设置服务商

![](https://cdn.nlark.com/yuque/0/2025/png/44843733/1753955206531-3741a808-152f-438f-b8f2-0d9f153f48d8.png)

+ 设置模型

![](https://cdn.nlark.com/yuque/0/2025/png/44843733/1753955224254-375f5c60-96a0-456b-8c6c-f3986f60466b.png)

## 数据库设计

### 用户表 (users)

存储用户基本信息和权限信息。

| 字段名      | 类型         | 描述                     |
| ----------- | ------------ | ------------------------ |
| id          | INT (主键)   | 用户ID                   |
| username    | VARCHAR(50)  | 用户名（唯一）           |
| password    | VARCHAR(255) | 密码哈希值               |
| avatar      | VARCHAR(500) | 用户头像URL              |
| create_time | TIMESTAMP    | 创建时间                 |
| last_login  | TIMESTAMP    | 最后登录时间             |
| status      | TINYINT      | 用户状态：1-正常，0-禁用 |
| is_admin    | TINYINT      | 是否为管理员：1-是，0-否 |


### API服务商表 (api_providers)

存储AI模型API服务商信息。

| 字段名      | 类型         | 描述                 |
| ----------- | ------------ | -------------------- |
| id          | INT (主键)   | 服务商ID             |
| name        | VARCHAR(100) | 服务商名称           |
| base_url    | VARCHAR(500) | API基础URL           |
| api_key     | VARCHAR(500) | API密钥              |
| description | TEXT         | 服务商描述           |
| status      | TINYINT      | 状态：1-启用，0-禁用 |
| create_time | TIMESTAMP    | 创建时间             |
| update_time | TIMESTAMP    | 更新时间             |


### 模型配置表 (model_configs)

存储AI模型配置信息。

| 字段名      | 类型         | 描述                 |
| ----------- | ------------ | -------------------- |
| id          | INT (主键)   | 模型配置ID           |
| provider_id | INT          | 服务商ID（外键）     |
| model_id    | VARCHAR(200) | 模型ID               |
| model_name  | VARCHAR(200) | 模型显示名称         |
| description | TEXT         | 模型描述             |
| max_tokens  | INT          | 最大token数          |
| status      | TINYINT      | 状态：1-启用，0-禁用 |
| sort_order  | INT          | 排序权重             |
| create_time | TIMESTAMP    | 创建时间             |
| update_time | TIMESTAMP    | 更新时间             |


### 会话表 (chat_sessions)

管理用户对话会话。

| 字段名      | 类型         | 描述                       |
| ----------- | ------------ | -------------------------- |
| id          | INT (主键)   | 会话ID                     |
| session_id  | VARCHAR(100) | 会话标识（唯一）           |
| user_id     | INT          | 用户ID（外键）             |
| title       | VARCHAR(200) | 会话标题                   |
| model_id    | VARCHAR(100) | 当前使用的模型ID           |
| create_time | TIMESTAMP    | 创建时间                   |
| update_time | TIMESTAMP    | 更新时间                   |
| is_active   | TINYINT      | 是否活跃：1-活跃，0-已结束 |


### 对话消息表 (ai_chat_messages)

存储具体的对话消息记录。

| 字段名      | 类型                      | 描述                                |
| ----------- | ------------------------- | ----------------------------------- |
| id          | INT (主键)                | 消息ID                              |
| session_id  | VARCHAR(100)              | 会话ID（外键）                      |
| user_id     | INT                       | 用户ID（外键）                      |
| role        | ENUM('user', 'assistant') | 消息角色：user-用户，assistant-助手 |
| content     | TEXT                      | 消息内容                            |
| create_time | TIMESTAMP                 | 创建时间                            |


## API接口说明

### 用户认证相关

+ `POST /api/register` - 用户注册
+ `POST /api/login` - 用户登录

### 聊天功能相关

+ `GET /api/models` - 获取可用模型列表
+ `POST /api/chat/stream` - 发送消息（流式响应）
+ `GET /api/chat/history` - 获取对话历史
+ `POST /api/chat/history/time-range` - 根据时间范围筛选对话历史
+ `DELETE /api/chat/session/{session_id}` - 删除对话会话

### 用户管理相关

+ `GET /api/user/info` - 获取用户信息
+ `POST /api/user/avatar` - 上传用户头像

## 前端界面介绍

### 登录/注册页面

用户首次使用系统需要注册账号，已有账号的用户可以直接登录。

### 主聊天界面

登录成功后进入主聊天界面，包含以下主要区域：

1. **侧边栏**：显示对话历史记录，支持新建对话和删除对话
2. **聊天区域**：显示对话内容，区分用户消息和AI回复
3. **输入区域**：用户输入消息的地方，支持快捷键发送

> ![](https://cdn.nlark.com/yuque/0/2025/png/44843733/1753969084196-c10761ad-74a6-446f-9499-d68eac78262d.png)

### 模型选择

系统支持多种AI模型，用户可以通过下拉菜单切换不同的AI模型。

![](https://cdn.nlark.com/yuque/0/2025/png/44843733/1753955293707-5d12babd-d2e7-4fe8-8408-acbbbb3ec22c.png)

### 时间范围筛选功能

系统支持根据时间范围筛选对话历史记录：

1. 在侧边栏的对话历史区域上方有时间范围选择器
2. 选择开始日期和结束日期后，系统会自动筛选该时间段内的对话
3. 点击"清除筛选"按钮可恢复显示所有对话历史

![](https://cdn.nlark.com/yuque/0/2025/png/44843733/1753969032139-bcb76d6e-6a49-4e11-84c6-7637a7753f35.png)

![](https://cdn.nlark.com/yuque/0/2025/png/44843733/1753969044143-568642cf-476d-4d50-8035-0c5ba0a8f8fa.png)

![](https://cdn.nlark.com/yuque/0/2025/png/44843733/1753969054967-413e65ad-2e9a-49dc-bedc-b7c5edb352fc.png)

## 使用说明

1. **注册/登录**：首次使用需要注册账号，之后可使用注册的账号登录系统
2. **开始对话**：登录后点击"新建对话"按钮开始与AI聊天
3. **切换模型**：在聊天界面右上角选择不同的AI模型
4. **查看历史**：左侧边栏显示所有对话历史，点击可查看历史对话
5. **时间筛选**：使用侧边栏顶部的时间范围选择器筛选特定时间段的对话
6. **快捷键操作**：使用 Ctrl+Enter 快速发送消息



![](https://cdn.nlark.com/yuque/0/2025/png/44843733/1753969116442-4dfeca07-9329-40b3-957f-618170ba1552.png)

## 支持的AI模型

+ 管理员可以设置支持 openai 格式的

## 项目结构

```plain
ai-helper/
├── static/                 # 静态资源文件
│   ├── index.html          # 主页面
│   ├── admin.html          # 管理员页面
│   ├── script.js           # 主页面JavaScript逻辑
│   ├── admin.js            # 管理员页面JavaScript逻辑
│   └── style.css           # 样式文件
├── main.py                 # 后端主程序
├── config.py               # 配置文件
├── database.sql            # 数据库初始化脚本
├── requirements.txt        # 项目依赖
├── README.md               # 项目说明文档
└── 实操题.md               # 实操题目要求
```

![](https://cdn.nlark.com/yuque/0/2025/png/44843733/1753955469539-b84feb1e-a5eb-433a-9475-e5ac03937b59.png)

