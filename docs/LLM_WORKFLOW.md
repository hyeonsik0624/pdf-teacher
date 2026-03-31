# External LLM Workflow

다른 LLM도 지금 사이트와 같은 결과를 내게 하려면, PDF 원문을 바로 던지는 대신 이 저장소의 입력/출력 규칙을 지키게 해야 합니다.

## 핵심 원칙

- 화면 데이터는 `content/courses/<course-id>/site.json`, `content/courses/<course-id>/lectures/*.json`만 수정합니다.
- `study-data.js`는 생성 파일이므로 직접 수정하지 않습니다.
- 강의별 출력은 반드시 `content/templates/lecture-template.json` 구조를 따릅니다.
- 다른 LLM의 답변은 설명문이 아니라 **JSON만** 받아야 합니다.

## 권장 작업 순서

1. PDF 텍스트 추출

```bash
cd /Users/hyeonsik/Development/Web/pdf_teacher
.venv/bin/python scripts/extract-pdf-text.py --course multicultural-understanding --match 2주차
```

2. 새 강의용 JSON 초안 준비

- `content/templates/lecture-template.json`을 복사합니다.
- 파일명은 보통 PDF 이름 기준 slug를 씁니다.
- `source`에는 실제 PDF 파일명을 그대로 적습니다.

3. 다른 LLM에 프롬프트 전달

- `docs/LLM_PROMPT_TEMPLATE.md`의 내용을 복사합니다.
- 함께 전달할 자료:
  - 새 PDF의 추출 텍스트
  - `content/templates/lecture-template.json`
  - 필요하면 기존 강의 JSON 1개

4. 다른 LLM의 출력 저장

- 응답은 반드시 JSON만 받아서 `content/courses/<course-id>/lectures/<new>.json`에 저장합니다.

5. 검증 + 빌드

```bash
.venv/bin/python scripts/validate-content.py --course <course-id>
.venv/bin/python scripts/build-study-data.py
```

6. 미리보기

```bash
python3 -m http.server 4173
```

## 새 PDF가 아직 정리되지 않았을 때

- 빌드 스크립트는 소스 폴더의 PDF를 자동 감지합니다.
- 해당 PDF에 대응하는 강의 JSON이 없으면 사이트에 `Draft` 카드가 자동으로 표시됩니다.
- 즉, PDF 추가 여부와 해설 작성 여부를 분리해서 관리할 수 있습니다.

## 품질 기준

- 강의식 설명이어야 합니다.
- 시험 대비형이어야 합니다.
- 슬라이드 문장을 그대로 나열하지 말고, 연결해서 설명해야 합니다.
- `pitfalls`, `checklist`, `quiz`는 반드시 실전용이어야 합니다.
- `commands` 필드는 실제 명령어일 수도 있고 이론 비교 카드일 수도 있지만, 의미/답안 틀/예시/헷갈리는 포인트를 모두 포함해야 합니다.
