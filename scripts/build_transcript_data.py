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
BLOCK_TARGET_CHARS = 700
BLOCK_MIN_CHARS = 340
BLOCK_MAX_CHARS = 920
BLOCK_MAX_PARAGRAPHS = 4
PARAGRAPH_TARGET_CHARS = 220
PARAGRAPH_MAX_CHARS = 340
PARAGRAPH_MAX_UNITS = 3
TITLE_MAX_CHARS = 30
MIN_TOPIC_SCORE = 2
SECTION_TRANSITION_PATTERN = re.compile(
    r"^(?:"
    r"이번 시간에는|오늘은|먼저|첫 ?번째|두 ?번째|세 ?번째|"
    r"그러면|그럼|이제|다음(?:은|으로)?|이어서|이어(?:서)?|"
    r"마지막으로|정리하면|한편|여기서|다시|끝으로|간단하게|"
    r"또 하나(?:의)?|이와 관련해"
    r")"
)
TOPIC_STOPWORDS = {
    "강의",
    "주차",
    "차시",
    "내용",
    "부분",
    "정리",
    "설명",
    "이해",
    "학습",
    "목표",
    "관점",
    "방식",
    "과정",
    "구조",
    "형태",
    "상황",
    "결과",
    "문제",
    "사실",
    "지점",
    "의미",
    "핵심",
    "처음",
    "마지막",
    "이번",
    "시간",
    "여기",
    "이것",
    "그것",
    "그때",
    "현재",
    "당시",
    "통해",
    "관련",
    "대해",
    "이후",
    "먼저",
    "다음",
    "하나",
    "가지",
}
TOKEN_SUFFIXES = [
    "으로부터",
    "이었습니다",
    "였습니다",
    "이지만",
    "하지만",
    "하면서",
    "에서는",
    "으로는",
    "에게서",
    "까지는",
    "부터는",
    "이라고",
    "이라는",
    "입니다",
    "합니다",
    "하도록",
    "되도록",
    "에서의",
    "에서",
    "에게",
    "으로",
    "로서",
    "로는",
    "로의",
    "로",
    "까지",
    "부터",
    "처럼",
    "같은",
    "같이",
    "마다",
    "조차",
    "마저",
    "인데",
    "이면",
    "이란",
    "으론",
    "이다",
    "다는",
    "보다",
    "하고",
    "하며",
    "하게",
    "이고",
    "이며",
    "적인",
    "에는",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "의",
    "에",
    "와",
    "과",
    "도",
    "만",
]


def normalize_inline_text(text: str) -> str:
    cleaned = text.replace("\u00a0", " ").replace("\u200b", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
    cleaned = re.sub(r"((?:[가-힣A-Za-z0-9]+(?:\s+|,\s*)){1,6})\1{2,}", r"\1", cleaned)
    return cleaned


def normalize_keyword_token(token: str) -> str:
    normalized = re.sub(r"[^가-힣A-Za-z0-9]", "", token).lower()
    if not normalized:
        return ""

    changed = True
    while changed:
        changed = False
        for suffix in TOKEN_SUFFIXES:
            if normalized.endswith(suffix) and len(normalized) - len(suffix) >= 2:
                normalized = normalized[: -len(suffix)]
                changed = True
                break

    if normalized in TOPIC_STOPWORDS:
        return ""

    if len(normalized) < 2 and not normalized.isdigit():
        return ""

    return normalized


def extract_keyword_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for raw_token in re.findall(r"[가-힣A-Za-z0-9]+", text):
        token = normalize_keyword_token(raw_token)
        if not token or token in seen:
            continue
        tokens.append(token)
        seen.add(token)
    return tokens


def normalize_transcript_text(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"=== PAGE \d+ ===\s*", "\n", cleaned)
    lines = [normalize_inline_text(line) for line in cleaned.split("\n")]
    return "\n".join(line for line in lines if line)


def split_sentences(text: str) -> list[str]:
    parts = [normalize_inline_text(part) for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    return parts or ([normalize_inline_text(text)] if text else [])


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


def split_transcript_units(text: str) -> list[str]:
    units: list[str] = []
    for raw_line in normalize_transcript_text(text).split("\n"):
        if not raw_line:
            continue

        fragments = split_sentences(raw_line)
        if len(fragments) == 1 and len(fragments[0]) > PARAGRAPH_MAX_CHARS:
            fragments = wrap_long_text(fragments[0], limit=PARAGRAPH_TARGET_CHARS)

        units.extend(fragment for fragment in fragments if fragment)

    deduped_units: list[str] = []
    previous_key = ""
    for unit in units:
        key = re.sub(r"[^가-힣A-Za-z0-9]+", "", unit).lower()
        if key and key == previous_key:
            continue
        deduped_units.append(unit)
        previous_key = key

    return deduped_units


def is_transition_unit(text: str) -> bool:
    candidate = text.strip()
    if not candidate:
        return False

    if "학습 목표" in candidate:
        return True

    if SECTION_TRANSITION_PATTERN.match(candidate):
        return True

    return bool(
        len(candidate) <= 120
        and re.search(
            r"(알아보도록 하겠습니다|확인해 보도록 하겠습니다|설명해 드리겠습니다|설명하겠습니다|"
            r"살펴보겠습니다|말씀드리겠습니다)$",
            candidate,
        )
    )


def build_paragraphs(units: list[str]) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []
    current_len = 0

    for unit in units:
        extra = len(unit) + (1 if current else 0)
        should_flush = current and (
            (is_transition_unit(unit) and current_len >= 120)
            or current_len + extra > PARAGRAPH_MAX_CHARS
            or len(current) >= PARAGRAPH_MAX_UNITS
        )

        if should_flush:
            paragraphs.append(" ".join(current).strip())
            current = []
            current_len = 0

        current.append(unit)
        current_len += len(unit) + (1 if len(current) > 1 else 0)

        if current_len >= PARAGRAPH_TARGET_CHARS:
            paragraphs.append(" ".join(current).strip())
            current = []
            current_len = 0

    if current:
        paragraphs.append(" ".join(current).strip())

    return paragraphs


def derive_block_title(paragraphs: list[str], index: int) -> str:
    if not paragraphs:
        return f"정리 {index:02d}"

    candidates = split_sentences(paragraphs[0])
    title = paragraphs[0].strip()
    for candidate in candidates:
        if re.search(r"^(?:네\s+안녕하세요|안녕하세요)", candidate):
            continue
        title = candidate.strip()
        break

    title = re.sub(r"^(?:네\s+안녕하세요[. ]*)", "", title)
    title = re.sub(
        r"^(?:"
        r"이번 시간에는|오늘은|먼저|첫 ?번째|두 ?번째|세 ?번째|"
        r"그러면|그럼|이제|다음(?:은|으로)?|이어서|이어(?:서)?|"
        r"마지막으로|정리하면|한편|여기서|다시|끝으로|간단하게|"
        r"또 하나(?:의)?|이와 관련해"
        r")\s*",
        "",
        title,
    )
    title = re.sub(
        r"\s*(?:에 대해서|을 중심으로|를 중심으로)?\s*"
        r"(?:간단하게\s*)?"
        r"(?:알아보도록|확인해 보도록|설명해 드리도록|설명하도록|설명하겠습니다|"
        r"살펴보도록|정리해 보도록|말씀드리도록)\s*하겠습니다\.?$",
        "",
        title,
    ).strip(" .")

    title = re.sub(
        r"\s*(?:배워보도록|알아보도록|확인해 보도록|살펴보도록|정리해 보도록)\s*하겠습니다\.?$",
        "",
        title,
    ).strip(" .")

    if len(title) > TITLE_MAX_CHARS:
        candidate = re.split(r"[,:]| 그리고 | 하지만 | 그래서 ", title)[0].strip()
        if 8 <= len(candidate) <= TITLE_MAX_CHARS:
            title = candidate

    if len(title) > TITLE_MAX_CHARS:
        title = f"{title[:TITLE_MAX_CHARS].rstrip()}…"

    return title or f"정리 {index:02d}"


def build_topic_candidates(lecture: dict) -> list[dict]:
    candidates: list[dict] = []
    seen_titles: set[str] = set()

    collection_order = [("concepts", "title", "body")]
    if not lecture.get("concepts"):
        collection_order.append(("basics", "title", "body"))

    for collection_name, title_key, body_key in collection_order:
        for item in lecture.get(collection_name, []):
            if not isinstance(item, dict):
                continue

            title = normalize_inline_text(item.get(title_key, ""))
            if not title or title in seen_titles:
                continue

            body = normalize_inline_text(item.get(body_key, ""))
            candidates.append(
                {
                    "title": title,
                    "title_tokens": extract_keyword_tokens(title),
                    "body_tokens": extract_keyword_tokens(body),
                }
            )
            seen_titles.add(title)

    return candidates


def score_topic_candidate(block_text: str, candidate: dict) -> float:
    block_tokens = set(extract_keyword_tokens(block_text))
    if not block_tokens:
        return 0

    title_overlap = [token for token in candidate["title_tokens"] if token in block_tokens]
    body_overlap = [token for token in candidate["body_tokens"] if token in block_tokens]

    score = len(title_overlap) * 4 + len(body_overlap)

    if len(title_overlap) >= 2:
        score += 4
    elif len(title_overlap) == 1:
        score += 1.5

    normalized_block = "".join(block_text.split()).lower()
    normalized_title = "".join(candidate["title"].split()).lower()
    if normalized_title and normalized_title in normalized_block:
        score += 8

    return score


def apply_large_topic_titles(blocks: list[dict], lecture: dict) -> list[dict]:
    candidates = build_topic_candidates(lecture)
    if not blocks or not candidates:
        return blocks

    scores = [[score_topic_candidate(block["text"], candidate) for candidate in candidates] for block in blocks]
    assigned_indices = [max(range(len(candidates)), key=lambda idx: scores[0][idx])]

    for block_index in range(1, len(blocks)):
        row = scores[block_index]
        current_index = assigned_indices[-1]
        current_score = row[current_index]
        best_index = current_index
        best_score = current_score
        block_text = blocks[block_index]["text"]
        has_transition = bool(
            re.search(r"(그러면|그럼|이제|다음은|다음으로|이어서|마지막으로|한편|여기서)", block_text[:80])
        )

        for candidate_index in range(current_index + 1, len(candidates)):
            candidate_score = row[candidate_index]
            if candidate_score > best_score:
                best_index = candidate_index
                best_score = candidate_score

            should_advance = (
                candidate_score >= current_score + 0.5
                or (has_transition and candidate_score >= max(current_score - 1.5, MIN_TOPIC_SCORE))
                or (current_score < MIN_TOPIC_SCORE and candidate_score >= MIN_TOPIC_SCORE)
            )
            if should_advance:
                best_index = candidate_index
                best_score = candidate_score
                break

        assigned_indices.append(best_index)

    for block_index, candidate_index in enumerate(assigned_indices):
        blocks[block_index]["title"] = candidates[candidate_index]["title"]

    return blocks


def make_transcript_blocks(text: str, lecture: dict | None = None) -> list[dict]:
    units = split_transcript_units(text)
    paragraphs = build_paragraphs(units)
    blocks: list[dict] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        extra = len(paragraph) + (1 if current else 0)
        should_flush = current and (
            (is_transition_unit(paragraph) and current_len >= BLOCK_MIN_CHARS)
            or current_len + extra > BLOCK_MAX_CHARS
            or len(current) >= BLOCK_MAX_PARAGRAPHS
        )

        if should_flush:
            blocks.append(
                {
                    "index": len(blocks) + 1,
                    "title": derive_block_title(current, len(blocks) + 1),
                    "paragraphs": current.copy(),
                    "text": " ".join(current).strip(),
                }
            )
            current = []
            current_len = 0

        current.append(paragraph)
        current_len += len(paragraph) + (1 if len(current) > 1 else 0)

        if current_len >= BLOCK_TARGET_CHARS:
            blocks.append(
                {
                    "index": len(blocks) + 1,
                    "title": derive_block_title(current, len(blocks) + 1),
                    "paragraphs": current.copy(),
                    "text": " ".join(current).strip(),
                }
            )
            current = []
            current_len = 0

    if current:
        blocks.append(
            {
                "index": len(blocks) + 1,
                "title": derive_block_title(current, len(blocks) + 1),
                "paragraphs": current.copy(),
                "text": " ".join(current).strip(),
            }
        )

    if lecture:
        apply_large_topic_titles(blocks, lecture)

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

        transcript_blocks = make_transcript_blocks(transcript_text, lecture=lecture)
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
