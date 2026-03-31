# Content Structure

강의 데이터는 과목별 원본 데이터와 생성 결과를 분리해서 관리합니다.

## 파일 역할

- `courses/<course-id>/site.json`: 과목 공통 소개, 암기 포인트, 아틀라스, 실전 루틴
- `courses/<course-id>/lectures/*.json`: 과목별 강의 설명 데이터
- `templates/lecture-template.json`: 새 강의 JSON 템플릿
- `../study-data.js`: 위 데이터를 바탕으로 빌드되는 결과물. 직접 수정하지 않음

## 새 PDF가 추가될 때

1. 대상 과목의 PDF를 `site.json`의 `sourceFolder`에 넣습니다.
2. `.venv/bin/python scripts/extract-pdf-text.py --course <course-id> --match <키워드>`로 텍스트를 뽑습니다.
3. 아직 강의 JSON이 없으면 사이트에 `Draft` 카드가 자동으로 생깁니다.
4. `templates/lecture-template.json`이나 기존 강의 JSON을 복사해 `courses/<course-id>/lectures/` 아래 새 파일을 만듭니다.
5. `.venv/bin/python scripts/validate-content.py --course <course-id>`를 실행합니다.
6. `.venv/bin/python scripts/build-study-data.py`를 실행합니다.

## 권장 규칙

- `source` 값은 실제 PDF 파일명과 정확히 같아야 합니다.
- `pages`는 JSON에 직접 쓰지 않습니다. 빌드 스크립트가 자동으로 채웁니다.
- `order`로 화면 표시 순서를 조정합니다.
- 초안 상태를 유지하고 싶으면 `status`를 `draft`로 둘 수 있지만, 보통은 `ready`로 둡니다.
- 보조 읽기자료처럼 해설이 아직 준비되지 않은 PDF는 일부러 파일을 만들지 않아도 됩니다. 빌드 시 `Draft` 카드로 자동 표시됩니다.
