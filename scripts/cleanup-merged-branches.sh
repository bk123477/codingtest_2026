#!/usr/bin/env bash

set -euo pipefail

REMOTE="${1:-origin}"
BASE_BRANCH="${2:-main}"

REPOSITORY_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Git 저장소 안에서 실행하세요." >&2
  exit 1
}
cd "$REPOSITORY_ROOT"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "커밋되지 않은 변경사항이 있어 중단합니다. 먼저 커밋하거나 별도로 보관하세요." >&2
  exit 1
fi

CURRENT_BRANCH="$(git branch --show-current)"
if [[ "$CURRENT_BRANCH" != "$BASE_BRANCH" ]]; then
  git switch "$BASE_BRANCH"
fi

git fetch --prune "$REMOTE"
git pull --ff-only "$REMOTE" "$BASE_BRANCH"

deleted=0
while IFS= read -r branch; do
  [[ -z "$branch" || "$branch" == "$BASE_BRANCH" ]] && continue

  if git branch -d "$branch"; then
    echo "로컬 브랜치 삭제: $branch"
    deleted=$((deleted + 1))
  fi
done < <(git branch --merged "$BASE_BRANCH" --format='%(refname:short)')

if [[ "$deleted" -eq 0 ]]; then
  echo "삭제할 병합 완료 로컬 브랜치가 없습니다."
else
  echo "총 ${deleted}개 로컬 브랜치를 정리했습니다."
fi
