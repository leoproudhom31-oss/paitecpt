#!/usr/bin/env bash
# OCR a scanned PDF page-by-page (renders one page, OCRs it, deletes the image).
# A per-page timeout guarantees no single page can hang the whole run.
# Usage: ocr_pdf.sh <input.pdf> <output.txt> [dpi] [page_timeout_seconds]
set -uo pipefail

PDF="$1"
OUT="$2"
DPI="${3:-200}"
TLIMIT="${4:-45}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# keep tesseract single-threaded so parallel book jobs stay predictable
export OMP_THREAD_LIMIT=1

PAGES=$(pdfinfo "$PDF" | awk '/^Pages/{print $2}')
: > "$OUT"

for ((p=1; p<=PAGES; p++)); do
    rm -f "$TMP"/pg-*.pgm
    timeout 30 pdftoppm -f "$p" -l "$p" -r "$DPI" -gray "$PDF" "$TMP/pg" >/dev/null 2>&1
    img=$(ls "$TMP"/pg-*.pgm 2>/dev/null | head -1)
    printf '\n===PAGE %d===\n' "$p" >> "$OUT"
    if [[ -n "$img" ]]; then
        timeout "$TLIMIT" tesseract "$img" - --psm 6 -l eng >> "$OUT" 2>/dev/null \
            || printf '[SKIPPED: OCR timeout]\n' >> "$OUT"
        rm -f "$img"
    else
        printf '[SKIPPED: render failed]\n' >> "$OUT"
    fi
done
echo "DONE: $PDF -> $OUT ($PAGES pages)"
