# constants.py
# Centralized constants for CodeBase application

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
VERSION = "3.2"

# Cache configuration
CACHE_MAX_SIZE = 1000  # Maximum number of cached files
CACHE_MAX_MEMORY_MB = 100  # Maximum memory usage in MB
