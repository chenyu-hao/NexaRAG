"""
NexaRAG 智能客服系统 - 入口
"""
import uuid
import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from core.chat_service import ChatService
from agent.groups import build_customer_service_group
from agent.dependencies import AgentDependencies
from rag.knowledge_base import KnowledgeBase
from core.conversation_registry import ConversationRegistry
from core.session_store import SQLiteStore
from api import chat, context as context_api, knowledge, memory as memory_api, user
from memory.memory_compactor import MemoryCompactor
from memory.memory_service import MemoryService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="NexaRAG 智能客服", version="2.7")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


# 请求追踪中间件
@app.middleware("http")
async def request_tracing(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    request.state.request_id = request_id
    start = time.time()
    logger.info("[%s] %s %s", request_id, request.method, request.url.path)
    response = await call_next(request)
    elapsed = time.time() - start
    response.headers["X-Request-ID"] = request_id
    logger.info("[%s] %s %s → %d (%.2fs)", request_id, request.method, request.url.path, response.status_code, elapsed)
    return response


# 启动校验
from config import settings as config
if not config.dashscope_api_key:
    raise RuntimeError(
        "DASHSCOPE_API_KEY 未设置。请在环境变量中设置：\n"
        "  export DASHSCOPE_API_KEY=sk-xxxx\n"
        "或修改 config/settings.py 中的 dashscope_api_key"
    )

# 初始化服务并挂载到 app.state
agent_deps = AgentDependencies.from_config()
knowledge_svc = KnowledgeBase()
if config.startup_sync_knowledge:
    knowledge_svc.sync_index()
session_mgr = ConversationRegistry(
    llm=agent_deps.llm,
    store=SQLiteStore(),  # 持久化到 data/sessions.db，重启不丢失
)
agent_group = build_customer_service_group(
    vision_analyzer=agent_deps.vision_analyzer,
    intent_classifier=agent_deps.intent_classifier,
    chat_llm=agent_deps.llm,
    light_llm=agent_deps.light_llm,
    react_llm=agent_deps.react_llm,
    knowledge_base=knowledge_svc,
)
chat_svc = ChatService(
    conversations=session_mgr,
    agent_group=agent_group,
    session_ender=agent_deps,
)

app.state.chat = chat_svc
app.state.knowledge = knowledge_svc
app.state.sessions = session_mgr
app.state.memory_service = MemoryService(chat_svc.memory_root)
app.state.context_compactor = MemoryCompactor()

# 注册路由
app.include_router(chat.router)
app.include_router(context_api.router)
app.include_router(knowledge.router)
app.include_router(memory_api.router)
app.include_router(user.router)


@app.get("/")
async def root():
    return {"service": "NexaRAG", "version": "2.7", "status": "running"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "bm25_docs": knowledge_svc.retriever.bm25.doc_count,
        "active_sessions": len(session_mgr.sessions),
    }
