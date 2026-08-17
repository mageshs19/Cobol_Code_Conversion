from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

import pdfplumber


DEFAULT_PDF_PATH = Path(r"C:\VSCode\Source-Code\output\phase2-17-08-2026.pdf")

PROJECT_ROOT_MARKER = "IDMS-DB2-Code-Conversion"

TARGET_FILES = {
    "patterns/field_usage_patterns.py",
    "src/idms_db2_phase2/analyzers/field_usage_analyzer.py",
    "rules/validation_rules.py",
    "src/idms_db2_phase2/services/validation_service.py",
    "src/idms_db2_phase2/orchestration/conversion_service.py",
    "src/idms_db2_phase2/services/conversion_service.py",
    "rules/fixed_format_rules.py",
    "patterns/fixed_format_patterns.py",
    "patterns/fixed_format_rules.py",
    "src/idms_db2_phase2/composers/fixed_format_line_parser.py",
    "src/idms_db2_phase2/composers/fixed_format_body_formatter.py",
    "src/idms_db2_phase2/composers/fixed_format_wrapper.py",
    "src/idms_db2_phase2/composers/fixed_format_sequence_manager.py",
    "src/idms_db2_phase2/composers/fixed_format_composer.py",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recover exported project files from the phase2 PDF export."
    )
    parser.add_argument(
        "pdf_path",
        nargs="?",
        default=str(DEFAULT_PDF_PATH),
        help=(
            "Path to phase2-17-08-2026.pdf. "
            f"Default: {DEFAULT_PDF_PATH}"
        ),
    )
    parser.add_argument(
        "--output",
        default="recovered_from_pdf",
        help="Output folder for recovered files. Default: recovered_from_pdf",
    )
    parser.add_argument(
        "--restore-targets",
        action="store_true",
        help="Also copy recovered Batch 1 and Batch 2 target files into the project.",
    )
    parser.add_argument(
        "--restore-all",
        action="store_true",
        help="Copy all recovered files into the current project. Use carefully.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Only list recovered file paths.",
    )

    args = parser.parse_args()

    pdf_path = Path(args.pdf_path).resolve()
    output_dir = Path(args.output).resolve()
    project_root = Path.cwd().resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    extracted_text = extract_pdf_text(pdf_path)
    files = split_exported_files(extracted_text)

    if not files:
        raise RuntimeError(
            "No files were recovered. Check whether the PDF text contains FILE markers."
        )

    written = write_recovered_files(
        files=files,
        output_dir=output_dir,
    )

    print("")
    print("PDF recovery completed.")
    print(f"PDF path             : {pdf_path}")
    print(f"Project root         : {project_root}")
    print(f"Recovery output      : {output_dir}")
    print(f"Recovered file count : {written}")
    print("")

    if args.list:
        print("Recovered files:")
        for relative_path in sorted(files):
            print(f" - {relative_path}")
        return

    target_matches = list_target_matches(files)

    print("Batch 1 and Batch 2 files found in PDF:")
    if target_matches:
        for relative_path in target_matches:
            print(f" - {relative_path}")
    else:
        print(" - None")

    missing_targets = missing_target_files(target_matches)

    if missing_targets:
        print("")
        print("Batch 1 and Batch 2 files NOT found exactly by path:")
        for relative_path in missing_targets:
            print(f" - {relative_path}")

    if args.restore_targets:
        restore_files(
            files_to_restore=target_matches,
            output_dir=output_dir,
            project_root=project_root,
        )

    if args.restore_all:
        restore_files(
            files_to_restore=sorted(files),
            output_dir=output_dir,
            project_root=project_root,
        )


def extract_pdf_text(
    pdf_path: Path,
) -> str:
    page_texts: list[str] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(
                x_tolerance=1,
                y_tolerance=3,
                layout=False,
            )

            if not text:
                print(f"Warning: no text extracted from page {page_index}.")
                continue

            page_texts.append(text)

    return "\n".join(page_texts)


def split_exported_files(
    extracted_text: str,
) -> dict[str, str]:
    lines = extracted_text.splitlines()

    files: dict[str, list[str]] = {}
    current_path = ""
    current_lines: list[str] = []

    for raw_line in lines:
        line = raw_line.rstrip()

        file_path = parse_file_marker(line)

        if file_path:
            if current_path:
                files.setdefault(current_path, []).extend(current_lines)

            current_path = normalize_export_path(file_path)
            current_lines = []
            continue

        if not current_path:
            continue

        if is_export_noise_line(line):
            continue

        if is_encoding_line(line):
            continue

        current_lines.append(clean_export_line(line))

    if current_path:
        files.setdefault(current_path, []).extend(current_lines)

    cleaned_files: dict[str, str] = {}

    for path, content_lines in files.items():
        normalized_path = normalize_export_path(path)

        if not normalized_path:
            continue

        cleaned_files[normalized_path] = cleanup_file_content(
            "\n".join(content_lines)
        )

    return cleaned_files


def parse_file_marker(
    line: str,
) -> str:
    text = str(line or "").strip()

    if not text.startswith("FILE:"):
        return ""

    text = text[len("FILE:") :].strip()

    encoding_index = text.upper().find("ENCODING:")

    if encoding_index >= 0:
        text = text[:encoding_index].strip()

    return text


def normalize_export_path(
    file_path: str,
) -> str:
    path = str(file_path or "").strip()

    path = path.replace("\\", "/")
    path = path.replace("\u00a0", " ")
    path = re.sub(r"\s+", " ", path)

    marker = PROJECT_ROOT_MARKER + "/"

    if marker in path:
        path = path.split(marker, 1)[1]

    path = path.strip("/ ")

    path = fix_common_pdf_path_spacing(path)
    path = fix_init_file_name(path)
    path = fix_known_pdf_path_errors(path)

    return path


def fix_common_pdf_path_spacing(
    path: str,
) -> str:
    fixed = path

    fixed = re.sub(
        r"\s+\.(py|md|txt|toml|csv|json|yaml|yml)$",
        r".\1",
        fixed,
        flags=re.IGNORECASE,
    )

    fixed = re.sub(
        r"\s+/",
        "/",
        fixed,
    )

    fixed = re.sub(
        r"/\s+",
        "/",
        fixed,
    )

    fixed = fixed.replace(" .py", ".py")
    fixed = fixed.replace(" .md", ".md")
    fixed = fixed.replace(" .txt", ".txt")
    fixed = fixed.replace(" .toml", ".toml")
    fixed = fixed.replace(" .csv", ".csv")

    return fixed


def fix_init_file_name(
    path: str,
) -> str:
    parts = path.split("/")
    fixed_parts: list[str] = []

    for part in parts:
        clean = part.strip()

        normalized = clean.replace(" ", "")
        normalized = normalized.replace("_init__", "__init__")
        normalized = normalized.replace("__init_", "__init__")
        normalized = normalized.replace("_init_", "__init__")
        normalized = normalized.replace("_init__.py", "__init__.py")
        normalized = normalized.replace("__init_.py", "__init__.py")
        normalized = normalized.replace("_init_.py", "__init__.py")

        if normalized.lower() in {
            "__init__.py",
            "__init__py",
            "__init__.py",
        }:
            clean = "__init__.py"
        else:
            clean = normalized

        fixed_parts.append(clean)

    return "/".join(fixed_parts)


def fix_known_pdf_path_errors(
    path: str,
) -> str:
    fixed = path

    fixed = fixed.replace(
        "src/idms_db2_phase2/transformers /",
        "src/idms_db2_phase2/transformers/",
    )
    fixed = fixed.replace("catalogs /", "catalogs/")
    fixed = fixed.replace("config /", "config/")

    return fixed


def is_export_noise_line(
    line: str,
) -> bool:
    text = str(line or "").strip()

    if not text:
        return False

    if text.startswith("<!-- PageNumber="):
        return True

    if text.startswith("<!-- PageBreak"):
        return True

    if text.startswith("<!-- PageHeader="):
        return True

    if text.startswith("<!-- PageFooter="):
        return True

    if re.fullmatch(r"Page\s+\d+", text, flags=re.IGNORECASE):
        return True

    if re.fullmatch(
        r"PageNumber\s*=\s*['\"]?Page\s+\d+['\"]?",
        text,
        flags=re.IGNORECASE,
    ):
        return True

    if re.fullmatch(r"PageBreak", text, flags=re.IGNORECASE):
        return True

    if re.fullmatch(r"PageHeader=.*", text, flags=re.IGNORECASE):
        return True

    if re.fullmatch(r"PageFooter=.*", text, flags=re.IGNORECASE):
        return True

    if text.startswith("[") and "result(s)" in text and "truncated" in text:
        return True

    if text == "[Empty file]":
        return False

    if is_separator_line(text):
        return True

    if text in {"☒", "﻿"}:
        return True

    return False


def is_separator_line(
    text: str,
) -> bool:
    clean = str(text or "").strip()

    if not clean:
        return False

    if len(clean) < 8:
        return False

    separator_chars = set(clean)

    allowed = {
        "=",
        "-",
        "_",
        "*",
        "#",
        "—",
        "–",
    }

    return separator_chars.issubset(allowed)


def is_encoding_line(
    line: str,
) -> bool:
    text = str(line or "").strip().upper()

    return text.startswith("ENCODING:")


def clean_export_line(
    line: str,
) -> str:
    text = str(line or "").rstrip()

    if text == "[Empty file]":
        return ""

    text = text.replace("\u00a0", " ")

    return text


def cleanup_file_content(
    content: str,
) -> str:
    text = str(content or "")

    text = text.replace("\ufeff", "")
    text = text.replace("\u00a0", " ")

    lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        if is_export_noise_line(line):
            continue

        lines.append(line)

    text = "\n".join(lines)

    text = re.sub(
        r"\n{4,}",
        "\n\n\n",
        text,
    )

    return text.rstrip() + "\n"


def write_recovered_files(
    files: dict[str, str],
    output_dir: Path,
) -> int:
    count = 0

    for relative_path, content in sorted(files.items()):
        if not relative_path:
            continue

        target_path = output_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(
            content,
            encoding="utf-8",
        )
        count += 1

    return count


def list_target_matches(
    files: dict[str, str],
) -> list[str]:
    normalized_files = {
        normalize_compare_path(path): path
        for path in files
    }

    matches: list[str] = []

    for target in sorted(TARGET_FILES):
        normalized_target = normalize_compare_path(target)

        if normalized_target in normalized_files:
            matches.append(normalized_files[normalized_target])

    return matches


def missing_target_files(
    target_matches: list[str],
) -> list[str]:
    matched_normalized = {
        normalize_compare_path(path)
        for path in target_matches
    }

    missing: list[str] = []

    for target in sorted(TARGET_FILES):
        if normalize_compare_path(target) not in matched_normalized:
            missing.append(target)

    return missing


def normalize_compare_path(
    value: str,
) -> str:
    return str(value or "").replace("\\", "/").strip("/ ").lower()


def restore_files(
    files_to_restore: list[str],
    output_dir: Path,
    project_root: Path,
) -> None:
    print("")
    print("Restoring recovered files into current project...")

    for relative_path in files_to_restore:
        source_path = output_dir / relative_path
        target_path = project_root / relative_path

        if not source_path.exists():
            print(f"Skip missing recovered source: {source_path}")
            continue

        target_path.parent.mkdir(parents=True, exist_ok=True)

        if target_path.exists():
            backup_path = next_backup_path(target_path)
            shutil.copy2(target_path, backup_path)
            print(f"Backup current file: {backup_path}")

        shutil.copy2(source_path, target_path)
        print(f"Restored: {relative_path}")

    print("")
    print("Restore completed.")


def next_backup_path(
    target_path: Path,
) -> Path:
    base_backup_path = target_path.with_suffix(
        target_path.suffix + ".broken_before_pdf_restore"
    )

    if not base_backup_path.exists():
        return base_backup_path

    index = 1

    while True:
        candidate = target_path.with_suffix(
            target_path.suffix + f".broken_before_pdf_restore_{index}"
        )

        if not candidate.exists():
            return candidate

        index += 1


if __name__ == "__main__":
    main()