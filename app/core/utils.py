import re
import hashlib
from datetime import date


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-") or "item"


def generate_unique_slug(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    counter = 2
    while f"{base}-{counter}" in existing:
        counter += 1
    return f"{base}-{counter}"


def calculate_word_count(content: str | None) -> int:
    if not content:
        return 0
    text = re.sub(r"<[^>]+>", " ", content)
    return len(text.split())


def mask_secret_key(key: str) -> str:
    if len(key) <= 12:
        return "***"
    return key[:8] + "..." + key[-4:]


def detect_device_from_user_agent(ua: str) -> str:
    ua_lower = ua.lower()
    if re.search(r"mobile|android(?!.*tablet)|iphone|ipod|blackberry|windows phone", ua_lower):
        return "mobile"
    if re.search(r"tablet|ipad|android", ua_lower):
        return "tablet"
    return "desktop"


def detect_browser_from_user_agent(ua: str) -> str:
    if "Edg/" in ua or "Edge/" in ua:
        return "edge"
    if "OPR/" in ua or "Opera/" in ua:
        return "opera"
    if "Chrome/" in ua:
        return "chrome"
    if "Firefox/" in ua:
        return "firefox"
    if "Safari/" in ua:
        return "safari"
    return "other"


def hash_visitor(ip: str, user_agent: str) -> str:
    today = date.today().isoformat()
    raw = f"{today}:{ip}:{user_agent}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
