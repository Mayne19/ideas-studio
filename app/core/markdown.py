import re

try:
    import markdown as _markdown_lib
except Exception:  # pragma: no cover - fallback kept for local dev without dependency installed
    _markdown_lib = None


def _convert_headings(text: str) -> str:
    text = re.sub(r'(?m)^#### (.+)$', r'<h4>\1</h4>', text)
    text = re.sub(r'(?m)^### (.+)$', r'<h3>\1</h3>', text)
    text = re.sub(r'(?m)^## (.+)$', r'<h2>\1</h2>', text)
    text = re.sub(r'(?m)^# (.+)$', r'<h1>\1</h1>', text)
    return text


def _convert_bold_italic(text: str) -> str:
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'___(.+?)___', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
    return text


def _convert_links(text: str) -> str:
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return text


def _convert_images(text: str) -> str:
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" />', text)
    return text


def _convert_blockquotes(text: str) -> str:
    lines = text.split('\n')
    result = []
    in_blockquote = False
    for line in lines:
        m = re.match(r'^>\s?(.*)$', line)
        if m:
            if not in_blockquote:
                result.append('<blockquote>')
                in_blockquote = True
            result.append(f'<p>{m.group(1)}</p>')
        else:
            if in_blockquote:
                result.append('</blockquote>')
                in_blockquote = False
            result.append(line)
    if in_blockquote:
        result.append('</blockquote>')
    return '\n'.join(result)


def _convert_lists(text: str) -> str:
    lines = text.split('\n')
    result = []
    in_ul = False
    in_ol = False
    for line in lines:
        ul_match = re.match(r'^(\s*)[-*+]\s+(.+)$', line)
        ol_match = re.match(r'^(\s*)\d+\.\s+(.+)$', line)
        if ul_match:
            if in_ol:
                result.append('</ol>')
                in_ol = False
            if not in_ul:
                result.append('<ul>')
                in_ul = True
            result.append(f'<li>{ul_match.group(2)}</li>')
        elif ol_match:
            if in_ul:
                result.append('</ul>')
                in_ul = False
            if not in_ol:
                result.append('<ol>')
                in_ol = True
            result.append(f'<li>{ol_match.group(2)}</li>')
        else:
            if in_ul:
                result.append('</ul>')
                in_ul = False
            if in_ol:
                result.append('</ol>')
                in_ol = False
            result.append(line)
    if in_ul:
        result.append('</ul>')
    if in_ol:
        result.append('</ol>')
    return '\n'.join(result)


def _wrap_paragraphs(text: str) -> str:
    lines = text.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append('')
            continue
        if stripped.startswith('<h') or stripped.startswith('</h') or \
           stripped.startswith('<ul') or stripped.startswith('</ul') or \
           stripped.startswith('<ol') or stripped.startswith('</ol') or \
           stripped.startswith('<li') or stripped.startswith('</li') or \
           stripped.startswith('<blockquote') or stripped.startswith('</blockquote') or \
           stripped.startswith('<p') or stripped.startswith('</p') or \
           stripped.startswith('<img ') or stripped.startswith('<a '):
            result.append(line)
        else:
            result.append(f'<p>{stripped}</p>')
    return '\n'.join(result)


def _clean_horizontal_rules(text: str) -> str:
    text = re.sub(r'(?m)^---+\s*$', '<hr />', text)
    text = re.sub(r'(?m)^\*\*\*+\s*$', '<hr />', text)
    text = re.sub(r'(?m)^___+\s*$', '<hr />', text)
    return text


def markdown_to_html(md: str) -> str:
    if not md:
        return md
    if _markdown_lib is not None:
        html = _markdown_lib.markdown(
            md,
            extensions=["extra", "tables", "sane_lists", "fenced_code", "nl2br"],
            output_format="html5",
        )
        return html.strip()
    html = md
    html = _convert_images(html)
    html = _convert_links(html)
    html = _convert_headings(html)
    html = _convert_bold_italic(html)
    html = _convert_blockquotes(html)
    html = _convert_lists(html)
    html = _clean_horizontal_rules(html)
    html = _wrap_paragraphs(html)
    html = html.replace('\n\n', '\n')
    html = html.strip()
    return html
