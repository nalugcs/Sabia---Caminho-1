#!/usr/bin/env bash
# Restore de um backup .sql.gz gerado por backup_db.sh.
# Uso: DATABASE_URL="postgresql://..." ./scripts/restore_db.sh backups/arquivo.sql.gz
# ATENÇÃO: sobrescreve os dados atuais. Teste em um banco descartável primeiro.

set -euo pipefail

: "${DATABASE_URL:?defina DATABASE_URL (connection string do Postgres)}"
: "${1:?uso: $0 backups/sabia-AAAAMMDD-HHMMSS.sql.gz}"

test -f "$1" || { echo "arquivo não encontrado: $1" >&2; exit 1; }

echo "restaurando $1 em $DATABASE_URL"
gunzip -c "$1" | psql "$DATABASE_URL"
echo "restore concluído; rode /health e um fluxo de teste"
