#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from content_workflow import (
    extract_source_text,
    get_course_site_file,
    list_source_files,
    load_json,
    resolve_course_dirs,
    slugify,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="과목 소스 텍스트를 extracted 폴더로 추출하거나 복사합니다.")
    parser.add_argument("--course", help="특정 과목만 추출합니다. 예: multicultural-understanding")
    parser.add_argument("--match", help="파일명에 포함된 문자열만 추출합니다. 예: lec7 또는 2주차")
    args = parser.parse_args()

    course_dirs = resolve_course_dirs(args.course)

    for course_dir in course_dirs:
        site_data = load_json(get_course_site_file(course_dir))
        source_folder = Path(site_data["meta"]["sourceFolder"]).expanduser()
        output_dir = Path(__file__).resolve().parent.parent / "extracted" / course_dir.name
        output_dir.mkdir(parents=True, exist_ok=True)

        source_paths = list_source_files(site_data["meta"])
        if args.match:
            source_paths = [path for path in source_paths if args.match.lower() in path.name.lower()]

        if not source_paths:
            print(f"[{course_dir.name}] 추출할 소스 파일이 없습니다.")
            continue

        for source_path in source_paths:
            relative_stem = source_path.relative_to(source_folder).with_suffix("").as_posix()
            target = output_dir / f"{slugify(relative_stem)}.txt"
            target.write_text(extract_source_text(source_path), encoding="utf-8")
            print(f"[{course_dir.name}] wrote {target}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
