from __future__ import annotations

import json
import re
from typing import Any


def safe_json_load(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default
    return default


def safe_json_dump(value: Any, default: str = "null") -> str:
    if value is None:
        return default
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return default


def word_count_from_html(content: str | None) -> int:
    if not content:
        return 0
    text = re.sub(r"<[^>]+>", " ", content)
    return len(text.split())


def extract_headings_from_html(content: str) -> list[dict]:
    headings: list[dict] = []
    for match in re.finditer(r"<h([2-4])[^>]*>(.*?)</h\1>", content or "", re.IGNORECASE | re.DOTALL):
        text = re.sub(r"<[^>]+>", " ", match.group(2)).strip()
        headings.append({"level": int(match.group(1)), "text": text})
    return headings


def extract_links_from_html(content: str) -> list[dict]:
    links: list[dict] = []
    for match in re.finditer(r'<a\s[^>]*href="([^"]*)"[^>]*>(.*?)</a>', content or "", re.IGNORECASE | re.DOTALL):
        links.append({"url": match.group(1), "text": re.sub(r"<[^>]+>", " ", match.group(2)).strip()})
    return links


def strip_html(content: str) -> str:
    if not content:
        return ""
    with_breaks = re.sub(r"</(p|div|li|h[1-6]|blockquote|tr|table|ul|ol)>", "\n", content, flags=re.IGNORECASE)
    return re.sub(r"<[^>]+>", " ", with_breaks)


def normalize_text(text: str) -> str:
    text = strip_html(text).lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def detect_title_case_french(text: str) -> bool:
    if not text:
        return False
    words = text.split()
    if len(words) < 3:
        return False
    upper = sum(1 for w in words if w and w[0].isupper())
    return upper >= len(words) * 0.7


def detect_long_dash(text: str) -> list[str]:
    return list(set(re.findall(r"[—–]", text)))


def detect_h2_directly_followed_by_h3(content: str) -> list[str]:
    issues: list[str] = []
    pattern = re.compile(r"<h2[^>]*>.*?</h2>\s*(?:\s*<(?!h[2-6])[^>]*>.*?</[^>]+>\s*)*<h3[^>]*>", re.IGNORECASE | re.DOTALL)
    for match in pattern.finditer(content or ""):
        seq = content[max(0, match.start() - 20):match.end() + 20]
        issues.append(seq[:100])
    return issues


def detect_isolated_h3(content: str) -> bool:
    headings = extract_headings_from_html(content)
    i = 0
    while i < len(headings):
        h = headings[i]
        if h["level"] != 2:
            i += 1
            continue
        h3_count = 0
        j = i + 1
        while j < len(headings) and headings[j]["level"] > 2:
            if headings[j]["level"] == 3:
                h3_count += 1
            j += 1
        if h3_count == 1:
            return True
        i = j
    return False


def detect_abusive_bold(content: str) -> list[dict]:
    issues: list[dict] = []
    html = content or ""
    strong_patterns = [
        (r"<(?:strong|b)>(?:[^<]+</(?:strong|b)>\s*?){10,}</?(?:p|div|li)>", "trop_de_gras"),
        (r"<(?:p|div|li)[^>]*>(?:\s*<(?:strong|b)>[^<]+</(?:strong|b)>\s*?){5,}</(?:p|div|li)>", "ligne_gras_entière"),
    ]
    for pattern, reason in strong_patterns:
        for m in re.finditer(pattern, html, re.IGNORECASE):
            issues.append({"reason": reason, "match": m.group()[:100]})
    return issues


def detect_ai_phrases(content: str) -> list[str]:
    text = (content or "").lower()
    patterns = [
        "il est recommandé de",
        "il est conseillé de",
        "il est important de noter que",
        "dans le monde numérique d'aujourd'hui",
        "de nos jours",
        "en conclusion, il convient de",
        "cet article explore",
        "plongeons dans",
        "il est essentiel de comprendre que",
        "dans cet article, nous allons voir",
        "il ne faut pas oublier que",
    ]
    return [p for p in patterns if p in text]


def detect_list_length_issues(content: str) -> list[dict]:
    issues: list[dict] = []
    for match in re.finditer(r"<(?:ul|ol)[^>]*>(.*?)</(?:ul|ol)>", content or "", re.IGNORECASE | re.DOTALL):
        items = re.findall(r"<li[^>]*>(.*?)</li>", match.group(1), re.IGNORECASE | re.DOTALL)
        if len(items) > 10:
            issues.append({"reason": "liste_trop_longue", "count": len(items), "sample": items[0][:80]})
        for item in items:
            text = strip_html(item)
            if len(text.split()) > 40:
                issues.append({"reason": "element_liste_trop_long", "text": text[:80]})
    return issues
