#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from content_workflow import (
    ROOT,
    describe_source_file,
    extract_source_text,
    get_course_lectures_dir,
    get_course_site_file,
    list_source_files,
    load_json,
    natural_key,
    normalize_source_name,
    resolve_course_dirs,
    validate_lecture_data,
    validate_site_data,
)


TRANSCRIPT_OUTPUT_FILE = ROOT / "transcript-data.js"
BLOCK_TARGET_CHARS = 780
BLOCK_MAX_CHARS = 980
BLOCK_MAX_SENTENCES = 7


def normalize_transcript_text(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"=== PAGE \d+ ===\s*", " ", cleaned)
    cleaned = cleaned.replace("\u00a0", " ").replace("\u200b", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"((?:[가-힣A-Za-z0-9]+(?:\s+|,\s*)){1,6})\1{3,}", r"\1", cleaned)
    return cleaned


def split_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    return parts or ([text] if text else [])


def wrap_long_text(text: str, limit: int = BLOCK_TARGET_CHARS) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in text.split():
        extra = len(word) + (1 if current else 0)
        if current and current_len + extra > limit:
            chunks.append(" ".join(current).strip())
            current = [word]
            current_len = len(word)
            continue

        current.append(word)
        current_len += extra

    if current:
        chunks.append(" ".join(current).strip())

    return chunks


def make_transcript_blocks(text: str) -> list[dict]:
    sentences = split_sentences(normalize_transcript_text(text))
    blocks: list[dict] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        fragments = wrap_long_text(sentence, limit=BLOCK_TARGET_CHARS)
        for fragment in fragments:
            extra = len(fragment) + (1 if current else 0)
            should_flush = current and (
                current_len + extra > BLOCK_MAX_CHARS or len(current) >= BLOCK_MAX_SENTENCES
            )

            if should_flush:
                blocks.append(
                    {
                        "index": len(blocks) + 1,
                        "text": " ".join(current).strip(),
                    }
                )
                current = [fragment]
                current_len = len(fragment)
                continue

            current.append(fragment)
            current_len += extra

    if current:
        blocks.append(
            {
                "index": len(blocks) + 1,
                "text": " ".join(current).strip(),
            }
        )

    return blocks


def build_course_transcript_payload(course_dir: Path, generated_at: str) -> dict | None:
    site_file = get_course_site_file(course_dir)
    if not site_file.exists():
        raise SystemExit(f"공통 데이터 파일이 없습니다: {site_file}")

    site_data = load_json(site_file)
    site_errors = validate_site_data(site_data, course_id=course_dir.name)
    if site_errors:
        raise SystemExit("site.json 검증 실패:\n- " + "\n- ".join(site_errors))

    source_folder = Path(site_data["meta"]["sourceFolder"]).expanduser()
    if not source_folder.exists():
        raise SystemExit(f"소스 폴더가 없습니다: {source_folder}")

    source_entries = [describe_source_file(path, source_folder) for path in list_source_files(site_data["meta"])]
    transcript_source_entries = [entry for entry in source_entries if entry.get("type") == "txt"]
    if not transcript_source_entries:
        return None

    transcript_source_paths = {
        normalize_source_name(entry["file"]): source_folder / Path(entry["file"])
        for entry in transcript_source_entries
    }
    source_entry_by_file = {normalize_source_name(entry["file"]): entry for entry in transcript_source_entries}

    lectures_dir = get_course_lectures_dir(course_dir)
    lecture_paths = sorted(
        [
            path
            for path in lectures_dir.glob("*.json")
            if not path.name.startswith("_") and not path.name.startswith(".")
        ],
        key=lambda path: natural_key(path.name),
    )

    lectures: list[dict] = []
    total_characters = 0
    total_blocks = 0

    for lecture_path in lecture_paths:
        lecture = load_json(lecture_path)
        lecture["source"] = normalize_source_name(lecture.get("source", ""))
        errors = validate_lecture_data(
            lecture,
            file_name=str(Path("content/courses") / course_dir.name / "lectures" / lecture_path.name),
        )
        if errors:
            raise SystemExit("강의 JSON 검증 실패:\n- " + "\n- ".join(errors))

        status = lecture.get("status", "ready")
        if status != "ready":
            continue

        source_file = lecture.get("source", "")
        if source_file not in transcript_source_paths:
            continue

        transcript_text = normalize_transcript_text(extract_source_text(transcript_source_paths[source_file]))
        if not transcript_text:
            continue

        transcript_blocks = make_transcript_blocks(transcript_text)
        total_characters += len(transcript_text)
        total_blocks += len(transcript_blocks)

        source_entry = source_entry_by_file[source_file]
        basics = lecture.get("basics", [])
        concepts = lecture.get("concepts", [])
        topic_titles = [item["title"] for item in basics[:3] if isinstance(item, dict) and item.get("title")]
        topic_titles.extend(
            item["title"]
            for item in concepts[:4]
            if isinstance(item, dict) and item.get("title") and item["title"] not in topic_titles
        )

        lectures.append(
            {
                "id": lecture["id"],
                "order": lecture.get("order", len(lectures) + 1),
                "badge": lecture["badge"],
                "title": lecture["title"],
                "theme": lecture["theme"],
                "summary": lecture["summary"],
                "source": source_file,
                "sourceDisplay": lecture.get("sourceDisplay") or source_entry["name"],
                "sourceMetricLabel": source_entry["metricLabel"],
                "narrative": lecture.get("narrative", []),
                "basics": basics,
                "topicTitles": topic_titles,
                "transcriptTextLength": len(transcript_text),
                "transcriptBlocks": transcript_blocks,
            }
        )

    if not lectures:
        return None

    lectures.sort(key=lambda lecture: (lecture.get("order", 10_000), lecture.get("title", "").lower()))

    meta = {key: value for key, value in site_data["meta"].items() if key != "sourceFolder"}
    return {
        "id": course_dir.name,
        "meta": {
            **meta,
            "courseId": course_dir.name,
            "generatedAt": generated_at,
            "transcriptLectureCount": len(lectures),
            "transcriptBlockCount": total_blocks,
            "transcriptCharacterCount": total_characters,
        },
        "lectures": lectures,
    }


def build_transcript_courses(course_dirs: list[Path], generated_at: str) -> list[dict]:
    courses: list[dict] = []
    for course_dir in course_dirs:
        payload = build_course_transcript_payload(course_dir, generated_at)
        if payload:
            courses.append(payload)
    return courses


def write_transcript_output(course_dirs: list[Path], generated_at: str) -> list[dict]:
    courses = build_transcript_courses(course_dirs, generated_at)
    payload = {
        "generatedAt": generated_at,
        "courseOrder": [course["id"] for course in courses],
        "courses": courses,
    }
    output = (
        "/* This file is generated by scripts/build_transcript_data.py. */\n"
        "/* Do not edit this file directly; edit content/courses/* and source transcripts instead. */\n"
        f"window.transcriptLibrary = {json.dumps(payload, ensure_ascii=False, indent=2)};\n"
    )
    TRANSCRIPT_OUTPUT_FILE.write_text(output, encoding="utf-8")
    return courses


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat()
    course_dirs = resolve_course_dirs()
    courses = write_transcript_output(course_dirs, generated_at)

    print(f"Built {TRANSCRIPT_OUTPUT_FILE.name}")
    print(f"- Transcript courses: {len(courses)}")
    for course in courses:
        print(
            f"- {course['id']}: lectures {course['meta']['transcriptLectureCount']}, "
            f"blocks {course['meta']['transcriptBlockCount']}, "
            f"chars {course['meta']['transcriptCharacterCount']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
