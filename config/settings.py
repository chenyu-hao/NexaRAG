"""
统一配置文件
所有配置项集中管理，支持环境变量覆盖
"""
import os

# ==================== 服务配置 ====================
HOST = os.getenv("APP_HOST", "127.0.0.1")
PORT = int(os.getenv("APP_PORT", "8080"))

# ==================== DashScope API ====================
dashscope_api_key = os.getenv("DASHSCOPE_API_KEY", "sk-xxxx")

# ==================== 模型配置 ====================
embedding_model = "text-embedding-v4"
chat_model = "qwen3-max"
rerank_model = "gte-rerank-v2"
classifier_model = "qwen-turbo"  # 意图分类、验证、画像提取等轻量任务
vision_model = "qwen3-vl"       # 多模态视觉理解

# ==================== 图片上传限制 ====================
max_images_per_message = 3
max_image_size_mb = 10

# ==================== 文档分块 ====================
chunk_size = 500
chunk_overlap = 100
separators = ["\n\n", "\n", "。", "？", "！", "；", "，", "、", " ", ""]
max_split_char_number = 1000

# ==================== 向量数据库 ====================
collection_name = "rag"
persist_directory = ".chroma_db"

# ==================== 检索配置 ====================
bm25_top_k = 10
vector_top_k = 10
hybrid_top_k = 10
rrf_k = 60
similarity_num = 6
rerank_top_k = 6
startup_sync_knowledge = os.getenv("STARTUP_SYNC_KNOWLEDGE", "false").lower() == "true"

# ==================== 记忆配置 ====================
memory_window_size = 10
session_timeout_hours = 24
enable_session_event_recording = os.getenv("ENABLE_SESSION_EVENT_RECORDING", "true").lower() == "true"
daily_memory_filename = os.getenv("DAILY_MEMORY_FILENAME", "每日记忆.md")
write_daily_summary_file = os.getenv("WRITE_DAILY_SUMMARY_FILE", "true").lower() == "true"
enable_long_term_memory_promotion = os.getenv("ENABLE_LONG_TERM_MEMORY_PROMOTION", "true").lower() == "true"
enable_context_compaction = os.getenv("ENABLE_CONTEXT_COMPACTION", "true").lower() == "true"
context_keep_head_turns = int(os.getenv("CONTEXT_KEEP_HEAD_TURNS", "2"))
context_keep_tail_turns = int(os.getenv("CONTEXT_KEEP_TAIL_TURNS", "6"))
tool_result_placeholder_max_chars = int(os.getenv("TOOL_RESULT_PLACEHOLDER_MAX_CHARS", "200"))
middle_summary_max_chars = int(os.getenv("MIDDLE_SUMMARY_MAX_CHARS", "1200"))

# ==================== 数据路径 ====================
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
md5_path = os.path.join(DATA_DIR, "md5.text")
KNOWLEDGE_DIR = os.path.join(DATA_DIR, "knowledge")
QA_DIR = os.path.join(DATA_DIR, "qa_pairs")
MEMORY_DIR = os.path.join(DATA_DIR, "user_memory")
