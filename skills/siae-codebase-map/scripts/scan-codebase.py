#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["tiktoken"]
# ///
"""
Codebase Scanner per DevForge siae-codebase-map
Scansiona una directory, rispetta .gitignore, restituisce file con conteggio token.
Usa tiktoken per una stima token compatibile con Claude.

Esegui con: uv run scan-codebase.py [path]
UV installa automaticamente tiktoken in ambiente isolato.

Basato su Cartographer (https://github.com/kingbootoshi/cartographer) - MIT License
Adattato per DevForge SIAE.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import tiktoken
except ImportError:
    print("ERROR: tiktoken non installato.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Consigliato: installa UV per gestione automatica delle dipendenze:", file=sys.stderr)
    print("  curl -LsSf https://astral.sh/uv/install.sh | sh", file=sys.stderr)
    print("  Poi esegui: uv run scan-codebase.py", file=sys.stderr)
    print("", file=sys.stderr)
    print("Oppure installa manualmente: pip install tiktoken", file=sys.stderr)
    sys.exit(1)

DEFAULT_IGNORE = {
    ".git", ".svn", ".hg", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "venv", ".venv", "env", ".env", "dist",
    "build", ".next", ".nuxt", ".output", "coverage", ".coverage",
    ".nyc_output", "target", "vendor", ".bundle", ".cargo",
    ".DS_Store", "Thumbs.db", "*.pyc", "*.pyo", "*.so", "*.dylib",
    "*.dll", "*.exe", "*.o", "*.a", "*.lib", "*.class", "*.jar",
    "*.war", "*.egg", "*.whl", "*.lock", "package-lock.json",
    "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "Cargo.lock",
    "poetry.lock", "Gemfile.lock", "composer.lock",
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.ico", "*.svg", "*.webp",
    "*.mp3", "*.mp4", "*.wav", "*.avi", "*.mov", "*.pdf",
    "*.zip", "*.tar", "*.gz", "*.rar", "*.7z",
    "*.woff", "*.woff2", "*.ttf", "*.eot", "*.otf",
    "*.min.js", "*.min.css", "*.map", "*.chunk.js", "*.bundle.js",
}


def parse_gitignore(root: Path) -> list:
    gitignore_path = root / ".gitignore"
    patterns = []
    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    return patterns


def matches_pattern(path: Path, pattern: str, root: Path) -> bool:
    import fnmatch
    rel_path = str(path.relative_to(root))
    name = path.name
    if pattern.startswith("!"):
        return False
    if pattern.endswith("/"):
        if not path.is_dir():
            return False
        pattern = pattern[:-1]
    if "/" in pattern:
        if pattern.startswith("/"):
            pattern = pattern[1:]
        return fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(rel_path, pattern + "/**")
    else:
        return fnmatch.fnmatch(name, pattern)


def should_ignore(path: Path, root: Path, gitignore_patterns: list) -> bool:
    import fnmatch
    name = path.name
    for pattern in DEFAULT_IGNORE:
        if "*" in pattern:
            if fnmatch.fnmatch(name, pattern):
                return True
        elif name == pattern:
            return True
    for pattern in gitignore_patterns:
        if matches_pattern(path, pattern, root):
            return True
    return False


def count_tokens(text: str, encoding) -> int:
    try:
        return len(encoding.encode(text))
    except Exception:
        return len(text) // 4


def is_text_file(path: Path) -> bool:
    text_extensions = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".vue", ".svelte",
        ".html", ".htm", ".css", ".scss", ".sass", ".less",
        ".json", ".yaml", ".yml", ".toml", ".xml", ".md", ".mdx",
        ".txt", ".rst", ".sh", ".bash", ".zsh", ".fish",
        ".ps1", ".bat", ".cmd", ".sql", ".graphql", ".gql", ".proto",
        ".go", ".rs", ".rb", ".php", ".java", ".kt", ".kts", ".scala",
        ".clj", ".ex", ".exs", ".erl", ".hs", ".ml", ".fs", ".cs",
        ".vb", ".swift", ".m", ".h", ".hpp", ".c", ".cpp", ".cc",
        ".r", ".R", ".jl", ".lua", ".vim", ".el", ".lisp",
        ".tf", ".hcl", ".dockerfile", ".makefile", ".cmake",
        ".gradle", ".groovy", ".rake", ".gemspec",
        ".ini", ".cfg", ".conf", ".config",
        ".gitignore", ".gitattributes", ".editorconfig",
        ".prettierrc", ".eslintrc", ".stylelintrc", ".babelrc",
    }
    if path.suffix.lower() in text_extensions:
        return True
    text_names = {
        "readme", "license", "licence", "changelog", "authors",
        "contributors", "copying", "dockerfile", "containerfile",
        "makefile", "rakefile", "gemfile", "procfile", "vagrantfile",
    }
    if path.name.lower() in text_names:
        return True
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                return False
            try:
                chunk.decode("utf-8")
                return True
            except UnicodeDecodeError:
                return False
    except Exception:
        return False


def scan_directory(root: Path, encoding, max_file_tokens: int = 50000) -> dict:
    root = root.resolve()
    gitignore_patterns = parse_gitignore(root)
    files = []
    directories = []
    skipped = []
    total_tokens = 0

    def walk(current: Path):
        nonlocal total_tokens
        if should_ignore(current, root, gitignore_patterns):
            return
        if current.is_dir():
            rel_path = str(current.relative_to(root))
            if rel_path != ".":
                directories.append(rel_path)
            try:
                entries = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
                for entry in entries:
                    walk(entry)
            except PermissionError:
                skipped.append({"path": str(current.relative_to(root)), "reason": "permission_denied"})
        elif current.is_file():
            rel_path = str(current.relative_to(root))
            size_bytes = current.stat().st_size
            if size_bytes > 1_000_000:
                skipped.append({"path": rel_path, "reason": "too_large", "size_bytes": size_bytes})
                return
            if not is_text_file(current):
                skipped.append({"path": rel_path, "reason": "binary"})
                return
            try:
                with open(current, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                tokens = count_tokens(content, encoding)
                if tokens > max_file_tokens:
                    skipped.append({"path": rel_path, "reason": "too_many_tokens", "tokens": tokens})
                    return
                files.append({"path": rel_path, "tokens": tokens, "size_bytes": size_bytes})
                total_tokens += tokens
            except Exception as e:
                skipped.append({"path": rel_path, "reason": f"read_error: {str(e)}"})

    walk(root)
    return {
        "root": str(root),
        "files": files,
        "directories": directories,
        "total_tokens": total_tokens,
        "total_files": len(files),
        "skipped": skipped,
    }


def format_tree(scan_result: dict) -> str:
    lines = []
    root_name = Path(scan_result["root"]).name
    lines.append(f"{root_name}/")
    lines.append(f"Totale: {scan_result['total_files']} file, {scan_result['total_tokens']:,} token")
    lines.append("")
    tree: dict = {}
    for f in scan_result["files"]:
        parts = Path(f["path"]).parts
        current = tree
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = f

    def print_tree(node: dict, prefix: str = ""):
        items = sorted(node.items(), key=lambda x: (not isinstance(x[1], dict) or "tokens" in x[1], x[0].lower()))
        for i, (name, value) in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            if isinstance(value, dict) and "tokens" not in value:
                lines.append(f"{prefix}{connector}{name}/")
                print_tree(value, prefix + ("    " if is_last else "│   "))
            else:
                lines.append(f"{prefix}{connector}{name} ({value.get('tokens', 0):,} token)")

    print_tree(tree)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Scansiona un codebase e restituisce file con conteggio token")
    parser.add_argument("path", nargs="?", default=".", help="Path da scansionare (default: directory corrente)")
    parser.add_argument("--format", choices=["json", "tree", "compact"], default="json")
    parser.add_argument("--max-tokens", type=int, default=50000, help="Salta file con più di N token (default: 50000)")
    parser.add_argument("--encoding", default="cl100k_base")
    args = parser.parse_args()

    path = Path(args.path).resolve()
    if not path.exists():
        print(f"ERROR: Path non esiste: {path}", file=sys.stderr)
        sys.exit(1)
    if not path.is_dir():
        print(f"ERROR: Path non e' una directory: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        encoding = tiktoken.get_encoding(args.encoding)
    except Exception as e:
        print(f"ERROR: Encoding '{args.encoding}' non valido: {e}", file=sys.stderr)
        sys.exit(1)

    result = scan_directory(path, encoding, args.max_tokens)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    elif args.format == "tree":
        print(format_tree(result))
    elif args.format == "compact":
        files_sorted = sorted(result["files"], key=lambda x: x["tokens"], reverse=True)
        print(f"# {result['root']}")
        print(f"# Totale: {result['total_files']} file, {result['total_tokens']:,} token")
        print()
        for f in files_sorted:
            print(f"{f['tokens']:>8} {f['path']}")


if __name__ == "__main__":
    main()
