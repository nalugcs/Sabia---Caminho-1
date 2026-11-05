#!/usr/bin/env bash
# Backup do Postgres de produção.
# Uso: DATABASE_URL="postgresql://..." ./scripts/backup_db.sh
# Agende no cron/Render Job e mantenha os arquivos fora do servidor.

set -euo pipefail

: "${DATABASE_URL:?defina DATABASE_URL (connection string do Postgres)}"

mkdir -p backups
stamp="$(date +%Y%m%d-%H%M%S)"
out="backups/sabia-${stamp}.sql.gz"

pg_dump "$DATABASE_URL" | gzip > "$out"
echo "backup: $out ($(du -h "$out" | cut -f1))"
