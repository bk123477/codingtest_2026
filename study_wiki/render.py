"""Small, escaped Markdown renderer. Raw HTML and executable URLs stay inert."""
import html
import re
from urllib.parse import urlsplit


def safe_url(value):
    return bool(value and not any(ord(c) < 32 for c in value)
                and (urlsplit(value).scheme.lower() in ('https', 'http')
                     or (not urlsplit(value).scheme and not value.startswith(('//', '\\')))))


def inline(text, resolve=lambda x: x):
    tokens = re.compile(r'(`[^`]+`|\[[^\]\n]+\]\([^\s)]+\)|\*\*[^*]+\*\*)')
    result = []
    for part in tokens.split(text):
        if part.startswith('`') and part.endswith('`'):
            result.append('<code>' + html.escape(part[1:-1]) + '</code>')
        elif part.startswith('**') and part.endswith('**'):
            result.append('<strong>' + html.escape(part[2:-2]) + '</strong>')
        elif re.fullmatch(r'\[[^\]\n]+\]\([^\s)]+\)', part):
            label, target = re.fullmatch(r'\[([^\]]+)\]\(([^)]+)\)', part).groups()
            target = resolve(target)
            if safe_url(target):
                result.append(f'<a href="{html.escape(target, quote=True)}" rel="noopener noreferrer">{html.escape(label)}</a>')
            else:
                result.append(html.escape(label))
        else:
            result.append(html.escape(part))
    return ''.join(result)


def markdown(text, resolve=lambda x: x):
    # Comments outside code blocks are template instructions, not reader content.
    lines = text.splitlines()
    output, paragraph, listing = [], [], None
    def flush():
        if paragraph:
            output.append('<p>' + '<br>'.join(inline(s, resolve) for s in paragraph) + '</p>')
            paragraph.clear()
    def close_list():
        nonlocal listing
        if listing:
            output.append(f'</{listing}>')
            listing = None
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith('<!--'):
            while '-->' not in line and i + 1 < len(lines):
                i += 1
                line = lines[i]
            i += 1
            continue
        fence = re.match(r'^\s*(`{3,}|~{3,})(.*)$', line)
        if fence:
            flush(); close_list()
            marker, language = fence.groups()
            code = []
            i += 1
            while i < len(lines) and not re.match(r'^\s*' + re.escape(marker[0]) + '{' + str(len(marker)) + r',}\s*$', lines[i]):
                code.append(lines[i]); i += 1
            output.append('<pre><code>' + html.escape('\n'.join(code)) + '</code></pre>')
        elif re.match(r'^#{1,6}\s', line):
            flush(); close_list()
            head, body = line.split(' ', 1)
            level = min(len(head) + 1, 6)
            output.append(f'<h{level}>' + inline(body, resolve) + f'</h{level}>')
        elif i + 1 < len(lines) and '|' in line and re.fullmatch(r'\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*', lines[i + 1]):
            flush(); close_list()
            cells = lambda s: s.strip().strip('|').split('|')
            output.append('<div class="table-scroll"><table><thead><tr>' + ''.join('<th>' + inline(c.strip(), resolve) + '</th>' for c in cells(line)) + '</tr></thead><tbody>')
            i += 2
            while i < len(lines) and '|' in lines[i] and lines[i].strip():
                output.append('<tr>' + ''.join('<td>' + inline(c.strip(), resolve) + '</td>' for c in cells(lines[i])) + '</tr>')
                i += 1
            output.append('</tbody></table></div>')
            continue
        elif re.match(r'^\s*(?:[-*+] |\d+\. )', line):
            flush()
            match = re.match(r'^\s*([-*+]|\d+\.) (.*)', line)
            kind = 'ol' if match[1][0].isdigit() else 'ul'
            if listing != kind:
                close_list(); listing = kind; output.append(f'<{kind}>')
            output.append('<li>' + inline(match[2], resolve) + '</li>')
        elif line.startswith('> '):
            flush(); close_list()
            output.append('<blockquote>' + inline(line[2:], resolve) + '</blockquote>')
        elif not line.strip():
            flush(); close_list()
        else:
            close_list(); paragraph.append(line)
        i += 1
    flush(); close_list()
    return '\n'.join(output)
