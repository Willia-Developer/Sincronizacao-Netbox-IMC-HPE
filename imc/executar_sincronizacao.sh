#!/usr/bin/env bash
set -euo pipefail
umask 077
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${IMC_PYTHON_BIN:-python3}"
# A configuração é lida pelo Python como dados, nunca executada como shell.
command -v flock >/dev/null || { echo "ERRO: flock não instalado" >&2; exit 2; }
exec 9>"$SCRIPT_DIR/../.wrapper.lock"
flock -n 9 || { echo "ERRO: outra execução está em andamento" >&2; exit 2; }
exec "$PYTHON_BIN" "$SCRIPT_DIR/sincronizacao_imc_netbox.py" "$@"
