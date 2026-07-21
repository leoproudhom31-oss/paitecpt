#!/usr/bin/env bash
# OCR a scanned PDF page-by-page (renders one page, OCRs it, deletes the image).
# Usage: ocr_pdf.sh <input.pdf> <output.txt>
set -euo pipefail

PDF="$1"
OUT="$2"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PAGES=$(pdfinfo "$PDF" | awk '/^Pages/{print $2}')
: > "$OUT"

for ((p=1; p<=PAGES; p++)); do
    pdftoppm -f "$p" -l "$p" -r 300 -gray "$PDF" "$TMP/pg" >/dev/null 2>&1
    img=$(ls "$TMP"/pg-*.pgm 2>/dev/null | head -1)
    if [[ -n "$img" ]]; then
        printf '\n===PAGE %d===\n' "$p" >> "$OUT"
        tesseract "$img" - --psm 6 -l eng >> "$OUT" 2>/dev/null || true
        rm -f "$img"
    fi
done
echo "DONE: $PDF -> $OUT ($PAGES pages)"
