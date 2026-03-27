#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly VENV_DIR="$SCRIPT_DIR/venv"
readonly VENV_PYTHON="$VENV_DIR/bin/python"
readonly PYPROJECT_FILE="$SCRIPT_DIR/pyproject.toml"
readonly BOOTSTRAP_STAMP="$VENV_DIR/.newsr-bootstrap-complete"

cd "$SCRIPT_DIR"

read_required_python_version() {
  local version
  version="$(sed -nE 's/^requires-python = ">=([0-9]+)\.([0-9]+)".*/\1 \2/p' "$PYPROJECT_FILE" | head -n 1)"
  if [[ -z "$version" ]]; then
    echo "Unable to determine the minimum supported Python version from $PYPROJECT_FILE." >&2
    exit 1
  fi

  read -r REQUIRED_PYTHON_MAJOR REQUIRED_PYTHON_MINOR <<<"$version"
  readonly REQUIRED_PYTHON_MAJOR
  readonly REQUIRED_PYTHON_MINOR
}

python_satisfies_requirement() {
  local python_cmd="$1"
  "$python_cmd" -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= ($REQUIRED_PYTHON_MAJOR, $REQUIRED_PYTHON_MINOR) else 1)" \
    >/dev/null 2>&1
}

find_system_python() {
  local candidate
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && python_satisfies_requirement "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

ensure_virtualenv() {
  local bootstrap_python

  if [[ -x "$VENV_PYTHON" ]] && python_satisfies_requirement "$VENV_PYTHON"; then
    return 0
  fi

  if ! bootstrap_python="$(find_system_python)"; then
    cat <<EOF >&2
No compatible Python interpreter was found.

newsr requires Python ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR} or newer.
Install a compatible Python version and rerun:
  ./newsr.sh
EOF
    exit 1
  fi

  echo "Creating local virtual environment with $bootstrap_python..."
  "$bootstrap_python" -m venv "$VENV_DIR"
}

bootstrap_dependencies() {
  local needs_install=0

  if [[ ! -f "$BOOTSTRAP_STAMP" || "$PYPROJECT_FILE" -nt "$BOOTSTRAP_STAMP" ]]; then
    needs_install=1
  fi

  if ! "$VENV_PYTHON" -c "import bs4, newsr, PIL, textual, yaml" >/dev/null 2>&1; then
    needs_install=1
  fi

  if (( needs_install == 0 )); then
    return 0
  fi

  echo "Installing newsr into $VENV_DIR..."
  "$VENV_PYTHON" -m ensurepip --upgrade >/dev/null 2>&1 || true
  PIP_DISABLE_PIP_VERSION_CHECK=1 "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel
  PIP_DISABLE_PIP_VERSION_CHECK=1 "$VENV_PYTHON" -m pip install -e .
  touch "$BOOTSTRAP_STAMP"
}

read_required_python_version
ensure_virtualenv
bootstrap_dependencies

exec "$VENV_PYTHON" -m newsr "$@"
