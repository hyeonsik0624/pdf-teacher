# PDF Teacher

여러 과목의 PDF/TXT 강의 자료를 바탕으로 만든 정적 웹사이트입니다. 과목별 원본 콘텐츠와 생성 결과를 분리해서, 강의 자료가 계속 늘어나도 관리하기 쉽게 구성했습니다.

## 데이터 빌드

```bash
cd /Users/hyeonsik/Development/Web/pdf_teacher
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/validate-content.py
.venv/bin/python scripts/build-study-data.py
```

`study-data.js`와 `transcript-data.js`는 생성 파일이므로 직접 수정하지 말고 `content/courses/<course-id>/site.json`, `content/courses/<course-id>/lectures/*.json`, 원본 소스 파일을 수정한 뒤 다시 빌드하면 됩니다.

로컬 PDF/TXT 폴더 경로는 빌드에만 쓰이며, 생성된 정적 파일에는 포함되지 않도록 처리되어 있습니다.

## 실행

```bash
cd /Users/hyeonsik/Development/Web/pdf_teacher
.venv/bin/python scripts/build-study-data.py
python3 -m http.server 4173
```

브라우저에서 `http://localhost:4173`를 열면 됩니다. 여러 과목이 있을 경우 `?course=<course-id>`로 직접 진입할 수도 있습니다.

- 개념 교재: `http://localhost:4173/?course=<course-id>`
- 정리된 전사문: `http://localhost:4173/transcript.html?course=<course-id>`

## GitHub Pages 배포

이 저장소에는 GitHub Pages용 워크플로우가 이미 포함되어 있습니다.

1. 로컬에서 먼저 최신 데이터로 다시 빌드합니다.
2. GitHub 저장소의 기본 브랜치를 `main`으로 맞춥니다.
3. 이 프로젝트를 push 합니다.
4. GitHub 저장소의 `Settings > Pages`에서 배포 방식이 `GitHub Actions`인지 확인합니다.
5. 배포가 끝나면 `https://<username>.github.io/<repo>/` 형태의 주소로 접속합니다.

중요:

- GitHub Actions는 현재 체크인된 정적 파일만 배포합니다.
- 따라서 새 강의를 추가했으면 push 전에 반드시 `.venv/bin/python scripts/build-study-data.py`를 다시 실행해야 합니다.
- 검색 노출을 줄이기 위해 `index.html`에 `noindex` 메타 태그를 넣고 `robots.txt`도 차단 상태로 두었습니다.
- 그래도 링크를 아는 사람은 접속할 수 있으므로, 이것은 비공개 설정이 아니라 검색 억제 설정입니다.

## 파일 구성

- `index.html`: 개념 교재 페이지 뼈대
- `transcript.html`: 정리된 전사문 페이지 뼈대
- `styles.css`: 전체 스타일
- `content/courses/<course-id>/site.json`: 과목 공통 학습 데이터
- `content/courses/<course-id>/lectures/*.json`: 과목별 강의 설명 데이터
- `content/templates/lecture-template.json`: 강의 JSON 템플릿
- `scripts/build-study-data.py`: 모든 과목 소스 폴더 스캔 + `study-data.js`, `transcript-data.js` 생성
- `scripts/build_transcript_data.py`: TXT 전사 기반 `transcript-data.js` 생성 로직
- `scripts/extract-pdf-text.py`: 과목별 PDF 텍스트 추출
- `scripts/validate-content.py`: JSON 구조 검증
- `study-data.js`: 생성된 강의 데이터
- `transcript-data.js`: 생성된 전사문 데이터
- `app.js`: 페이지 렌더링과 과목 전환, 아틀라스 필터
- `transcript-app.js`: 전사문 페이지 렌더링과 키워드 필터

## 새 PDF 추가 워크플로우

1. 해당 과목의 PDF를 그 과목 `site.json`에 적힌 `sourceFolder`에 넣습니다.
2. `.venv/bin/python scripts/extract-pdf-text.py --course <course-id> --match <키워드>`로 텍스트를 뽑습니다.
3. 다른 LLM을 쓸 경우 [docs/LLM_WORKFLOW.md](/Users/hyeonsik/Development/Web/pdf_teacher/docs/LLM_WORKFLOW.md), [docs/LLM_PROMPT_TEMPLATE.md](/Users/hyeonsik/Development/Web/pdf_teacher/docs/LLM_PROMPT_TEMPLATE.md), [lecture-template.json](/Users/hyeonsik/Development/Web/pdf_teacher/content/templates/lecture-template.json)을 기준으로 JSON을 생성합니다.
4. `content/courses/<course-id>/lectures/` 아래에 새 강의 JSON을 저장합니다.
5. `.venv/bin/python scripts/validate-content.py --course <course-id>`를 실행합니다.
6. `.venv/bin/python scripts/build-study-data.py`를 실행합니다.
7. 개념 교재와 전사문 페이지에 `Draft` 카드가 남아 있지 않은지 확인합니다.
