#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from content_workflow import (
    get_course_lectures_dir,
    get_course_site_file,
    load_json,
    resolve_course_dirs,
    validate_lecture_data,
    validate_site_data,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="콘텐츠 JSON 구조를 검증합니다.")
    parser.add_argument("--course", help="특정 과목만 검증합니다. 예: linux-programming")
    args = parser.parse_args()

    failures: list[str] = []
    course_dirs = resolve_course_dirs(args.course)

    for course_dir in course_dirs:
        site_file = get_course_site_file(course_dir)
        if not site_file.exists():
            failures.append(f"{course_dir.name}: site.json is missing")
            continue

        site_data = load_json(site_file)
        failures.extend(validate_site_data(site_data, course_id=course_dir.name))

        lecture_paths = sorted(
            [
                path
                for path in get_course_lectures_dir(course_dir).glob("*.json")
                if not path.name.startswith("_") and not path.name.startswith(".")
            ]
        )

        for lecture_path in lecture_paths:
            lecture = load_json(lecture_path)
            failures.extend(
                validate_lecture_data(
                    lecture,
                    file_name=str(Path("content/courses") / course_dir.name / "lectures" / lecture_path.name),
                )
            )

    if failures:
        print("콘텐츠 검증 실패:")
        for error in failures:
            print(f"- {error}")
        return 1

    if args.course:
        print(f"콘텐츠 검증 통과: {args.course}")
    else:
        print(f"콘텐츠 검증 통과: {len(course_dirs)}개 과목")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
