#!/bin/bash
#
# nightly_mine.sh — Nightly batch: convert new Cursor transcripts and mine them.
# Run via cron on EC2:
#   0 2 * * * /opt/mempalace-env/bin/bash /opt/mempalace-repo/scripts/nightly_mine.sh >> /var/log/mempalace-nightly.log 2>&1

set -euo pipefail

VENV="/opt/mempalace-env"
REPO="/opt/mempalace-repo"
TRANSCRIPTS_ROOT="/data/transcripts"
CONVERTED_ROOT="/data/converted"
PYTHON="$VENV/bin/python"
MEMPALACE="$VENV/bin/mempalace"

# List of developers — edit this to match your team
DEVELOPERS=(alice bob carol dave eve)

source "$VENV/bin/activate"

echo "=== MemPalace nightly mine: $(date) ==="

for dev in "${DEVELOPERS[@]}"; do
    SRC="$TRANSCRIPTS_ROOT/$dev"
    OUT="$CONVERTED_ROOT/$dev"

    if [ ! -d "$SRC" ]; then
        echo "[$dev] No transcripts directory at $SRC — skipping"
        continue
    fi

    echo "[$dev] Converting new transcripts..."
    "$PYTHON" "$REPO/scripts/convert_cursor_transcripts.py" "$SRC" "$OUT" --developer "$dev" --incremental

    CONVERTED_COUNT=$(find "$OUT" -name "*.txt" -newer "$OUT/.last_mined" 2>/dev/null | wc -l || echo "0")
    if [ ! -f "$OUT/.last_mined" ] || [ "$CONVERTED_COUNT" -gt 0 ]; then
        echo "[$dev] Mining into wing_$dev..."
        "$MEMPALACE" mine "$OUT" --mode convos --wing "wing_$dev"
        touch "$OUT/.last_mined"
    else
        echo "[$dev] No new transcripts to mine"
    fi
done

echo "=== Nightly mine complete: $(date) ==="

# Backup to S3 (uncomment and configure)
# echo "Backing up palace to S3..."
# aws s3 sync ~/.mempalace/ s3://YOUR-BUCKET/mempalace-backup/ --delete
# echo "Backup complete"
