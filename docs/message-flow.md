# NexaRAG 内部代码执行链路解读

本文只描述当前仓库代码的真实运行方式。默认启动链路来自 `main.py` 中构建的 `CustomerServiceAgentGroup`，而不是旧文档中的 `RagService` 主编排。

## 1. 应用启动

入口文件：`main.py`

启动时完成以下动作：

1. 创建 `FastAPI(title="NexaRAG 智能客服", version="2.7")`。
2. 注册 CORS 中间件。
3. 注册请求追踪中间件：
   - 读取或生成 `X-Request-ID`。
   - 写入 `request.state.request_id`。
   - 在响应头回传 `X-Request-ID`。
   - 记录请求方法、路径、状态码和耗时。
4. 校验 `DASHSCOPE_API_KEY`。
5. 初始化并挂载服务到 `app.state`：
   - `app.state.chat = ChatService(...)`
   - `app.state.knowledge = KnowledgeBase()`
   - `app.state.sessions = ConversationRegistry(...)`
   - `app.state.memory_service = MemoryService(...)`
   - `app.state.context_compactor = MemoryCompactor()`
6. 注册路由：
   - `api.chat`
   - `api.context`
   - `api.knowledge`
   - `api.memory`
   - `api.user`

健康检查：

```text
GET /health
  -> status
  -> knowledge_svc.retriever.bm25.doc_count
  -> len(session_mgr.sessions)
```

## 2. 依赖初始化

文件：`agent/dependencies.py`

`AgentDependencies.from_config()` 创建三类共享 LLM：

| 属性 | 模型 | streaming | 用途 |
| --- | --- | --- | --- |
| `llm` | `config.chat_model`，默认 `qwen3-max` | 是 | 查询改写、闲聊、答案生成、流式输出 |
| `light_llm` | `config.classifier_model`，默认 `qwen-turbo` | 否 | 意图分类、答案验证、用户画像提取 |
| `react_llm` | `config.chat_model`，默认 `qwen3-max` | 否 | ReAct 风格工具调用循环 |

同时初始化：

| 属性 | 代码 | 说明 |
| --- | --- | --- |
| `vision_analyzer` | `VisionAnalyzer()` | 图片理解，使用 Qwen3-VL |
| `intent_classifier` | `IntentClassifier()` | 意图分类 |
| `profile_extractor` | `UserProfileExtractor()` | 结束会话时抽取长期画像 |
| `long_term_factory` | `LongTermMemory` | 写入 `data/user_memory/<user_id>.json` |

## 3. 默认 Agent 编排

文件：`agent/groups/customer_service_group.py`

`build_customer_service_group(...)` 构建默认节点顺序：

```text
VisionNode
  -> IntentNode
  -> QueryRewriteNode
  -> ToolReasoningNode
  -> AnswerGenerationNode
  -> VerificationNode
```

`CustomerServiceAgentGroup.run()` 的执行规则：

1. 将 `AgentInput` 转成可变 `state`。
2. 依次执行每个 node。
3. 节点返回 dict 时合并进 `state`。
4. 如存在 `runtime.recorder`，在节点前后记录：
   - `node_started`
   - `node_finished`
5. 最终用 `AgentOutput.from_state(state)` 生成输出。

`CustomerServiceAgentGroup.stream()` 的特殊点：

1. 遇到支持 `stream()` 的节点时逐 chunk `yield`。
2. 当前支持流式的是 `AnswerGenerationNode`。
3. 流式结束后仍继续执行后续节点，例如 `VerificationNode`。
4. 最终结果保存在 `self.last_output`，供 `ChatService.chat_stream()` 写会话和元数据。

## 4. 请求到回答的主流程

核心文件：`core/chat_service.py`

普通文本对话：

```text
POST /chat
  -> api.chat.chat()
  -> ChatService.chat()
  -> ConversationRegistry.get_or_create()
  -> MemoryContextBuilder.build()
  -> SessionRecorder.record(user_message)
  -> ChatService._build_agent_chat_history()
  -> AgentGroup.run(AgentInput)
  -> ConversationMemory.add_message(user)
  -> ConversationMemory.add_message(assistant)
  -> SessionRecorder.record(assistant_message)
  -> SessionRecorder.record(verification_result)
  -> 返回 answer/session_id/turn_count/intent/verification/image 信息
```

流式文本对话：

```text
POST /chat/stream
  -> api.chat.chat_stream()
  -> StreamingResponse(generate)
  -> ChatService.chat_stream()
  -> AgentGroup.stream()
  -> AnswerGenerationNode.stream()
  -> llm.astream(prompt_text)
  -> 逐 token yield
  -> 写入会话记忆和 recorder
  -> yield __CA_META__{...}__CA_META_END__
```

图片对话：

```text
POST /chat/image 或 /chat/image/stream
  -> UploadFile list
  -> _validate_images()
       - 检查 max_images_per_message
       - 检查 max_image_size_mb
       - 读取 bytes
       - base64 编码
       - 拼接 data:<content-type>;base64,<payload>
  -> ChatService.chat/chat_stream(images=[...])
```

## 5. AgentInput 和 AgentOutput

文件：`agent/schemas.py`

`AgentInput` 是 API/Core 进入 Agent 层的边界对象：

| 字段 | 说明 |
| --- | --- |
| `question` | 当前用户问题 |
| `user_id` | 用户 ID |
| `session_id` | 会话 ID |
| `chat_history` | 压缩后的会话上下文 |
| `user_profile` | 预留用户画像文本 |
| `images` | base64 data URI 图片列表 |
| `memory_context` | 稳定记忆、昨日记忆、今日记忆拼接后的 prompt 上下文 |

`to_state()` 会初始化 Agent 节点共享状态：

```text
question/user_id/session_id/chat_history/user_profile/images/memory_context
intent/rewritten_query/context/answer/verification
image_desc/detected_products/used_tools
```

`AgentOutput.from_state()` 从最终状态中提取：

```text
answer
intent
verification
context
rewritten_query
image_desc
detected_products
used_tools
```

## 6. 节点解读

### VisionNode

文件：`agent/nodes/vision_node.py`

职责：

1. 如果没有图片，直接返回空图片结果。
2. 如果有图片，调用 `VisionAnalyzer.aanalyze(images, question)`。
3. 写入：
   - `image_desc`
   - `detected_products`
   - 清空 `images`，避免 base64 继续向后传递。
4. 如果视觉分析为空且有 recorder，记录 `vision_analysis_empty`。

### IntentNode

文件：`agent/nodes/intent_node.py`

职责：

1. 调用 `IntentClassifier.aclassify(...)`。
2. 传入当前问题、历史上下文、轻量 LLM、是否有图片。
3. 写入结构化意图：

```json
{
  "intent": "product_query",
  "confidence": 0.9
}
```

4. 当意图为 `chitchat` 时写入 `is_chitchat = true`。

### QueryRewriteNode

文件：`agent/nodes/query_rewrite_node.py`

职责：

1. 闲聊直接跳过改写。
2. 如果问题包含无上下文指代词，并且没有历史、图片、产品提示，则返回澄清问题。
3. 正常业务问题调用 `QueryRewriter.arewrite(...)` 做指代消解和省略补全。
4. 写入 `rewritten_query`。

澄清分支会写入：

```text
needs_clarification = true
answer = Which product are you asking about? ...
```

### ToolReasoningNode

文件：`agent/nodes/tool_reasoning_node.py`

职责：

1. 闲聊直接返回 `context = 闲聊`，不调用工具。
2. 需要澄清时直接跳过工具。
3. 业务问题交给 `LLMToolReasoningRunner`。

`LLMToolReasoningRunner` 的输入由以下内容拼接：

```text
长期记忆 memory_context
用户画像 user_profile
对话历史 chat_history
图片识别结果 image_desc/detected_products
当前问题 question
```

工具循环：

1. `react_llm.bind_tools(tools)`。
2. 用 `agent.router.get_prompt(intent)` 选择系统提示。
3. LLM 返回 tool_calls 时执行对应工具。
4. 工具结果以 `ToolMessage` 追加回 messages。
5. 最多循环 `max_iterations=5`。
6. 输出：
   - `context`：工具返回内容拼接。
   - `used_tools`：工具名和参数。

### AnswerGenerationNode

文件：`agent/nodes/answer_generation_node.py`

职责：

1. 如果需要澄清，直接返回澄清文案。
2. 如果是闲聊，构建闲聊 prompt。
3. 如果是业务问题：
   - 根据意图选择 prompt。
   - 注入工具 `context`。
   - 注入长期记忆、用户画像、历史、图片识别结果、当前问题。
4. 普通模式调用 `llm.ainvoke(prompt_text)`。
5. 流式模式调用 `llm.astream(prompt_text)` 并逐 token yield。

### VerificationNode

文件：`agent/nodes/verification_node.py`

职责：

1. 闲聊、澄清、空答案直接跳过。
2. 业务答案调用 `AnswerVerifier.averify(question, answer, context, llm)`。
3. 输出 `verification`。

当前默认 `CustomerServiceAgentGroup` 不做验证失败后的自动 retry；自动 retry 逻辑存在于 `agent/graph.py` 的 LangGraph 版本中。

## 7. LangGraph 图实现

文件：`agent/graph.py`

该文件保留了另一套图编排：

```text
START
  -> classify_intent
  -> route_intent
       -> chitchat
       -> vision_analyze
  -> rewrite_query
  -> react_generate
  -> verify
  -> check_verify
       -> output
       -> retry -> react_generate
  -> END
```

它的特点：

1. 使用 `StateGraph(AgentState)`。
2. `react_generate` 内部直接实现 ReAct 工具循环。
3. `verify` 失败且 `retry_count < 1` 时回到 `react_generate`。
4. 当前 `main.py` 没有挂载这张图作为默认运行入口。

## 8. 工具层

目录：`tools/`

工具构建入口：

```text
build_customer_service_toolset(knowledge_base)
  -> build_retrieval_tools(knowledge_base)
  -> build_product_tools(knowledge_base)
```

检索工具：

| 工具 | 说明 |
| --- | --- |
| `search_knowledge(query, top_k=6)` | 通用知识库检索 |
| `search_product_knowledge(product_name, top_k=6)` | 指定产品检索 |
| `search_troubleshoot_docs(problem, top_k=8)` | 故障排查资料检索 |

产品工具：

| 工具 | 说明 |
| --- | --- |
| `compare_products(product_names)` | 多产品对比检索 |
| `get_product_specs(product_name)` | 获取产品规格资料 |
| `get_troubleshoot_guide(problem)` | 获取故障排查指南 |

所有工具通过 `StructuredTool.from_function(...)` 暴露给 LLM。

## 9. RAG 入库和检索

统一入口：`rag/knowledge_base.py`

`KnowledgeBase` 聚合两条链：

```text
KnowledgeIngestionChain
  -> KnowledgeIngestion

QuestionAnswerRetrievalChain
  -> KnowledgeRetriever
```

入库流程：

```text
KnowledgeBase.add_document(text, source)
  -> KnowledgeIngestion.add_document()
  -> 空文本检查
  -> MD5 去重，记录到 data/md5.text
  -> 长文本按 chunk_size/chunk_overlap 切块
  -> 写入 Chroma(collection_name=config.collection_name)
```

检索流程：

```text
KnowledgeBase.search_as_documents(query)
  -> QuestionAnswerRetrievalChain.search_as_documents()
  -> KnowledgeRetriever.search_as_documents()
  -> HybridRetriever.search_as_documents()
       -> BM25Retriever.search()
       -> VectorRetriever.search()
       -> RRF fusion
       -> 转为 LangChain Document
```

BM25 同步：

```text
KnowledgeBase.sync_index()
  -> 从 Chroma collection 分批读取 documents/metadatas
  -> BM25Retriever.clear()
  -> BM25Retriever.add_documents(...)
  -> 返回同步文档数
```

上传接口：

```text
POST /knowledge/upload
  -> 读取 UploadFile UTF-8 内容
  -> knowledge.add_document(content, filename)
  -> knowledge.sync_index()
```

导入脚本：

```text
python scripts/import_knowledge.py
  -> 遍历 data/3c_knowledge/*.txt
  -> KnowledgeService.upload(...)
  -> KnowledgeService.sync_index()
```

## 10. 会话和持久化

目录：`core/`

`ConversationRegistry` 负责运行时会话注册：

1. `get_or_create(session_id, user_id)` 创建或恢复会话。
2. 内存中保存 `ConversationState`。
3. 超过 `session_timeout_hours` 的会话会被移除。
4. 底层 repository 默认是 `SQLiteStore`。

`SQLiteStore` 持久化到 `data/sessions.db`：

| 表 | 说明 |
| --- | --- |
| `sessions` | 会话 ID、用户 ID、创建时间、最后活跃时间 |
| `messages` | 会话消息、角色、图片数、时间戳 |
| `session_summary` | 压缩摘要 |

`ConversationMemory` 负责短期上下文：

1. 保存 user/assistant 消息。
2. 超过窗口后触发 `_compress()`。
3. 有 LLM 时调用模型摘要旧消息。
4. 无 LLM 时使用规则摘要 fallback。
5. 通过回调写入 SQLite。

## 11. 记忆系统

目录：`memory/`

三类记忆来源：

| 类型 | 文件/存储 | 用途 |
| --- | --- | --- |
| 短期记忆 | `ConversationMemory` + SQLite | 当前会话上下文 |
| 每日记忆 | `data/memory/<user_id>/daily/YYYY-MM-DD.md` | 会话结束或压缩时写入快照 |
| 稳定记忆 | `data/memory/<user_id>/memory.md` | prompt 注入的长期稳定事实 |
| 用户画像 | `data/user_memory/<user_id>.json` | `/users/{id}/profile` 返回 |

`MemoryContextBuilder.build(user_id)` 会读取：

```text
StableMemory(memory.md)
Yesterday DailyMemory
Today DailyMemory
```

然后拼接为 prompt-ready 文本传入 `AgentInput.memory_context`。

`MemoryService.record_daily_snapshot(...)` 会生成包含以下段落的 Markdown：

```text
本轮/本次请求
执行动作
已完成
未完成
失败/阻塞
重要事实
长期记忆候选
```

`MemoryService.promote_daily_to_stable(...)` 会从每日记忆中抽取长期候选，去重后写入稳定记忆。

`MemoryCompactor.compact(...)` 负责压缩上下文：

1. 标准化消息。
2. 将大工具结果替换为 placeholder。
3. 按 turn 分组。
4. 保留头部若干轮和尾部若干轮。
5. 中间部分用 LLM 或规则 fallback 摘要。
6. 返回 `CompactResult`。

## 12. API 层

目录：`api/`

| 文件 | 路由前缀 | 职责 |
| --- | --- | --- |
| `chat.py` | `/chat` | 文本/图片/流式聊天、结束会话、历史查询 |
| `knowledge.py` | `/knowledge` | 上传知识库并同步索引 |
| `user.py` | `/users` | 查询用户画像和会话列表 |
| `context.py` | `/api/context` | 压缩指定会话上下文 |
| `memory.py` | `/api/memory` | 每日记忆提升到稳定记忆 |

API 层原则：

1. 只做输入校验、文件读取和服务调用。
2. 不直接持有 RAG 或 LLM 逻辑。
3. 通过 `request.app.state` 获取服务实例。

## 13. 前端链路

目录：`frontend/`

技术栈：

```text
React 19
Vite 6
TypeScript 5.7
Tailwind CSS 3
lucide-react
```

关键文件：

| 文件 | 说明 |
| --- | --- |
| `frontend/src/App.tsx` | 根组件和全局状态 |
| `frontend/src/lib/api.ts` | 后端 API 封装 |
| `frontend/src/components/Toolbar.tsx` | 顶部工具栏 |
| `frontend/src/components/SessionSidebar.tsx` | 会话侧栏 |
| `frontend/src/components/ChatPanel.tsx` | 聊天主面板 |
| `frontend/src/components/MessageBubble.tsx` | 消息展示 |
| `frontend/src/components/DiagnosticsPanel.tsx` | 诊断信息 |
| `frontend/src/components/KnowledgePanel.tsx` | 知识库管理 |
| `frontend/src/components/MemoryControls.tsx` | 记忆操作 |

前端请求路径由 `VITE_API_BASE_URL` 控制，默认连接本地后端。

## 14. 测试覆盖

当前 `python -m pytest --collect-only -q` 收集 110 个测试用例。

主要覆盖：

| 测试文件 | 覆盖内容 |
| --- | --- |
| `tests/test_api.py` | 根接口、健康检查、请求 ID、用户 API |
| `tests/test_chat_api_service.py` | chat API 到 ChatService 的边界 |
| `tests/test_chat_service_agent_group.py` | ChatService、AgentGroup、记忆、流式元数据 |
| `tests/test_agent_group_nodes.py` | AgentGroup 节点顺序和流式执行 |
| `tests/test_agent_nodes.py` | 各 Agent 节点行为 |
| `tests/test_agent_node_runners.py` | 工具推理 runner 和答案生成 runner |
| `tests/test_retrieval.py` | BM25、HybridRetriever、RRF |
| `tests/test_rag_knowledge_base.py` | KnowledgeBase 统一入口 |
| `tests/test_rag_chains.py` | 入库链、检索链、评测链 |
| `tests/test_memory*.py` | 短期记忆、三层记忆、压缩、提升、API |
| `tests/test_vision.py` | VisionAnalyzer 和图片字段 |
| `tests/test_frontend_knowledge_page.py` | 前端知识库页面入口 |
| `tests/test_import_knowledge_script.py` | 知识库导入脚本兼容当前 RAG 架构 |

## 15. 当前文档边界

`docs/` 目录当前只保留：

```text
message-flow.md
自动测试.md
手工测试.md
Codex自动测试记录1.md
Codex自动测试记录2.md
```

规划、设计、阶段计划和代码修改清单已移出文档保留范围。
