#!/usr/bin/env bash
set -euo pipefail
sudo apt-get update && sudo apt-get install -y tree >/dev/null 2>&1 || true
{
  echo "# Snapshot: $(date -Iseconds)"
  echo "## Árbol"; tree -a app -I '__pycache__|*.pyc|.git|backups'
  echo; echo "## requirements.txt"; [ -f requirements.txt ] && sed 's/^/    /' requirements.txt || echo "    (no existe)"
  echo; echo "## .py files"
  find app -type f -name '*.py' -not -path '*/__pycache__/*' -print0 | sort -z | while IFS= read -r -d '' f; do
    echo "-----8<----- FILE: $f -----"; nl -ba "$f"; echo "-----8<----- END FILE: $f -----"
  done
} > app_completa.txt
echo "Generado app_completa.txt"
