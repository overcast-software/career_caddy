import argparse
import os
import sys
from pathlib import Path
from typing import Set
from lib.models.user import User
from lib.models.resume import Resume
from lib.handlers.db_handler import DatabaseHandler
from docx import Document
from pdfminer.high_level import extract_text as pdf_extract_text


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

    # Determine user: prefer --user-email, then USERNAME env var, then DB heuristics
    if args.user_email:
        user = User.find_by(email=args.user_email)
        if not user:
            raise ValueError(
                f"No user found with email {args.user_email}."
                "Please create one with cli/load_user.py"
            )
    elif os.getenv("USERNAME"):
        user = User.find_by(name=os.getenv("USERNAME"))
        if not user:
            raise ValueError(f"No user found with name {os.getenv('USERNAME')}")
    else:
        user_count = User.count()
        if user_count == 1:
            user = User.first()
        elif user_count == 0:
            raise ValueError(
                "No users found in database. Please create a user first using cli/load_user.py"
            )
        else:
            raise ValueError(
                "Multiple users found. Please set USERNAME env var or use --user-email to select a user."
            )

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
    text = extract_text(src)
    dest = src.with_suffix(".org")
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
    return pdf_extract_text(str(path)) or ""


def render_org(filename: str, text: str, ext: str) -> str:
    header = f"#+TITLE: {filename}\n#+FILETAGS: :resume:\n\n* {filename}\n"
    # Keep original type as a source block language for clarity
    lang = "markdown" if ext == ".md" else "text"
    body = f"#+BEGIN_SRC {lang}\n{text}\n#+END_SRC\n"
    return header + body


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
