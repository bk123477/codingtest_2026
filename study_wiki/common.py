import json
import unicodedata
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
TAXONOMY = json.loads((PACKAGE / 'taxonomy.json').read_text(encoding='utf-8'))


PLACEHOLDERS = {'none', 'null', 'n/a', '미분류', '미입력', '없음', '-'}

def is_placeholder(value):
    return isinstance(value,str) and value.strip().casefold() in PLACEHOLDERS

def term_key(value):
    """Spacing, Unicode presentation and case never define a new category."""
    return ''.join(unicodedata.normalize('NFKC', value).casefold().split())


def alias_map(field):
    groups = TAXONOMY.values() if field == 'tags' else [TAXONOMY.get(field, {})]
    aliases = {}
    for group in groups:
        for name, names in group.items():
            for alias in [name, *names]:
                key = term_key(alias)
                if key in aliases and aliases[key] != name:
                    raise ValueError(f'분류 별칭 충돌: {alias}')
                aliases[key] = name
    return aliases


def normalize(values, field):
    aliases = alias_map(field)
    if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError(f'{field}: 비어 있지 않은 문자열 배열이 필요합니다.')
    result = {}
    for value in values:
        if is_placeholder(value):
            continue
        name = aliases.get(term_key(value), ' '.join(unicodedata.normalize('NFKC', value).split()))
        result.setdefault(term_key(name), name)
    return list(result.values())


def classify(record):
    """Only curated core concepts become facets; unknown terms remain searchable.

    No fuzzy matching: an unseen technique cannot safely be assigned a meaning.
    Legacy metadata is projected without rewriting the author's source files.
    """
    values = []
    for field in ('data_structures', 'algorithms', 'tags'):
        values.extend(normalize(record.get(field, []), 'tags'))
    values = normalize(values, 'tags')
    known = alias_map('tags')
    return {
        'data_structures': [v for v in dict.fromkeys(values) if v in TAXONOMY['data_structures']],
        'algorithms': [v for v in dict.fromkeys(values) if v in TAXONOMY['algorithms']],
        'tags': [],
        'keywords': [v for v in dict.fromkeys(values) if term_key(v) not in known],
    }


def safe_file(root, path):
    """Never read a symlink or a file outside the selected source tree."""
    root = root.resolve()
    if not path.is_absolute():
        path = root / path
    if not path.resolve().is_relative_to(root):
        raise ValueError(f'원본 폴더 밖의 경로: {path}')
    current = path
    while True:
        if current.is_symlink():
            raise ValueError(f'심볼릭 링크는 지원하지 않습니다: {path}')
        if current.resolve() == root:
            break
        if current == current.parent:
            raise ValueError(f'원본 경로를 확인할 수 없습니다: {path}')
        current = current.parent
    if not path.is_file():
        raise ValueError(f'파일이 없습니다: {path}')
    return path
