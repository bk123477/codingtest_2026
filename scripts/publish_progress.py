"""Publish only generated README to a separate branch, without changing main."""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(*args, data=None):
    env = dict(os.environ, GIT_AUTHOR_NAME='github-actions[bot]',
               GIT_AUTHOR_EMAIL='41898282+github-actions[bot]@users.noreply.github.com',
               GIT_COMMITTER_NAME='github-actions[bot]',
               GIT_COMMITTER_EMAIL='41898282+github-actions[bot]@users.noreply.github.com')
    return subprocess.run(['git', *args], input=data, text=True, capture_output=True,
                          cwd=ROOT, env=env, check=True).stdout.strip()


def publish():
    content = (ROOT / '.study/dashboard.md').read_text(encoding='utf-8')
    refs = run('ls-remote', '--heads', 'origin', 'refs/heads/progress')
    parent = None
    if refs:
        run('fetch', 'origin', 'refs/heads/progress')
        parent = run('rev-parse', 'FETCH_HEAD')
    blob = run('hash-object', '-w', '--stdin', data=content)
    tree = run('mktree', data=f'100644 blob {blob}\tREADME.md\n')
    if parent and run('rev-parse', f'{parent}^{{tree}}') == tree:
        print('현황 변경 없음')
        return
    args = ['commit-tree', tree, '-m', 'docs: update study progress']
    if parent:
        args += ['-p', parent]
    commit = run(*args)
    # Fast-forward only: a concurrent external update fails safely, never overwrites.
    run('push', 'origin', f'{commit}:refs/heads/progress')
    print('progress 브랜치 갱신 완료')


if __name__ == '__main__':
    publish()
