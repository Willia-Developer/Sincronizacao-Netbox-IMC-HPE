#!/usr/bin/env bash
# Remove a tarefa de sincronização IMC -> NetBox do crontab do usuário
# atual, sem mexer em nenhuma outra tarefa que você já tenha agendada.
#
# Uso:
#   ./desinstalar_cron.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/executar_sincronizacao.sh"

if ! command -v crontab >/dev/null; then
    echo "ERRO: comando 'crontab' não encontrado (instale o pacote cron)." >&2
    exit 1
fi

if [[ -z "$(crontab -l 2>/dev/null | grep -F "$SYNC_SCRIPT" || true)" ]]; then
    echo "Nada a remover: nenhuma tarefa de $SYNC_SCRIPT encontrada no crontab."
    exit 0
fi

# O "|| true" final é necessário: com set -e, um grep que filtra tudo e não
# sobra nenhuma linha retorna código de saída 1 — resultado esperado, não erro.
REMAINING="$(
    { crontab -l 2>/dev/null || true; } | grep -vF "$SYNC_SCRIPT" || true
)"

if [[ -n "$REMAINING" ]]; then
    printf '%s\n' "$REMAINING" | crontab -
else
    crontab -r
fi

echo "✅ Tarefa removida do crontab."
