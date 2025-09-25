# constants.py
# Centralized constants for CodeBase application

def get_configurable_constant(settings_manager, key: str, default_value):
    """Get a configurable constant from settings, with fallback to default."""
    if settings_manager is None:
        return default_value
    return settings_manager.get('app', key, default_value)

# Default text file extensions that CodeBase recognizes
TEXT_EXTENSIONS_DEFAULT = {
    '.txt', '.py', '.cpp', '.c', '.h', '.java', '.js', '.ts', '.tsx', '.jsx', 
    '.css', '.scss', '.html', '.json', '.md', '.xml', '.svg', '.gitignore', 
    '.yml', '.yaml', '.toml', '.ini', '.properties', '.csv', '.tsv', '.log', 
    '.sql', '.sh', '.bash', '.zsh', '.fish', '.awk', '.sed', '.bat', '.cmd', 
    '.ps1', '.php', '.rb', '.erb', '.haml', '.slim', '.pl', '.lua', '.r', 
    '.m', '.mm', '.asm', '.v', '.vhdl', '.verilog', '.s', '.swift', '.kt', 
    '.kts', '.go', '.rs', '.dart', '.vue', '.pug', '.coffee', '.proto', 
    '.dockerfile', '.make', '.tf', '.hcl', '.sol', '.gradle', '.groovy', 
    '.scala', '.clj', '.cljs', '.cljc', '.edn', '.rkt', '.jl', '.purs', 
    '.elm', '.hs', '.lhs', '.agda', '.idr', '.nix', '.dhall', '.tex', 
    '.bib', '.sty', '.cls', '.cs', '.fs', '.fsx', '.mdx', '.rst', '.adoc', 
    '.org', '.texinfo', '.w', '.man', '.conf', '.cfg', '.env', '.ipynb', 
    '.rmd', '.qmd', '.lock', '.srt', '.vtt', '.po', '.pot', '.mts'
}

# File separator used in content generation
FILE_SEPARATOR = "===FILE_SEPARATOR===\n"

# Application version
VERSION = "3.6"

# Cache configuration
CACHE_MAX_SIZE = 1000  # Maximum number of cached files
CACHE_MAX_MEMORY_MB = 100  # Maximum memory usage in MB

# Path normalization settings
PATH_NORMALIZATION_ENABLED = True  # Enable consistent path normalization
CROSS_PLATFORM_PATHS = True  # Use forward slashes for cross-platform compatibility

# Error handling settings
ERROR_HANDLING_ENABLED = True  # Enable centralized error handling
ERROR_UI_FEEDBACK = True  # Show UI error messages
ERROR_LOGGING_LEVEL = "ERROR"  # Default error logging level
ERROR_RECOVERY_ATTEMPTS = 3  # Number of recovery attempts for recoverable errors

# Logging configuration
DEFAULT_LOG_LEVEL = "INFO"  # Default logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_TO_FILE = True  # Enable file logging
LOG_TO_CONSOLE = True  # Enable console logging
LOG_FILE_PATH = "codebase_debug.log"  # Default log file path
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"  # Log format string

# Security configuration
SECURITY_ENABLED = True  # Enable security validation
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max file size
MAX_TEMPLATE_SIZE = 1024 * 1024   # 1MB max template size
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max content length
SECURITY_STRICT_MODE = True  # Enable strict security validation

# Performance configuration
TREE_MAX_ITEMS = 10000  # Maximum items to process in tree operations
TREE_UI_UPDATE_INTERVAL = 100  # Update UI every N items to prevent blocking
TREE_SAFETY_LIMIT = 10000  # Safety limit to prevent infinite loops

# UI Configuration
DEFAULT_WINDOW_SIZE = "1200x800"
DEFAULT_WINDOW_POSITION = "+100+100"
STATUS_MESSAGE_DURATION = 5000  # 5 seconds
ERROR_MESSAGE_DURATION = 10000  # 10 seconds
WINDOW_TOP_DURATION = 100  # 100ms
LEFT_PANEL_WIDTH = 200
TOOLTIP_DELAY = 500
TOOLTIP_WRAP_LENGTH = 300
DIALOG_MIN_WIDTH = 500
CACHE_OVERHEAD_BYTES = 100
