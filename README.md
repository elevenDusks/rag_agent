# My RAG Agent

智能问答系统，支持 RAG 知识库问答和 Agent 智能体模式。

## 功能特性

### 双模式切换
- **京东客服模式**：基于 RAG 知识库的智能客服，解答购物、配送、售后等问题
- **Agent 智能体模式**：基于 ReAct 架构的智能助手，可调用多种工具（网络搜索、知识库、计算器等）

### 后端能力
- **RAG 知识库问答**：支持京东帮助文档、法律条文等知识库的混合检索与重排序
- **ReAct Agent**：支持工具调用的智能体，可自主决策使用工具获取信息
- **多级记忆系统**：
  - 工作记忆：会话级上下文管理
  - 情景记忆：历史对话持久化存储
  - 语义记忆：向量化的知识摘要
- **认证系统**：JWT 令牌认证，支持登录注册

### 前端特性
- 现代化 React + TypeScript + Ant Design UI
- 实时流式输出
- 消息持久化

## 技术栈

### 后端
- FastAPI + Uvicorn
- LangChain / LangGraph (ReAct Agent)
- ChromaDB (向量数据库)
- MySQL 8.0 (用户数据、会话记录)
- Redis 7 (缓存、消息队列)
- Sentence Transformers + BGE Reranker (嵌入与重排序)
- Docker 容器化部署

### 前端
- React 18 + TypeScript
- Vite 构建工具
- Ant Design 5 组件库
- Axios HTTP 客户端

## 快速开始

### 环境要求
- Docker & Docker Compose
- OpenAI API Key (或其他兼容 API)

### 配置

复制 `.env.example` 或创建 `.env` 文件：

```env
# OpenAI 配置
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-ada-002

# 向量数据库
CHROMA_NAME_JD=jd_help
CHROMA_NAME_LAWS=laws
CHROMA_NAME_EXAMPLES=examples
CROSS_ENCODER_NAME=BAAI/bge-reranker-base

# MySQL
MYSQL_PASSWORD=123456
MYSQL_DATABASE=agent

# Redis
REDIS_PASSWORD=123456

# JWT
JWT_SECRET_KEY=your-secret-key-min-32-chars
```

### 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

访问 http://localhost 查看前端界面。

## 项目结构

```
my-rag-agent/
├── backend/
│   └── src/rag_agent/
│       ├── agent/           # Agent 核心模块
│       │   ├── core/       # ReAct Agent 实现
│       │   ├── prompts/    # 提示词模板
│       │   └── tools/      # 工具注册与实现
│       ├── api/            # API 路由
│       ├── auth/           # 认证模块
│       ├── core/           # 核心配置
│       ├── db/             # 数据库客户端
│       ├── memroy/         # 记忆系统
│       ├── models/         # 数据模型
│       └── rag/            # RAG 管道
├── frontend/
│   └── src/
│       ├── components/     # React 组件
│       ├── services/       # API 服务
│       └── types/          # TypeScript 类型
├── docker-compose.yml      # Docker 编排配置
├── Dockerfile.backend      # 后端构建文件
└── Dockerfile.frontend    # 前端构建文件
```

## API 接口

### 认证
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/refresh` - 刷新令牌

### 聊天
- `POST /api/chat/rag` - RAG 问答
- `POST /api/chat/stream` - 流式 RAG 问答
- `POST /api/chat/agent` - Agent 问答
- `POST /api/chat/agent/stream` - 流式 Agent 问答

### 知识库管理
- `POST /api/ingest` - 导入知识库文档
- `DELETE /api/ingest` - 清除知识库

## 开发

### 本地运行后端

```bash
cd backend
pip install -r requirements.txt
uvicorn rag_agent.main:app --reload --port 8000
```

### 本地运行前端

```bash
cd frontend
npm install
npm run dev
```

## License

MIT
