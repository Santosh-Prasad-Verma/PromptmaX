"""Text processing utilities for PromptX."""

import re
import hashlib
from typing import List, Tuple, Optional


def normalize_text(text: str) -> str:
    """Normalize whitespace, remove extra spaces, standardize line breaks."""
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_urls(text: str) -> List[str]:
    """Extract all URLs from text."""
    pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(pattern, text)


def extract_code_blocks(text: str) -> List[Tuple[str, str]]:
    """Extract code blocks with their language identifiers."""
    pattern = r'```(\w*)\n([\s\S]*?)```'
    matches = re.findall(pattern, text)
    return [(lang or 'unknown', code.strip()) for lang, code in matches]


def extract_emails(text: str) -> List[str]:
    """Extract email addresses from text."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(pattern, text)


def extract_numbers(text: str) -> List[str]:
    """Extract numbers and numeric patterns."""
    pattern = r'\b\d+(?:\.\d+)?(?:%|px|em|rem|kg|mb|gb|tb|ms|s|m|h|k|M|B)?\b'
    return re.findall(pattern, text)


def count_sentences(text: str) -> int:
    """Count sentences in text."""
    sentences = re.split(r'[.!?]+', text)
    return len([s for s in sentences if s.strip()])


def calculate_avg_sentence_length(text: str) -> float:
    """Calculate average sentence length in words."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0.0
    lengths = [len(s.split()) for s in sentences]
    return sum(lengths) / len(lengths)


def hash_text(text: str) -> str:
    """Generate deterministic hash for caching."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def detect_language_in_text(text: str) -> Optional[str]:
    """Detect programming language mentioned in text."""
    language_map = {
        'python': r'\b(python|py|django|flask|fastapi|pandas|numpy)\b',
        'javascript': r'\b(javascript|js|node|react|vue|angular|express|next\.?js)\b',
        'typescript': r'\b(typescript|ts)\b',
        'java': r'\b(java|spring|maven|gradle)\b',
        'csharp': r'\b(c#|csharp|\.net|dotnet|asp\.net)\b',
        'cpp': r'\b(c\+\+|cpp)\b',
        'go': r'\b(golang|go\s+lang)\b',
        'rust': r'\b(rust|cargo)\b',
        'ruby': r'\b(ruby|rails|sinatra)\b',
        'php': r'\b(php|laravel|symfony)\b',
        'sql': r'\b(sql|mysql|postgresql|postgres|sqlite|oracle)\b',
        'swift': r'\b(swift|ios|swiftui)\b',
        'kotlin': r'\b(kotlin|android)\b',
    }

    for lang, pattern in language_map.items():
        if re.search(pattern, text, re.IGNORECASE):
            return lang
    return None


def sanitize_input(text):
    if not text:
        return text
    lower = text.lower()
    if "ignore all previous instructions" in lower or "ignore previous instructions" in lower:
        return ""
    sanitized = re.sub(r'[^\x20-\x7E\n\t]', '', str(text))
    return sanitized.strip()
