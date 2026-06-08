# NexaRAG — 3C 数码智能客服系统 v2.7

基于 ReAct 风格工具调用 + 多模态视觉理解的 RAG 智能问答系统，面向 3C 数码产品客服场景。系统支持产品咨询、故障排查、购买推荐、竞品对比、闲聊分流、图片问答、会话记忆、长期用户画像和知识库上传。

当前默认运行入口为 `main.py` 中挂载的 `CustomerServiceAgentGroup` 顺序节点编排；仓库同时保留 `agent/graph.py` 的 LangGraph `StateGraph` 实现，用于测试和后续图编排演进。

## v2.7 关键特性

| 特性 | 说明 |
| --- | --- |
| ReAct 风格工具推理 | `ToolReasoningNode` 让 LLM 自主决定是否调用知识检索、商品规格、竞品对比、故障排查等工具，最多 5 轮 |
| 多模态视觉理解 | 图片接口将上传图片转为 base64 data URI，再由 `VisionAnalyzer` 调用 Qwen3-VL 识别产品、故障截图和图片语义 |
| 全链路异步化 | API、Agent 节点、LLM 调用和流式输出均采用 async/await |
| 真实流式输出 | `AnswerGenerationNode.stream()` 调用 streaming LLM 逐 token 输出，并在末尾追加 `__CA_META__` 元数据 |
| FastAPI 依赖注入 | `app.state` 统一挂载 `ChatService`、`KnowledgeBase`、`ConversationRegistry`、`MemoryService`、`MemoryCompactor` |
| LLM 实例复用 | `llm`、`light_llm`、`react_llm` 三个共享 ChatTongyi 实例覆盖生成、轻量分类/验证和工具推理 |
| 混合检索 | ChromaDB 向量检索 + BM25(jieba) + RRF 融合，支持知识库同步和工具化查询 |
| 三层记忆 | SQLite 会话历史、JSONL 节点事件、每日 Markdown、长期 `memory.md` 和用户画像 JSON |
| 工作台前端 | React 19 + Vite 6 + TypeScript + Tailwind CSS，提供聊天、会话、诊断、知识库管理等工作台能力 |
| 健康检查 + 请求追踪 | `/health` 端点返回 BM25 文档数和活跃会话数；中间件注入 `X-Request-ID` |
| pytest 测试体系 | 当前收集 110 个测试用例，覆盖配置、RAG、记忆、API、Agent 节点、工具、视觉、前端关键页面 |

## 系统架构

默认运行链路：

```text
用户请求
  -> FastAPI API 层
  -> ChatService
  -> ConversationRegistry / SQLiteStore 恢复或创建会话
  -> MemoryContextBuilder + MemoryCompactor 构建上下文
  -> CustomerServiceAgentGroup
       -> VisionNode
       -> IntentNode
       -> QueryRewriteNode
       -> ToolReasoningNode(ReAct 风格工具循环)
       -> AnswerGenerationNode
       -> VerificationNode
  -> ConversationMemory / SessionRecorder / DailyMemory 写入
  -> API 响应或 StreamingResponse
```

仓库保留的 LangGraph 图实现：

```text
START
  -> classify_intent
  -> chitchat? ---------------------------> output -> END
  -> vision_analyze
  -> rewrite_query
  -> react_generate
  -> verify
  -> pass? output : retry -> react_generate
```

## ReAct 工具循环

```text
ToolReasoningNode:
  构建系统提示 + 长期记忆 + 用户画像 + 对话历史 + 图片识别结果 + 当前问题
    -> react_llm.bind_tools(...)
    -> LLM 选择工具
       -> search_knowledge / search_product_knowledge / search_troubleshoot_docs
       -> compare_products / get_product_specs / get_troubleshoot_guide
    -> 工具返回观察结果
    -> 信息不足时继续调用工具，信息充分时停止
    -> 将 context 和 used_tools 交给 AnswerGenerationNode
```

## LLM 实例分布

| 实例 | 默认模型 | 用途 |
| --- | --- | --- |
| `llm` | `qwen3-max` | 查询改写、闲聊、最终答案生成、真实流式输出 |
| `light_llm` | `qwen-turbo` | 意图分类、答案验证、用户画像提取 |
| `react_llm` | `qwen3-max` | 非流式 ReAct 工具调用循环 |
| `VisionAnalyzer` | `qwen3-vl` | 产品图片、故障截图、多模态场景识别 |

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 编排 | `CustomerServiceAgentGroup` 默认顺序编排；`LangGraph StateGraph` 保留图实现 |
| LLM | DashScope Qwen3-max / Qwen-turbo / Qwen3-VL |
| 向量库 | ChromaDB 持久化 |
| 检索 | BM25(jieba) + Chroma 向量语义 + RRF 融合 + DashScope rerank 支持 |
| 后端 | FastAPI + Uvicorn + Python 3.12+ |
| 前端 | React 19 + Vite 6 + TypeScript + Tailwind CSS 3 |
| 测试 | pytest + pytest-asyncio + httpx |

## 项目结构

```text
├── agent/                  # Agent 编排、节点、视觉、意图、验证、LangGraph 图实现
│   ├── groups/             # CustomerServiceAgentGroup 默认运行编排
│   ├── nodes/              # Vision / Intent / QueryRewrite / ToolReasoning / Answer / Verification
│   ├── dependencies.py     # 共享 LLM、视觉、意图、画像抽取依赖
│   ├── graph.py            # LangGraph StateGraph 实现
│   ├── intent.py           # 意图分类器
│   ├── router.py           # 不同意图的 Prompt 模板选择
│   ├── verifier.py         # 回答质量验证
│   └── vision.py           # Qwen3-VL 图片分析
├── api/                    # FastAPI REST 接口
│   ├── chat.py             # /chat 文本、图片、流式、会话历史和结束会话
│   ├── context.py          # /api/context/compact 上下文压缩
│   ├── knowledge.py        # /knowledge/upload 知识库上传
│   ├── memory.py           # /api/memory/promote-daily 每日记忆提升
│   └── user.py             # /users/{id}/profile 和 /users/sessions
├── core/                   # 应用服务、会话注册、SQLite 持久化、事件记录
│   ├── chat_service.py     # 聊天主编排：会话、记忆、Agent、流式、结束会话
│   ├── conversation_registry.py
│   ├── session_store.py
│   ├── knowledge_service.py # KnowledgeBase 兼容包装
│   └── recorder.py
├── rag/                    # 知识入库、检索、混合召回、重排和评测链路
│   ├── knowledge_base.py   # RAG 统一入口
│   ├── ingestion.py        # 文档读取、MD5 去重、切块、写入 Chroma
│   ├── retriever.py        # 组合向量、BM25、混合检索
│   ├── vector.py           # Chroma 向量检索 + RRF 融合
│   ├── bm25.py             # BM25 关键词检索
│   ├── reranker.py         # gte-rerank-v2 重排序
│   └── evaluation_chain.py # RAG 检索评测链路
├── tools/                  # LangChain StructuredTool 工具集
│   ├── retrieval_tools.py
│   ├── product_tools.py
│   └── toolsets.py
├── memory/                 # 短期对话、长期画像、每日记忆、上下文压缩
│   ├── conversation.py
│   ├── long_term.py
│   ├── memory_context.py
│   ├── memory_service.py
│   ├── memory_compactor.py
│   └── query_rewriter.py
├── frontend/               # React 工作台前端
│   └── src/
│       ├── App.tsx
│       ├── lib/api.ts
│       └── components/
├── data/                   # 样例知识、测试夹具和 QA 数据
├── docs/                   # 测试文档和 message-flow 内部代码解读
├── scripts/import_knowledge.py
├── tests/                  # pytest 测试
├── config/settings.py      # 统一配置
├── main.py                 # FastAPI 应用入口
├── pyproject.toml
└── requirements.txt
```

## 快速启动

后端：

```bash
pip install -r requirements.txt
export DASHSCOPE_API_KEY=sk-your-key
python -m uvicorn main:app --host 127.0.0.1 --port 8080
```

访问 API 文档：

```text
http://127.0.0.1:8080/docs
```

前端：

```bash
cd frontend
npm install
npm run dev
```

打开：

```text
http://localhost:5173
```

如需指定后端地址，创建 `frontend/.env`：

```env
VITE_API_BASE_URL=http://127.0.0.1:8080
```

导入样例知识库：

```bash
python scripts/import_knowledge.py
```

运行测试：

```bash
python -m pytest tests/ -v
```

## API 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/` | 服务状态 |
| `GET` | `/health` | 健康检查、BM25 文档数、活跃会话数 |
| `POST` | `/chat` | 纯文本对话 |
| `POST` | `/chat/stream` | 流式文本对话 |
| `POST` | `/chat/image` | 图片对话，multipart/form-data |
| `POST` | `/chat/image/stream` | 图片流式对话 |
| `POST` | `/chat/{session_id}/end` | 结束会话，写入每日记忆并抽取长期画像 |
| `GET` | `/chat/{session_id}/history` | 获取会话历史 |
| `POST` | `/knowledge/upload` | 上传知识库 TXT 文件并同步索引 |
| `GET` | `/users/{user_id}/profile` | 获取用户画像 |
| `GET` | `/users/sessions` | 会话列表 |
| `POST` | `/api/context/compact` | 压缩指定会话上下文，可写每日快照 |
| `POST` | `/api/memory/promote-daily` | 将每日记忆候选提升到长期稳定记忆 |

## 配置项

配置位于 `config/settings.py`，部分配置支持同名环境变量覆盖。

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_HOST` / `APP_PORT` | `127.0.0.1` / `8080` | 服务地址 |
| `DASHSCOPE_API_KEY` | `sk-xxxx` | DashScope API Key |
| `chat_model` | `qwen3-max` | 主生成模型 |
| `classifier_model` | `qwen-turbo` | 轻量分类、验证、画像提取模型 |
| `vision_model` | `qwen3-vl` | 多模态视觉模型 |
| `rerank_model` | `gte-rerank-v2` | 重排序模型 |
| `embedding_model` | `text-embedding-v4` | 向量嵌入模型 |
| `collection_name` | `rag` | Chroma collection |
| `persist_directory` | `.chroma_db` | Chroma 持久化目录 |
| `bm25_top_k` / `vector_top_k` / `hybrid_top_k` | `10` / `10` / `10` | 召回数量 |
| `rerank_top_k` | `6` | 重排后保留数量 |
| `max_images_per_message` | `3` | 单次最大图片数 |
| `max_image_size_mb` | `10` | 单张图片大小限制 |
| `memory_window_size` | `10` | 短期记忆窗口 |
| `enable_context_compaction` | `true` | 是否启用上下文压缩 |
| `STARTUP_SYNC_KNOWLEDGE` | `false` | 启动时是否从 Chroma 同步 BM25 |

## 文档

当前文档目录只保留测试与流程解读：

| 文档 | 说明 |
| --- | --- |
| `docs/message-flow.md` | 内部代码执行链路和模块解读 |
| `docs/自动测试.md` | 自动化测试方案 |
| `docs/手工测试.md` | 手工测试方案 |
| `docs/Codex自动测试记录1.md` | 自动测试记录 |
| `docs/Codex自动测试记录2.md` | 自动测试记录 |

## 评测

RAG 检索评测链路位于 `rag/evaluation_chain.py`，可基于 `data/qa_pairs/test_qa.json` 计算召回和命中指标。运行完整测试时会覆盖该链路：

```bash
python -m pytest tests/test_rag_chains.py -v
```
