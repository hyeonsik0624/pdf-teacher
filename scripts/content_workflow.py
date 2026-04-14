from __future__ import annotations

import json
import logging
import re
import unicodedata
from fnmatch import fnmatch
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover - runtime guard
    raise SystemExit(
        "pypdf가 필요합니다. `.venv/bin/python -m pip install -r requirements.txt` 후 다시 실행하세요."
    ) from exc


logging.getLogger("pypdf").setLevel(logging.ERROR)

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"
COURSES_DIR = CONTENT_DIR / "courses"
TEMPLATES_DIR = CONTENT_DIR / "templates"
OUTPUT_FILE = ROOT / "study-data.js"


def natural_key(value: str) -> list[object]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "lecture"


def normalize_source_name(value: str) -> str:
    return unicodedata.normalize("NFC", value.replace("\\", "/"))


def prettify_title(file_name: str) -> str:
    stem = Path(file_name).stem
    title = re.sub(r"^\s*lec\d+[-_\s]*", "", stem, flags=re.IGNORECASE)
    title = re.sub(r"^\s*lab\d+[-_\s]*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^\s*practice[-_\s]*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^\s*\[\d+주차\]\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"[-_]+", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title or stem


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def count_pdf_pages(path: Path) -> int:
    return len(PdfReader(str(path)).pages)


def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    chunks: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        chunks.append(f"=== PAGE {index} ===\n{text.strip()}\n")
    return "\n".join(chunks).strip() + "\n"


def read_text_source(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").strip() + "\n"


def count_text_characters(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="ignore").strip())


def _normalize_patterns(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [normalize_source_name(str(value)) for value in values if isinstance(value, str) and value.strip()]


def _is_hidden_relative(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def get_source_extensions(meta: dict) -> list[str]:
    values = meta.get("sourceExtensions")
    if isinstance(values, list):
        extensions = []
        for value in values:
            if not isinstance(value, str) or not value.strip():
                continue
            extension = value.lower()
            if not extension.startswith("."):
                extension = f".{extension}"
            extensions.append(extension)
        if extensions:
            return extensions
    return [".pdf"]


def list_source_files(meta: dict) -> list[Path]:
    source_folder = Path(meta["sourceFolder"]).expanduser()
    recursive = bool(meta.get("sourceRecursive", False))
    extensions = set(get_source_extensions(meta))
    exclude_patterns = _normalize_patterns(meta.get("sourceExcludePatterns"))

    if recursive:
        candidates = [path for path in source_folder.rglob("*") if path.is_file()]
    else:
        candidates = [path for path in source_folder.glob("*") if path.is_file()]

    source_paths: list[Path] = []
    for path in candidates:
        if path.suffix.lower() not in extensions:
            continue

        relative_path = path.relative_to(source_folder)
        if _is_hidden_relative(relative_path):
            continue

        normalized_relative = normalize_source_name(relative_path.as_posix())
        if any(fnmatch(normalized_relative, pattern) or fnmatch(path.name, pattern) for pattern in exclude_patterns):
            continue

        source_paths.append(path)

    return sorted(
        source_paths,
        key=lambda path: natural_key(normalize_source_name(path.relative_to(source_folder).as_posix())),
    )


def describe_source_file(path: Path, source_folder: Path) -> dict:
    relative_name = normalize_source_name(path.relative_to(source_folder).as_posix())
    display_name = normalize_source_name(path.name)
    source_type = path.suffix.lower().lstrip(".")

    if path.suffix.lower() == ".pdf":
        metric = count_pdf_pages(path)
        metric_label = f"{metric}p"
    else:
        metric = count_text_characters(path)
        metric_label = f"{metric:,}자"

    return {
        "file": relative_name,
        "name": display_name,
        "type": source_type,
        "metric": metric,
        "metricLabel": metric_label,
    }


def extract_source_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return extract_pdf_text(path)
    return read_text_source(path)


def get_source_stat_labels(meta: dict, sources: list[dict]) -> tuple[str, str]:
    count_label = meta.get("statsSourceCountLabel")
    measure_label = meta.get("statsSourceMeasureLabel")
    if isinstance(count_label, str) and count_label.strip() and isinstance(measure_label, str) and measure_label.strip():
        return count_label, measure_label

    source_types = {source.get("type") for source in sources}
    if source_types == {"pdf"}:
        return "PDF 묶음", "총 페이지"
    if source_types == {"txt"}:
        return "TXT 전사", "총 글자 수"
    return "자료 묶음", "총 분량"


def list_course_dirs() -> list[Path]:
    if not COURSES_DIR.exists():
        return []
    return sorted(
        [path for path in COURSES_DIR.iterdir() if path.is_dir() and not path.name.startswith(".")],
        key=lambda path: natural_key(path.name),
    )


def get_course_dir(course_id: str) -> Path:
    course_dir = COURSES_DIR / course_id
    if not course_dir.exists():
        available = ", ".join(path.name for path in list_course_dirs()) or "(none)"
        raise SystemExit(f"과목 '{course_id}'를 찾을 수 없습니다. 사용 가능한 과목: {available}")
    return course_dir


def resolve_course_dirs(course_id: str | None = None) -> list[Path]:
    if course_id:
        return [get_course_dir(course_id)]
    course_dirs = list_course_dirs()
    if not course_dirs:
        raise SystemExit(f"과목 디렉터리가 없습니다: {COURSES_DIR}")
    return course_dirs


def get_course_site_file(course_dir: Path) -> Path:
    return course_dir / "site.json"


def get_course_lectures_dir(course_dir: Path) -> Path:
    return course_dir / "lectures"


def make_draft_lecture(source_entry: dict, order: int) -> dict:
    suggested_file = f"{slugify(Path(source_entry['file']).stem)}.json"
    pretty_title = prettify_title(source_entry["file"])
    source_kind = source_entry.get("type", "source").upper()

    return {
        "id": f"draft-{slugify(Path(source_entry['file']).stem)}",
        "order": order,
        "status": "draft",
        "badge": "Draft",
        "type": "pending",
        "title": f"{pretty_title} 해설 준비 중",
        "source": source_entry["file"],
        "sourceDisplay": source_entry.get("name", source_entry["file"]),
        "sourceMetricLabel": source_entry.get("metricLabel", ""),
        "pages": source_entry.get("metric", 0),
        "theme": "새 자료 감지됨",
        "summary": "소스 파일은 자동으로 감지됐지만 아직 시험용 해설 데이터 파일이 작성되지 않았습니다.",
        "narrative": [
            f"이 {source_kind} 자료는 소스 폴더에서 자동 감지되었습니다. 지금 단계에서는 <code>{suggested_file}</code> 해설 파일이 없어서 임시 카드만 표시됩니다.",
            "새 강의를 본격 반영하려면 같은 과목의 기존 강의 JSON 하나를 복사해 제목, 요약, 핵심 개념, 시험용 카드, 체크리스트, 퀴즈를 채운 뒤 빌드 스크립트를 다시 실행하면 됩니다."
        ],
        "concepts": [],
        "commands": [],
        "pitfalls": [
            "PDF 파일 자체는 잡혔지만 아직 사람이 정리한 시험용 해설은 없습니다."
        ],
        "checklist": [
            "새 강의 JSON 파일을 추가한다.",
            "핵심 개념, 시험용 카드, 퀴즈를 채운다.",
            "<code>.venv/bin/python scripts/build-study-data.py</code>를 다시 실행한다."
        ],
        "quiz": []
    }


def _validate_str(value: object, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")


def _validate_list_of_str(values: object, label: str, errors: list[str]) -> None:
    if not isinstance(values, list):
        errors.append(f"{label} must be a list")
        return
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label}[{index}] must be a non-empty string")


def validate_site_data(site_data: dict, course_id: str = "course") -> list[str]:
    errors: list[str] = []
    meta = site_data.get("meta")
    if not isinstance(meta, dict):
        return [f"{course_id}.meta must be an object"]

    for field in ("title", "summary", "sourceFolder"):
        _validate_str(meta.get(field), f"{course_id}.meta.{field}", errors)

    if "sourceExtensions" in meta:
        _validate_list_of_str(meta.get("sourceExtensions"), f"{course_id}.meta.sourceExtensions", errors)

    if "sourceExcludePatterns" in meta:
        _validate_list_of_str(meta.get("sourceExcludePatterns"), f"{course_id}.meta.sourceExcludePatterns", errors)

    if "sourceRecursive" in meta and not isinstance(meta.get("sourceRecursive"), bool):
        errors.append(f"{course_id}.meta.sourceRecursive must be a boolean")

    _validate_list_of_str(site_data.get("fastRecall"), f"{course_id}.fastRecall", errors)

    if "starterGuide" in site_data and not isinstance(site_data.get("starterGuide"), list):
        errors.append(f"{course_id}.starterGuide must be a list")

    for field in ("examMap", "cramPlan", "vimCheat", "commandAtlas", "studyDrills"):
        if not isinstance(site_data.get(field), list):
            errors.append(f"{course_id}.{field} must be a list")

    for index, item in enumerate(site_data.get("starterGuide", [])):
        if not isinstance(item, dict):
            errors.append(f"{course_id}.starterGuide[{index}] must be an object")
            continue
        _validate_str(item.get("title"), f"{course_id}.starterGuide[{index}].title", errors)
        _validate_str(item.get("body"), f"{course_id}.starterGuide[{index}].body", errors)

    for index, item in enumerate(site_data.get("examMap", [])):
        if not isinstance(item, dict):
            errors.append(f"{course_id}.examMap[{index}] must be an object")
            continue
        _validate_str(item.get("title"), f"{course_id}.examMap[{index}].title", errors)
        _validate_str(item.get("body"), f"{course_id}.examMap[{index}].body", errors)

    for index, item in enumerate(site_data.get("cramPlan", [])):
        if not isinstance(item, dict):
            errors.append(f"{course_id}.cramPlan[{index}] must be an object")
            continue
        for field in ("time", "title", "body"):
            _validate_str(item.get(field), f"{course_id}.cramPlan[{index}].{field}", errors)

    for index, item in enumerate(site_data.get("vimCheat", [])):
        if not isinstance(item, dict):
            errors.append(f"{course_id}.vimCheat[{index}] must be an object")
            continue
        _validate_str(item.get("title"), f"{course_id}.vimCheat[{index}].title", errors)
        _validate_list_of_str(item.get("bullets"), f"{course_id}.vimCheat[{index}].bullets", errors)

    for index, group in enumerate(site_data.get("commandAtlas", [])):
        if not isinstance(group, dict):
            errors.append(f"{course_id}.commandAtlas[{index}] must be an object")
            continue
        _validate_str(group.get("title"), f"{course_id}.commandAtlas[{index}].title", errors)
        items = group.get("items")
        if not isinstance(items, list):
            errors.append(f"{course_id}.commandAtlas[{index}].items must be a list")
            continue
        for item_index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{course_id}.commandAtlas[{index}].items[{item_index}] must be an object")
                continue
            for field in ("name", "use", "compare", "example"):
                _validate_str(
                    item.get(field),
                    f"{course_id}.commandAtlas[{index}].items[{item_index}].{field}",
                    errors,
                )

    for index, item in enumerate(site_data.get("studyDrills", [])):
        if not isinstance(item, dict):
            errors.append(f"{course_id}.studyDrills[{index}] must be an object")
            continue
        for field in ("title", "body"):
            _validate_str(item.get(field), f"{course_id}.studyDrills[{index}].{field}", errors)
        _validate_list_of_str(item.get("bullets"), f"{course_id}.studyDrills[{index}].bullets", errors)

    return errors


def validate_lecture_data(lecture: dict, file_name: str = "lecture") -> list[str]:
    errors: list[str] = []
    required_string_fields = ("id", "badge", "type", "title", "source", "theme", "summary")
    for field in required_string_fields:
        _validate_str(lecture.get(field), f"{file_name}.{field}", errors)

    if "order" in lecture and not isinstance(lecture["order"], int):
        errors.append(f"{file_name}.order must be an integer")

    status = lecture.get("status", "ready")
    if status not in {"ready", "draft", "missing-source"}:
        errors.append(f"{file_name}.status must be ready, draft, or missing-source")

    lecture_type = lecture.get("type")
    if lecture_type not in {"core", "practice", "pending"}:
        errors.append(f"{file_name}.type must be core, practice, or pending")

    _validate_list_of_str(lecture.get("narrative"), f"{file_name}.narrative", errors)
    _validate_list_of_str(lecture.get("pitfalls"), f"{file_name}.pitfalls", errors)
    _validate_list_of_str(lecture.get("checklist"), f"{file_name}.checklist", errors)

    for field in ("concepts", "commands", "quiz"):
        if not isinstance(lecture.get(field), list):
            errors.append(f"{file_name}.{field} must be a list")

    for index, item in enumerate(lecture.get("concepts", [])):
        if not isinstance(item, dict):
            errors.append(f"{file_name}.concepts[{index}] must be an object")
            continue
        _validate_str(item.get("title"), f"{file_name}.concepts[{index}].title", errors)
        _validate_str(item.get("body"), f"{file_name}.concepts[{index}].body", errors)

    for index, item in enumerate(lecture.get("commands", [])):
        if not isinstance(item, dict):
            errors.append(f"{file_name}.commands[{index}] must be an object")
            continue
        for field in ("name", "syntax", "idea", "example", "pitfall"):
            _validate_str(item.get(field), f"{file_name}.commands[{index}].{field}", errors)

    for index, item in enumerate(lecture.get("quiz", [])):
        if not isinstance(item, dict):
            errors.append(f"{file_name}.quiz[{index}] must be an object")
            continue
        _validate_str(item.get("q"), f"{file_name}.quiz[{index}].q", errors)
        _validate_str(item.get("a"), f"{file_name}.quiz[{index}].a", errors)

    return errors
