#!/usr/bin/env python3
"""Build a personal/shared study wiki without an API, server, or third-party package."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from socketserver import TCPServer
from pathlib import Path

from study_wiki.build import build, read_records

ROOT = Path(__file__).resolve().parent


class WikiRequestHandler(SimpleHTTPRequestHandler):
    def guess_type(self, path):
        if Path(path).suffix.lower() in ('.py', '.md', '.txt', '.java', '.c', '.cpp', '.kt', '.go', '.rs', '.swift'):
            return 'text/plain; charset=utf-8'
        kind = super().guess_type(path)
        return kind + '; charset=utf-8' if kind.startswith('text/') else kind


class LocalWikiServer(ThreadingHTTPServer):
    def server_bind(self):
        # The reader is loopback-only; avoid a potentially blocking reverse DNS lookup.
        TCPServer.server_bind(self)
        self.server_name = "localhost"
        self.server_port = self.server_address[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('build', 'search'):
        command = commands.add_parser(name)
        command.add_argument('--source-root', type=Path, default=ROOT, help='기록을 읽을 저장소 (읽기 전용)')
        command.add_argument('--include-drafts', action='store_true', help='작성 중 기록도 포함하는 미리보기')
        users = command.add_mutually_exclusive_group()
        users.add_argument('--user', help='이 작성자만 포함')
        users.add_argument('--mine', action='store_true', help='원본 저장소의 .study/config.json 사용자')
        if name == 'build':
            command.add_argument('--output', type=Path, default=ROOT / '.study/wiki')
            command.add_argument('--repo-url', default='', help='GitHub 원본 링크용 HTTPS 저장소 URL')
            command.add_argument('--ref', default='main', help='원본 링크용 브랜치 또는 commit SHA')
        else:
            command.add_argument('query', help='제목·본문·코드·분류에서 검색 (공백으로 나눈 단어 모두 일치)')
    serve = commands.add_parser('serve', help='생성된 Wiki를 로컬에서 보기')
    serve.add_argument('--directory', type=Path, default=ROOT / '.study/wiki')
    serve.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    try:
        if args.command == 'serve':
            if not (args.directory / '.study-wiki-output').is_file():
                raise ValueError('먼저 wiki.py build를 실행하세요.')
            handler = partial(WikiRequestHandler, directory=str(args.directory.resolve()))
            with LocalWikiServer(('127.0.0.1', args.port), handler) as server:
                print(f'Study Wiki: http://127.0.0.1:{server.server_port} (Ctrl+C 종료)', flush=True)
                server.serve_forever()
            return
        if args.mine:
            config = args.source_root / '.study/config.json'
            if not config.is_file():
                raise ValueError('로컬 사용자 설정이 없습니다. --user 사용자명을 지정하세요.')
            args.user = json.loads(config.read_text(encoding='utf-8'))['user']
        if args.command == 'build':
            result = build(args.source_root, args.output, args.include_drafts, args.user, args.repo_url, args.ref)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            tokens = args.query.casefold().split()
            rows = [r for r in read_records(args.source_root, args.include_drafts, args.user) if all(t in r['search'] for t in tokens)]
            for r in rows:
                print(f'{r["date"]} · {r["user"]} · {r["title"]} [{r["status"]}]\n  {r["id"]}/README.md')
            print(f'{len(rows)}건')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f'오류: {exc}\n')
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
