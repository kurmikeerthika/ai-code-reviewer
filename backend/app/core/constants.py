# app/core/constants.py
# Central place for all fixed values used across the application.

# ---------------------------------------------------------------------------
# Supported Programming Languages
# ---------------------------------------------------------------------------

EXTENSION_TO_LANGUAGE = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".sh": "Shell Script",
    ".bash": "Bash Script",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".sql": "SQL",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".scala": "Scala",
}

ALLOWED_EXTENSIONS = set(EXTENSION_TO_LANGUAGE.keys())

# ---------------------------------------------------------------------------
# File Size Limits
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024
MAX_TOTAL_SIZE_BYTES = 5 * 1024 * 1024
MAX_FILES_PER_UPLOAD = 10
CONTENT_PREVIEW_LENGTH = 300

# ---------------------------------------------------------------------------
# API Route Prefixes
# ---------------------------------------------------------------------------

API_V1_PREFIX = "/api/v1"

# ---------------------------------------------------------------------------
# Session ID Settings
# ---------------------------------------------------------------------------

SESSION_ID_LENGTH = 16

# ---------------------------------------------------------------------------
# RAG / Chunking Settings  ← NEW
# ---------------------------------------------------------------------------

# How many lines of code per chunk
CHUNK_SIZE_LINES = 40

# How many lines overlap between consecutive chunks
# Overlap ensures context isn't lost at chunk boundaries
CHUNK_OVERLAP_LINES = 8

# Minimum lines for a chunk to be worth storing
MIN_CHUNK_LINES = 3

# Maximum characters sent to embedding API per chunk
MAX_CHUNK_CHARS = 2000

# How many similar chunks to retrieve during RAG search
RAG_TOP_K_RESULTS = 5

# ChromaDB distance metric — cosine = best for text similarity
CHROMA_DISTANCE_METRIC = "cosine"