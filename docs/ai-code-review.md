# OpenRouter AI 코드리뷰

이 저장소는 PR이 열리거나 새 commit이 올라오거나 다시 열릴 때
OpenRouter의 `minimax/minimax-m3:free` 모델로 변경사항을 리뷰하고,
기록 폴더별로 나눈 하나의 PR 댓글을 생성하거나 갱신합니다.

## 동작 흐름

```text
PR opened / synchronize / reopened
  → trusted base branch의 workflow 실행
  → PR head를 Git object로 fetch
  → 변경된 텍스트 파일과 문제·학습 정리 context 확인
  → 문제·노트 기록 폴더별로 리뷰 결과 구성
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

리뷰어는 기록의 `meta.json`에 있는 `type`을 기준으로 문제 풀이와 학습 정리를
다르게 평가합니다. 단순 formatting이나 취향 차이는 지적하지 않습니다.
리뷰 본문은 한국어로 작성하며, 각 섹션은 최대 3개의 짧은 bullet과 1~2문장의
요약만 사용합니다. 코드 식별자와 파일 경로는 원문을 유지합니다.

문제 풀이 기록의 기준은 다음과 같습니다.

- `Critical`: 오답 가능성이 높은 논리, 런타임 오류, 문제 조건 위반, 치명적인 반례, 제한 시간 안에 불가능한 알고리즘
- `Important`: 경계 조건, 입출력 실수, 자료구조·알고리즘 선택, 시간·공간 복잡도, Python 특유의 오류
- `Suggestions`: 더 단순하거나 견고한 풀이, 복잡도 설명, 유용한 추가 테스트

학습 정리 기록의 기준은 다음과 같습니다.

- `Critical`: 사실 오류, 위험한 잘못된 지식, 설명과 예시의 모순, 결론을 뒷받침하지 못하는 추론
- `Important`: 빠진 전제·트레이드오프, 과도한 일반화, 알고리즘·자료구조 설명의 불명확함, 부적절한 예시
- `Suggestions`: 더 명확한 구성, 작은 예시, 유사 개념 비교, 직접 확인할 수 있는 실습 방법

실제 채점 결과나 실행 여부를 입력으로 받지 않았다면 모델이 임의로 만들어내지
않습니다. 따라서 문제 풀이의 평가는 제공된 문제 조건·코드·README를 근거로 한
정적 검토입니다.

기록 폴더는 이름의 접두사를 기준으로 판단하지 않고 다음 구조에서 동적으로 찾습니다.
기록 유형과 문제 플랫폼은 `meta.json`에서 확인합니다.

```text
records/YYYY/MM/DD/<사용자>/<기록폴더>/
├── README.md
├── solution.* 또는 notes.md
└── meta.json
```

`meta.json`, lock file, binary file, generated directory는 기본적으로 모델 입력에서
제외합니다. 큰 diff는 파일별·전체 크기 제한에 따라 잘릴 수 있습니다.

같은 PR에 여러 문제나 학습 정리가 있으면 각 기록 폴더를 별도 그룹으로 리뷰합니다.
문제 기록은 `meta.json`의 `solution` 파일과 `README.md`, 학습 정리는 `README.md`와
`source_file`이 가리키는 정리 파일을 함께 참고합니다. 따라서 Programmers,
CodeTree, 다른 플랫폼 이름이나 사용자 정의 기록 폴더도 같은 방식으로 처리됩니다.
댓글은 다음처럼 기록별 섹션으로 구성됩니다.

```markdown
## 🤖 AI Code Review

### 📁 records/2026/09/08/alice/programmers-12922
#### ⚠️ Important
- ...

### 📁 records/2026/09/08/alice/note-git
#### 💡 Suggestions
- ...

### ✅ Summary
...
```

각 기록의 `Critical`, `Important`, `Suggestions` 중 내용이 있는 섹션만 표시하며,
기록별 최대 3개의 짧은 bullet을 사용합니다. 이는 GitHub의 파일 줄에 직접 다는
인라인 리뷰가 아니라, 하나의 PR 댓글 안에서 기록별로 구분하는 방식입니다.

## 댓글 처리

댓글 본문에 내부 marker를 넣고, 다음 실행 때 같은 marker를 가진 댓글을 찾아
갱신합니다. 따라서 새 commit마다 기록별 AI 댓글이 무한히 쌓이지 않습니다.

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
