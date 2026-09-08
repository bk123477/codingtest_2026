import json
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
TAXONOMY = json.loads((PACKAGE / 'taxonomy.json').read_text(encoding='utf-8'))


PLACEHOLDERS = {'none', 'null', 'n/a', '미분류', '미입력', '없음', '-'}

def is_placeholder(value):
    return isinstance(value,str) and value.strip().casefold() in PLACEHOLDERS

def normalize(values, field):
    aliases = {alias.casefold(): name for name, names in TAXONOMY.get(field, {}).items()
               for alias in [name, *names]}
    if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError(f'{field}: 비어 있지 않은 문자열 배열이 필요합니다.')
    return list(dict.fromkeys(aliases.get(v.strip().casefold(), v.strip()) for v in values if not is_placeholder(v)))


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
