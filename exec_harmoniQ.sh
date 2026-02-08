#!/bin/bash
# Launch HarmoniQ: setup env (venv), init DB, run web app.
# Uses Python's venv only (python3 -m venv); no pyenv.
#
# Demande (données de demande) :
#   --demande-db        utiliser la base demande.db (fichier harmoniQ/harmoniq/db/demande.db)
#   --demande-synthetic utiliser la synthèse (courbe en canard + saisonnalité), pas de fichier requis
#   (par défaut : db si demande.db existe, sinon synthetic)

set -e

# Project root = directory containing this script (and harmoniQ/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
HARMONIQ_DIR="$PROJECT_ROOT/harmoniQ"
DEFAULT_PORT=5000

# Parse options: demande mode
export HARMONIQ_DEMANDE_MODE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --demande-db)
            export HARMONIQ_DEMANDE_MODE=db
            shift
            ;;
        --demande-synthetic)
            export HARMONIQ_DEMANDE_MODE=synthetic
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --demande-db        Use real demand database (demande.db). File must exist."
            echo "  --demande-synthetic Use synthetic demand (duck curve + seasonal). No file needed."
            echo "  -h, --help          Show this help."
            echo ""
            echo "If neither --demande-db nor --demande-synthetic is set, demand data is automatic:"
            echo "  - use demande.db if present in harmoniQ/harmoniq/db/"
            echo "  - otherwise use synthetic demand."
            exit 0
            ;;
        *)
            echo "Unknown option: $1. Use -h or --help." >&2
            exit 1
            ;;
    esac
done

# Optional: user code for port offset (e.g. on shared servers)
codeutilisateur="$(echo "$USER" | grep -o '[0-9]\+' || true)"
if [ -n "$codeutilisateur" ]; then
    port=$((codeutilisateur + 5000))
else
    port="$DEFAULT_PORT"
fi

# Python: need 3.8–3.12 (numpy 1.26.4 and other deps do not support 3.14+)
PYTHON=""
for cand in python3.12 python3.11 python3.10 python3.9 python3.8 python3; do
    if command -v "$cand" &>/dev/null; then
        ver=$("$cand" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null) || true
        if [ -n "$ver" ]; then
            major=${ver%%.*}
            minor=${ver#*.}; minor=${minor%%.*}
            if [ "$major" -eq 3 ] && [ "$minor" -ge 8 ] && [ "$minor" -le 12 ]; then
                PYTHON="$cand"
                break
            fi
        fi
    fi
done
if [ -z "$PYTHON" ]; then
    echo "HarmoniQ requires Python 3.8–3.12 (numpy and deps do not support 3.14+)." >&2
    echo "Install e.g. Python 3.12:  brew install python@3.12" >&2
    echo "Then run this script again (it will prefer python3.12)." >&2
    exit 1
fi

# Python venv in project root: .venv
harmoniq_env="$PROJECT_ROOT/.venv"

need_venv=1
if [ -d "$harmoniq_env" ] && [ -x "$harmoniq_env/bin/python" ]; then
    ver=$("$harmoniq_env/bin/python" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null) || true
    if [ -n "$ver" ] && [ "$ver" -ge 8 ] && [ "$ver" -le 12 ]; then
        need_venv=0
    else
        echo "Removing existing .venv (Python 3.$ver not supported, need 3.8–3.12)."
        rm -rf "$harmoniq_env"
    fi
fi
if [ "$need_venv" -eq 1 ]; then
    echo "Creating Python venv at $harmoniq_env (using $PYTHON)"
    "$PYTHON" -m venv "$harmoniq_env"
fi

echo "Activating Python environment: $harmoniq_env"
# shellcheck source=/dev/null
source "$harmoniq_env/bin/activate"

# Install harmoniq from project
if ! pip show harmoniq &>/dev/null; then
    echo "Installing HarmoniQ..."
    pip install -e "$HARMONIQ_DIR[dev]"
else
    echo "HarmoniQ already installed."
fi

# Init DB (create + populate)
echo "Initializing database..."
init-db -p

# Find a free port if default is in use
while lsof -i ":$port" &>/dev/null; do
    old_port=$port
    port=$((port + 1))
    echo "Port $old_port in use, trying $port"
done

echo "Launching HarmoniQ on port $port"
[ -n "$HARMONIQ_DEMANDE_MODE" ] && echo "Demande: $HARMONIQ_DEMANDE_MODE"
echo "Open: http://127.0.0.1:$port"
exec launch-app --debug --host 0.0.0.0 --port "$port"
