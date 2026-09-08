# Study Wiki: 기록을 지식으로 연결하기

이 Wiki는 **사람과 코딩 에이전트가 원본 설명을 보완하고 PR에서 검토한 뒤,
동일한 원본으로 개인·전체 지식 목록과 웹 화면을 생성**하는 방식입니다.
기본 Wiki 생성·검색에는 LLM API, 벡터 DB, 별도 서버, Python 외부 패키지가 필요하지 않습니다.
선택 기능인 AI 개념 노트는 참여자의 명시적 생성 요청에만 무료 Nemotron API를 호출합니다.

## 구현 계획과 구성

1. `enrich.py`: 코딩 에이전트가 분석한 분류를 적용합니다. 완료 상태를 바꾸지 않습니다.
2. `wiki.py`와 `study_wiki/`: 원본을 읽어 재현 가능한 Markdown Wiki와 정적 웹을 생성합니다.
3. PR: 기록별 설명·분류·리뷰 반영 내용을 검토하고 다운로드 가능한 Wiki 미리보기를 만듭니다.
4. main merge: 완료 기록으로 전체·개인·개념·문제별 연결을 갱신하고 GitHub Pages에 배포합니다.

`study.py`에는 Wiki 기능을 추가하지 않았습니다. 기존 new/note/done/prepare 흐름은 유지합니다.
생성 결과는 `.study/wiki/`에만 두고 Git에 커밋하지 않으므로 공통 목록 충돌이 없습니다.

```text
records/.../README.md + solution.* 또는 notes.md + meta.json
  → 코딩 에이전트가 근거 있는 설명·분류 보완
  → PR에서 AI / 사람 리뷰 → 채택한 내용을 원본 파일에 반영
  → main merge → wiki.py build → GitHub Pages
                             → Markdown Wiki / 원본 사본 / 출처 manifest
```

## 로컬에서 보기

저장소 루트에서 실행합니다. Windows에서는 `python3` 대신 `py -3` 또는 `python`을 사용하세요.

```bash
# 현재 checkout의 완료 기록 전체
python3 wiki.py build
python3 wiki.py serve
# http://127.0.0.1:8765

# 작성 중인 기록까지 미리보기
python3 wiki.py build --include-drafts

# 개인 Wiki: init에서 저장한 사용자 설정 이용
python3 wiki.py build --mine --include-drafts
# 또는 작성자를 명시
python3 wiki.py build --user bk123477

# 터미널에서 검색
python3 wiki.py search "해시" --user bk123477
```

생성 후 `.study/wiki/index.html`을 직접 열어도 검색·필터·코드 읽기가 동작합니다.
브라우저가 로컬 파일 실행을 제한하면 `serve`를 사용하세요. 복사가 제한된 환경에서는
코드 선택 안내가 표시됩니다. `serve`는 내 컴퓨터의 127.0.0.1에만 바인딩합니다.

다른 worktree의 작업 중 기록도 수정 없이 읽을 수 있습니다.

```bash
python3 wiki.py build --source-root ../codingtest_2026 --include-drafts
```

**로컬 build는 merge 여부를 추측하지 않습니다.** 현재 파일 중 완료 상태인 기록을 사용합니다.
공유 사이트는 main workflow가 main에 합쳐진 완료 기록만 사용합니다.
다른 참여자의 최신 기록을 로컬에 반영하려면 변경사항을 보존한 뒤 기존 Git 절차로
최신 main을 받아 다시 build하세요. GitHub Actions가 다른 사람의 컴퓨터를 자동 수정하지 않습니다.
`--mine`은 개인 기록만 출력합니다. 전체 build의 참여자 필터는 UI 필터이며 접근 제어가 아닙니다.

## 화면에서 할 수 있는 일

- 전체 / 코딩 문제 / 학습 노트 전환
- 작성자, 자료구조, 알고리즘, 언어, 미분류 필터와 최신·오래된·제목순 정렬
- 제목, 문제 번호, 본문, 코드, 분류를 포함한 검색 (여러 단어는 AND)
- `DFS`, `dict` 등 사전에 등록한 별칭으로 개념 검색
- 개념을 클릭해서 관련 문제와 노트를 함께 보기
- 문제 설명·풀이·경계 조건·리뷰와 코드 탭, 코드 복사, 원본 링크
- 같은 문제의 다른 풀이, 같은 개념을 공유하는 노트 연결
- URL fragment에 필터·선택 기록 저장: 상세 링크를 공유할 수 있음
- 기록 수와 서로 다른 문제 수 구분, draft 표시, 미분류 기록 유지

문제는 자료구조·알고리즘이 모두 비어 있으면 미분류로 표시합니다.
노트는 자료구조·알고리즘·태그가 모두 비어 있을 때 미분류입니다.

노트의 README와 가져온 `notes.md`는 한 화면에서 읽을 수 있습니다.
문제 원문의 전문은 수집하지 않습니다. 기록에 작성한 문제 요약을 표시하고 원문 링크를 제공합니다.
Markdown의 제목·문단·목록·표·인용·코드 블록·링크·굵은 글씨를 표시합니다.
임의 HTML/스크립트는 실행하지 않으며, 이미지·수식·Mermaid의 시각 렌더링은 제공하지 않습니다.
원본 파일은 그대로 보존하고 연결합니다.

## 코딩 에이전트에게 보완 요청하기

```text
AGENTS.md의 ‘기존 기록 보완’ 절차를 따라 오늘 내 기록을 보완해줘.
solution.py와 내가 적은 README를 읽고, 근거 있는 풀이 설명·복잡도·분류를 채워줘.
코드와 기존 회고는 보존하고 채점 결과나 풀이 시간은 추측하지 마.
검증 후 Wiki 미리보기도 생성해줘. 완료 여부는 이미 전달한 채점 확인을 기준으로 처리해줘.
```

`enrich.py`는 스스로 코드 의미를 분석하는 AI가 아니라, 에이전트가 결정한 값을 안전하게 적용하는 명령입니다.
README의 서술 부분은 에이전트가 직접 편집합니다.

```bash
python3 enrich.py records/YYYY/MM/DD/사용자명/programmers-문제번호 \
  --data-structures "배열, 해시" --algorithms "문자열 처리" --tags "문자열"
python3 enrich.py records/YYYY/MM/DD/사용자명/note-01 --tags "Git, 브랜치"
```

기본은 **빈 필드만 보완**합니다. 문제의 `## 풀이 정보`도 기존 study 도구의 형식으로 맞춥니다.
기존 값이 있으면 보존 메시지를 출력합니다. 잘못된 분류를 확인해 교체할 때만 `--replace`를 붙이세요.
`--replace`는 명시한 필드만 교체하며, 빈 인수 `--tags "" --replace`는 해당 필드를 비웁니다.
`--difficulty`는 원문에서 확인한 경우에만 사용합니다.
사용자·날짜·URL·완료 상태·풀이 시간·풀이 방식은 이 명령으로 바꾸지 않습니다.

분류 별칭은 `study_wiki/taxonomy.json`에 관리합니다. 기존 기록 파일은 build가 수정하지 않습니다.
사전에 없는 개념도 사용할 수 있습니다. 실제 코드의 사용 방식에 근거해서 분류하고,
모든 반복문을 완전 탐색으로, 모든 리스트를 스택으로 분류하지 마세요.
알고리즘 노트는 설명하는 개념을 분류하고, 문제 풀이 경험과 혼동하지 않습니다.

## 설명·리뷰·출처 규칙

- 풀이와 학습 메모가 사실의 원본입니다. 생성된 HTML·Markdown은 직접 편집하지 않습니다.
- `## Wiki 요약`은 선택 항목입니다. 에이전트가 추가했다면 ‘코딩 에이전트 보완’임을 본문에 표시합니다.
  없으면 문제의 `## 풀이`, 노트의 `## 학습 주제 / 목표`에서 짧은 발췌를 사용합니다.
- `## 리뷰로 확인한 내용`에 채택한 지적, 확인 방법 또는 수정 내용, PR/댓글 링크를 남깁니다.
  AI 지적·미해결 질문을 확정된 학습 사실처럼 쓰지 않습니다.
- PR 댓글은 자동 수집하지 않습니다. merge 후 리뷰도 원본 수정 PR을 통해 반영합니다.
- 추가적인 개념 해설이나 풀이 비교는 `study.py note`로 학습 정리 초안을 만들어 검토합니다.
  여러 사람의 경험을 한 사람의 경험처럼 합치지 않고 관련 기록 링크를 남깁니다.
- 원본을 수정·삭제한 뒤 build하면 전체 연결을 다시 계산합니다. 이전 페이지도 제거됩니다.
  `manifest.json`에 원본 해시와 ref를 기록하여 어느 입력에서 생성됐는지 추적합니다.

## GitHub Pages 설정 (운영자가 처음 한 번)

1. 이 도구 변경을 별도 관리 PR로 main에 반영합니다.
2. 저장소 **Settings → Pages → Build and deployment → Source → GitHub Actions**를 선택합니다.
3. **Settings → Environments → github-pages**에서 main 배포가 허용되는지 확인합니다.
4. **Actions → Study Wiki → Run workflow → main**으로 첫 배포를 실행합니다.
5. 실행 결과의 `github-pages` 환경 링크에서 사이트를 엽니다.

기본 주소는 `https://<소유자>.github.io/<저장소>/`입니다. 실제 배포 결과의 URL이 기준입니다.
프로젝트 경로 아래에서도 동작하도록 모든 웹 자산 경로는 상대 경로를 사용합니다.
이 저장소의 예상 기본 주소는 `https://bk123477.github.io/codingtest_2026/`이며,
설정과 첫 배포가 끝나기 전에는 게시된 주소가 아닙니다.

PR의 `Study Wiki` 실행은 `wiki-preview-PR번호` artifact와 Step Summary를 만듭니다.
다운로드 후 압축을 풀고 `index.html`을 열면 됩니다. PR별 공개 URL은 만들지 않습니다.
미리보기는 읽기 권한으로 실행되고 Secret·Pages 배포 권한이 없습니다.
외부 fork PR은 GitHub 정책상 유지관리자의 Actions 실행 승인이 필요할 수 있습니다.
배포 job은 main의 push 또는 main 수동 실행에서만 실행됩니다.

공개 저장소의 표준 Actions runner 및 공개 저장소 Pages의 무료 범위로 운영합니다.
기본 Wiki에는 LLM 호출·상시 서버가 없고 PR 미리보기 artifact는 3일 보관합니다.
선택적인 AI 노트 생성은 무료 Nemotron만 사용하고 생성 초안 artifact는 7일 보관합니다. 유료 API fallback은 없습니다.
저장소가 비공개라면 Pages 제공 조건과 Actions 할당량을 별도로 확인해야 합니다.
전체 데이터가 정적 파일에 들어가므로 공개하면 코드·학습 메모 모두 공개됩니다.

공식 안내: [GitHub Pages workflow](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages),
[Actions 요금](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

## 검증과 제한

```bash
python3 -m unittest discover -s tests -v
node --test tests/wiki_search.test.cjs
node --check study_wiki/assets/app.js
python3 study.py check
python3 wiki.py build
git diff --check
```

Node는 UI 로직을 테스트할 때만 필요합니다. 로컬 생성·검색·서빙에는 Python 3.10 이상만 필요합니다.
현재 검색은 브라우저 메모리에서 수행하며 본문·코드도 정적 데이터에 포함됩니다.
아주 큰 저장소에서는 색인과 상세 본문을 분리하는 후속 최적화가 필요합니다.
대화형 질의는 제공하지 않습니다. 아래 생성 기능은 원본을 분석한 개념 노트 초안을 PR로 제출합니다.

## 코드 한글과 들여쓰기

README의 `solution.py` 링크는 원시 코드 파일 대신 Wiki의 코드 탭으로 이동합니다.
원본 사본에는 UTF-8을 명시한 `.html` 뷰어도 생성하며, 로컬 서버는 원시 코드·Markdown에도
`charset=utf-8`을 명시합니다. 소스 코드를 Markdown으로 해석하지 않고 그대로 이스케이프하므로
한글 주석과 들여쓰기를 보존합니다. 기존 원본 파일 자체는 수정하지 않습니다.

## 개념 연결과 노트 후보

페이지의 **개념 연결** 메뉴에서 개념을 선택하면, 같은 기록에 함께 등장한 다른 개념과
공통 기록 수를 볼 수 있습니다. 연결은 자료구조·알고리즘·개념 태그를 근거로 하며
선수 지식이나 인과관계를 의미하지 않습니다. 언어·난이도 태그는 개념 그래프에서 제외합니다.
AI 노트는 개념 페이지에 연결되지만, AI 설명이 새 개념 간 연결의 근거가 되지는 않습니다.

완료 기록 2개 이상이 있는 개념은 노트 후보로 표시합니다. 분류가 비어 있어도
**개념 자동 탐색** 요청을 통해 실제 README와 코드의 공통 주제를 분석할 수 있습니다.
아직 분류되지 않은 문제를 이 과정에서 자동 수정하지는 않습니다.

## AI 개념 노트 생성 설정과 흐름

1. main에 `wiki-note.yml`과 생성기를 반영합니다.
2. Repository Secret `OPENROUTER_API_KEY`를 설정합니다. 기존 OpenRouter 리뷰 키를 재사용할 수 있습니다.
3. 필요하면 Repository Variable `WIKI_MODEL`을 설정합니다.
   기본값은 `nvidia/nemotron-3.5-lightning:free`입니다.
   무료 NVIDIA Nemotron 모델 ID만 허용하며 유료 모델로 자동 전환하지 않습니다.
   기존 리뷰 모델 설정은 변경하지 않습니다.
4. Settings → Actions → General → Workflow permissions에서
   **Allow GitHub Actions to create and approve pull requests**를 활성화해야 PR 생성이 가능합니다.
   이 workflow는 PR을 생성할 뿐 승인·자동 merge하지 않습니다.
5. Wiki의 **GitHub에서 생성 요청** 버튼을 누르고 GitHub Issue 작성 화면에서 요청을 제출합니다.
   버튼 클릭만으로 제출되는 것은 아닙니다. Pages에 인증 토큰·모델 키를 저장하지 않습니다.
6. 저장소 쓰기 권한이 있는 참여자가 제출한 요청에 대해 Actions가 실행됩니다.
   **Actions → Generate Wiki concept note**에서 성공·실패와 PR을 확인합니다.
7. 생성 PR에서 인용·설명을 검토하고, 검토를 마쳤다면 `review_status`를 `reviewed`로 바꿉니다.
   merge 후 공개 Wiki의 **AI 개념 노트**에 나타납니다. merge만으로 검토 표시를 변경하지 않습니다.

또는 GitHub Actions 화면의 **Run workflow**로 `topic`과 선택적 `user`를 입력할 수 있습니다.
`topic=auto`는 전체 완료 기록에서 공통 개념을 탐색합니다. 명시한 개념은 해당 분류·본문과 맞는 기록으로 좁힙니다.
기본 Wiki와 AI 노트 생성 workflow 모두 main에서 실행하며 PR의 코드나 지시를 Secret 권한으로 실행하지 않습니다.

```bash
# 로컬에서 API 호출 없이 분석 대상만 확인
python3 -m study_wiki.generate --topic auto --dry-run
python3 -m study_wiki.generate --topic "해시" --user bk123477 --dry-run

# API 키가 환경변수에 있는 경우 실제 초안 생성 (무료 한도 사용)
python3 -m study_wiki.generate --topic "해시"
```

한 번의 요청은 **선택한 작성자·주제에 해당하는 완료 기록 전체**를 탐색합니다.
전체 기록 수 상한은 없습니다. 긴 원본은 8,000자 단위로 끝까지 분할하고, 개별 분석을
호출 입력 60,000자 이내로 묶어 여러 단계로 통합한 뒤 개념 노트 하나를 만듭니다.
분할·통합 과정에서도 원본 출처 ID를 유지합니다. 전체 탐색이 모든 기록을 최종 노트에서
인용한다는 뜻은 아니며, 최종 노트에는 해당 개념에 사용한 근거만 인용합니다.

기록 내용·모델·프롬프트·요청 주제를 기준으로 `.study/wiki-analysis/`에 중간 결과를 저장합니다.
동일한 기록은 재사용하고 추가·수정된 기록은 다시 분석하며, 통합 결과도 입력이 같으면 재사용합니다.
한 실행은 기본 최대 20회 호출 또는 240초 뒤 새 호출을 중단합니다. 이미 진행 중인 호출은
끝날 때까지 기다립니다. 이는 한 실행의 한도이며 전체 기록 수 제한이 아닙니다.
로컬에서는 `--max-calls`로 호출 한도를 조절할 수 있습니다.
무료 API 한도나 실행 한도로 중단되면 **같은 명령 또는 GitHub의 Re-run jobs**로 이어갑니다.
GitHub Actions는 실패한 실행에서도 분석 캐시를 저장하고, Step Summary에 처리 조각 수와
재사용 수를 표시합니다. 캐시가 만료·삭제되면 원본에서 다시 분석합니다. 유료 전환은 없습니다.

`none`, `null`, `미분류`, `미입력`, `없음` 등은 개념 목록에서 제외합니다.
기존 `topic=none` 주소는 전체 개념 화면으로 전환하고, 생성 요청의 `none`은 자동 탐색으로 처리합니다.
본문의 인용과 원본 ID를 검사하며 존재하지 않는 출처나 잘린 응답은 저장하지 않습니다.
한도 초과·모델 장애는 실패로 표시하고 유료 전환이나 무한 재시도를 하지 않습니다.
PR 생성 권한 문제로 실패하더라도 생성에 성공한 초안은 실행의 artifact에서 내려받을 수 있습니다.

자동 노트는 `wiki_notes/generated/<원본·요청 해시>/README.md`와 `meta.json`으로 저장합니다.
**AI 자동 생성**, 모델, 생성 시각, 원본 해시, 검토 상태를 표시하고 일일 목표에 합산하지 않습니다.
작성자 필터에는 해당 참여자의 원본을 인용한 AI 노트도 포함되며, 여러 사람을 인용한 노트의 내용은
작성자 필터로 잘라내지 않습니다. 필터는 접근 제어가 아닙니다.
AI 노트를 다시 모델 입력으로 사용하지 않습니다. 원본이 바뀌거나 사라지면 재검토 표시가 나타납니다.
재생성 노트가 이전 노트를 대체하는 경우 기존 노트 삭제도 검토 PR에 포함하여 중복을 정리하세요.

참고: [무료 Nemotron 모델](https://openrouter.ai/nvidia/nemotron-3.5-lightning:free),
[GitHub 수동 workflow 실행](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

## 기출 출처 기록

기출 여부나 회사를 제목에서 추측하지 않고 확인된 값만 적습니다.
`meta.json`의 선택 항목 `exam`은 `name`, `organization`, `year`, `round`, `url`을 사용하며
값은 문자열입니다. `name`은 필수이고 나머지는 아는 것만 지정합니다.

```bash
python3 enrich.py records/YYYY/MM/DD/사용자명/programmers-문제번호 \
  --exam-name "채용 코딩테스트" --exam-organization "확인된 기업명" \
  --exam-year "2024" --exam-round "1차" --exam-url "https://example.com/verified-source"
```

위 값은 형식 예시입니다. 실제 기출 근거로 바꿔 입력하세요.
기존 기출 정보를 교체할 때는 알고 있는 전체 `exam` 값을 `--replace`와 함께 지정합니다.
페이지의 **기출 모음**과 **기출·출제 연도 필터**에서 모아 볼 수 있습니다.
페이지 내 도움말에는 검색, 개념 연결, AI 생성, 기출과 갱신 방법을 안내합니다.
