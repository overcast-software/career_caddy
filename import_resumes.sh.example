#!/usr/bin/env bash
set -euo pipefail
PATHS=(
  "Doug Headley -- Security Software Engineer.docx"
  "Doug Headley -- Security Software Engineer.docx"
  "Doug Headley -- Senior Full Stack Engineer.docx"
  "Doug Headley -- Senior Information Security Analyst.docx"
  "Doug Headley Senior Software Engineer.docx"
  "Doug Headley Senior Software Engineer.docx"
)

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: $0 [PATH ...] [--user-email EMAIL]"
  echo "If no PATHs are provided, uses PATHS array defined inside this script."
  exit 0
fi

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_root"

# Separate positional PATHs from flag args (e.g., --user-email)
positional=()
user_args=()
for arg in "$@"; do
  if [[ "$arg" == --* ]]; then
    user_args+=("$arg")
  else
    positional+=("$arg")
  fi
done

# If no PATHs passed on CLI, use PATHS array defined in this script
if [[ ${#positional[@]} -eq 0 ]]; then
  if [[ -z "${PATHS+x}" ]]; then
    echo "No paths provided and PATHS not set. Define PATHS=(...) in this script or pass paths as arguments." >&2
    exit 1
  fi
  positional=("${PATHS[@]}")
fi

# Loop through each path and call Python CLI appropriately (dir vs file)
for p in "${positional[@]}"; do
  if [[ -d "$p" ]]; then
    echo "Importing directory: $p"
    python3 cli/load_resume.py --dir "$p" "${user_args[@]}"
  else
    echo "Importing file: $p"
    python3 cli/load_resume.py --resume "$p" "${user_args[@]}"
  fi
done
