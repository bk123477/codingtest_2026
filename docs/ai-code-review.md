# OpenRouter AI 코드리뷰

이 저장소는 PR이 열리거나 새 commit이 올라오거나 다시 열릴 때
OpenRouter의 `minimax/minimax-m3:free` 모델로 변경사항을 리뷰하고,
PR의 하나의 댓글을 생성하거나 갱신합니다.

## 동작 흐름

```text
PR opened / synchronize / reopened
  → trusted base branch의 workflow 실행
  → PR head를 Git object로 fetch
  → 변경된 텍스트 파일과 코딩 문제 README/solution.py 확인
  → OpenRouter Chat Completions API 호출
  → 기존 AI 리뷰 댓글 갱신 또는 새 댓글 작성
```

workflow는 보안상 `pull_request_target`을 사용합니다. 이 이벤트에서는
PR 브랜치의 workflow나 코드를 checkout하거나 실행하지 않고, base 브랜치의
스크립트가 PR diff를 텍스트로만 읽습니다. 따라서 fork PR도 리뷰할 수 있고,
외부 contributor의 코드가 Secret 권한으로 실행되지 않습니다.

## GitHub에서 한 번 설정할 것

1. 새 OpenRouter API 키를 발급합니다. 이전에 채팅에 입력한 키는 노출된 것으로 보고 폐기하세요.
2. GitHub 저장소의 **Settings → Secrets and variables → Actions**로 이동합니다.
3. Repository secret을 만들고 이름을 정확히 `OPENROUTER_API_KEY`로 지정합니다.
4. 값에는 새 API 키만 입력합니다.

`GITHUB_TOKEN`은 GitHub Actions가 자동으로 제공하므로 직접 등록할 필요가 없습니다.

모델을 바꾸려면 같은 화면의 **Variables**에 `OPENROUTER_MODEL`을 만들고
모델 ID를 입력하세요. 변수가 없으면 다음 기본값을 사용합니다.

```text
minimax/minimax-m3:free
```

## 로컬 `.env`

로컬 실행이나 설정 확인이 필요하면 다음처럼 사용합니다.

```bash
cp .env.example .env
```

`.env`에는 새 키를 넣을 수 있지만, `.gitignore`에 포함되어 Git에 올라가지
않습니다. `.env.example`에는 실제 키를 넣지 않습니다.

이 저장소의 자동 workflow는 `.env`를 읽지 않고 GitHub Secret만 읽습니다.

## 리뷰 범위

리뷰어는 우선 실제 버그, 반례, 경계 조건, 알고리즘 정확성, 시간·공간 복잡도,
보안·성능 문제를 찾습니다. 단순 formatting이나 취향 차이는 지적하지 않습니다.

코딩 문제 기록은 다음 구조를 기준으로 README와 풀이를 함께 봅니다.

```text
records/YYYY/MM/DD/<사용자>/programmers-<문제번호>/
├── README.md
├── solution.py
└── meta.json
```

`meta.json`, lock file, binary file, generated directory는 기본적으로 모델 입력에서
제외합니다. 큰 diff는 파일별·전체 크기 제한에 따라 잘릴 수 있습니다.

## 댓글 처리

댓글 본문에 내부 marker를 넣고, 다음 실행 때 같은 marker를 가진 댓글을 찾아
갱신합니다. 따라서 새 commit마다 AI 댓글이 무한히 쌓이지 않습니다.

OpenRouter 오류, rate limit, 빈 응답, GitHub 댓글 API 오류는 AI 리뷰 workflow를
성공 상태로 마무리하면서 Step Summary에 원인만 남깁니다. 기존 학습 검증 workflow의
성공 여부를 AI 서비스 장애가 막지 않습니다.

## 확인 방법

로컬에서는 외부 API를 호출하지 않고 다음 검사를 실행할 수 있습니다.

```bash
python3 -m py_compile .github/scripts/ai_code_review.py
python3 -m unittest discover -s tests -v
python3 study.py check
git diff --check
```

GitHub에서 확인하려면 작은 문제 기록 PR을 만들고 Actions의 **AI code review** 실행
결과와 PR 댓글을 확인하세요. 같은 PR에 새 commit을 push했을 때 기존 AI 댓글이
갱신되는지도 확인합니다.
