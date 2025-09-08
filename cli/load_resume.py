import argparse
import os
import sys
from pathlib import Path
from typing import Set
from lib.models.user import User
from lib.models.resume import Resume
from lib.handlers.db_handler import DatabaseHandler
from lib.handlers.user_handler import resolve_user
from lib.exports.orgmode_export import OrgModeExport
from lib.handlers.chatgpt_handler import ai_client
from docx import Document

try:
    from pdfminer.high_level import extract_text as pdf_extract_text
except Exception:
    pdf_extract_text = None


def parse_arguments():
    parser = argparse.ArgumentParser(description="Load a resume into the database.")
    parser.add_argument(
        "--user-email",
        required=False,
        help="Email of the user to associate with the resume.",
    )
    parser.add_argument("--resume", type=str, help="Path to the resume file")
    parser.add_argument(
        "--dir", type=str, help="Directory of documents to import recursively."
    )
    return parser.parse_args()


def main():
    DatabaseHandler()
    args = parse_arguments()

    user = resolve_user(args)

    # Import from directory (recursive) or single file
    if args.dir:
        process_directory(args.dir, user)
        print("Import completed.")
        return

    resume_path = args.resume or os.getenv("RESUME_PATH")
    if not resume_path:
        raise ValueError(
            "Provide a resume file with --resume or set RESUME_PATH; or use --dir to import a directory."
        )
    process_single_file(resume_path, user)
    print(f"Resume for user {user.email} has been loaded successfully.")


SUPPORTED_EXTS = {".org", ".pdf", ".docx", ".md", ".txt"}


def convert_to_org(src: Path) -> Path:
    if src.suffix.lower() == ".org":
        return src
    dest = src.with_suffix(".org")
    if dest.exists():
        # Skip processing if destination already exists
        return dest
    text = extract_text(src)
    org_content = render_org(src.name, text, src.suffix.lower())
    dest.write_text(org_content, encoding="utf-8")
    return dest


def save_org_path(org_path: Path, user: User):
    resume = Resume.find_by(file_path=str(org_path))
    if not resume and org_path.exists():
        resume = Resume.from_path_and_user_id(str(org_path), user.id)
    if resume:
        resume.save()
        print(f"Imported: {org_path}")


def process_single_file(path_str: str, user: User):
    src = Path(path_str).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"File not found: {src}")
    if src.suffix.lower() not in SUPPORTED_EXTS:
        raise ValueError(
            f"Unsupported file type: {src.suffix}. Supported: {', '.join(sorted(SUPPORTED_EXTS))}"
        )
    org_path = convert_to_org(src) if src.suffix.lower() != ".org" else src
    save_org_path(org_path, user)


def extract_text(src: Path) -> str:
    ext = src.suffix.lower()
    if ext == ".docx":
        return extract_docx_text(src)
    if ext == ".pdf":
        return extract_pdf_text(src)
    if ext in (".md", ".txt"):
        return src.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(
        f"Unsupported file type: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTS))}"
    )


def extract_docx_text(path: Path) -> str:
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def extract_pdf_text(path: Path) -> str:
    if pdf_extract_text is None:
        raise RuntimeError(
            "PDF extraction requires pdfminer.six. Please install it (pip install pdfminer.six)."
        )
    try:
        return pdf_extract_text(str(path)) or ""
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from PDF {path}: {e}")


def render_org(filename: str, text: str, ext: str) -> str:
    myexport = OrgModeExport(ai_client, text)
    org_body = myexport.process()
    return org_body


def process_directory(dir_path: str, user: User):
    root = Path(dir_path).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")
    # First convert and import all non-.org files
    converted: Set[Path] = set()
    for src in root.rglob("*"):
        if not src.is_file():
            continue
        if src.suffix.lower() in SUPPORTED_EXTS and src.suffix.lower() != ".org":
            try:
                org_path = convert_to_org(src)
                converted.add(org_path.resolve())
                save_org_path(org_path, user)
            except Exception as e:
                print(f"Failed to convert/import {src}: {e}", file=sys.stderr)
    # Then import standalone .org files not produced above
    for org in root.rglob("*.org"):
        try:
            if org.resolve() not in converted:
                save_org_path(org, user)
        except Exception as e:
            print(f"Failed to import {org}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
