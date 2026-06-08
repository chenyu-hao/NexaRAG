# NexaRAG — 3C 数码智能客服系统

**技术栈：**FastAPI、React、DashScope Qwen、LLM Tool Calling、Agent Loop、LangGraph、ChromaDB、BM25、RRF、JSONL Trace、pytest

**项目描述：**面向 3C 数码产品客服场景构建 RAG 智能问答系统，支持产品咨询、故障排查、购买推荐、竞品对比、闲聊分流和图片问答。项目以“数码客服知识问答”为业务场景，底层拆分出可复用的 Agent 编排、工具调用、知识库检索、会话记忆、上下文压缩和运行追踪能力，将 API 接入、模型调用、工具执行、Prompt 组装、检索召回、记忆注入和结果校验解耦，提升 AI 客服应用的可解释性、稳定性和可测试性。

当前默认运行入口为 `main.py` 中挂载的 `CustomerServiceAgentGroup` 顺序节点编排；仓库同时保留 `agent/graph.py` 的 LangGraph `StateGraph` 实现，用于测试和后续图编排演进。

## 核心亮点

| 特性 | 说明 |
| --- | --- |
| 知识库上传全链路 | `POST /knowledge/upload` 和 `scripts/import_knowledge.py` 支持 TXT 知识导入；后端完成文件读取、空内容校验、MD5 去重、长文分块、DashScope embedding 编码、ChromaDB 向量写入，并在上传后同步 BM25 索引，形成从文件到可检索知识库的完整闭环 |
| RAG 混合检索 | `KnowledgeBase` 统一封装入库和检索；`KnowledgeRetriever` 组合 Chroma 向量语义检索、BM25 关键词检索和 RRF 融合召回，并通过工具层暴露 `search_knowledge`、`search_product_knowledge`、`search_troubleshoot_docs` 等能力，让 Agent 能按意图自主检索证据 |
| Agent 编排与工具调用 | 默认使用 `CustomerServiceAgentGroup` 串联 Vision、Intent、QueryRewrite、ToolReasoning、Answer、Verification 六类节点；`ToolReasoningNode` 基于 LLM Tool Calling 实现多轮工具调用与观察结果回写，仓库同时保留 `agent/graph.py` 的 LangGraph `StateGraph` 版本，支持条件分流和验证失败 retry 的图式编排 |
| 三层记忆系统 | 系统同时维护短期会话记忆、每日 Markdown 记忆和长期稳定记忆；`ConversationMemory` 管理窗口上下文与摘要，`SessionRecorder` 写入 JSONL 节点事件，`DailyMemory` 记录会话快照，`StableMemory` 和 `LongTermMemory` 分别支撑 prompt 注入与用户画像 API |
| 上下文压缩 | `MemoryCompactor` 在长会话中保留头部和尾部关键轮次，将中间历史压缩为任务摘要，并把大工具结果替换成可追踪 placeholder；`/api/context/compact` 可主动触发压缩和每日快照，降低 prompt 噪声和上下文长度风险 |

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
