#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from content_workflow import extract_pdf_text, get_course_site_file, load_json, natural_key, resolve_course_dirs


def main() -> int:
    parser = argparse.ArgumentParser(description="PDF 텍스트를 extracted 폴더로 추출합니다.")
    parser.add_argument("--course", help="특정 과목만 추출합니다. 예: multicultural-understanding")
    parser.add_argument("--match", help="파일명에 포함된 문자열만 추출합니다. 예: lec7 또는 2주차")
    args = parser.parse_args()

    course_dirs = resolve_course_dirs(args.course)

    for course_dir in course_dirs:
        site_data = load_json(get_course_site_file(course_dir))
        source_folder = Path(site_data["meta"]["sourceFolder"]).expanduser()
        output_dir = Path(__file__).resolve().parent.parent / "extracted" / course_dir.name
        output_dir.mkdir(parents=True, exist_ok=True)

        pdf_paths = sorted(source_folder.glob("*.pdf"), key=lambda path: natural_key(path.name))
        if args.match:
            pdf_paths = [path for path in pdf_paths if args.match.lower() in path.name.lower()]

        if not pdf_paths:
            print(f"[{course_dir.name}] 추출할 PDF가 없습니다.")
            continue

        for pdf_path in pdf_paths:
            target = output_dir / f"{pdf_path.stem}.txt"
            target.write_text(extract_pdf_text(pdf_path), encoding="utf-8")
            print(f"[{course_dir.name}] wrote {target}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
