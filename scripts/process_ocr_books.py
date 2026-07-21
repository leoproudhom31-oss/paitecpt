"""Extract clean, 100%-Paite text from the OCR of the scanned Paite books
(Sintute Tehna, Late leh Thute), deduplicate against what is already in the
dataset, and append the genuinely new material.

Pipeline per book:
  1. Read the raw tesseract OCR (page-delimited by "===PAGE n===").
  2. Line cleaning: drop page headers / page numbers / stanza markers
     (roman numerals, "1.", "(a)"), strip OCR symbol noise, drop digits,
     drop English tokens and OCR-garbage tokens (camelCase, vowel-less).
  3. Chunk the surviving text into 80-200 word entries.
  4. Near-duplicate filtering with 4-gram shingles (normalised so OCR
     variants like "Geeltui"/"Geltui" collapse together) against the existing
     dataset AND across the newly-accepted chunks -> only new content is kept.

Nothing here invents Paite text; it only cleans and selects from the authentic
scanned sources.
"""

import json
import os
import re

# ---------------------------------------------------------------- config

MIN_WORDS, MAX_WORDS = 80, 200
DUP_4GRAM_THRESHOLD = 0.50   # >=50% of a chunk's 4-grams already seen => drop

# English / foreign tokens that are not Paite. Only words that are confidently
# NOT Paite are listed (avoid Paite look-alikes: "in","it","man","long","that").
EN_WORDS = {
    "the", "of", "to", "my", "at", "all", "and", "for", "with", "author",
    "copyright", "copyrights", "reserved", "rights", "chairman", "committee",
    "textbook", "literature", "vernacular", "varnacular", "telephone",
    "independence", "press", "convention", "society", "litt", "mission",
    "compound", "edition", "copy", "aman", "dedicated", "pioneer", "published",
    "printed", "culture", "hills", "english", "rocket", "chapter", "page",
    "report", "translator", "mother", "memorial", "gandhi", "bazar", "imphal",
    "paona", "mongolian", "pakistan", "january", "february", "march", "april",
    "june", "july", "august", "september", "october", "november", "december",
    "new", "york", "usa", "nefa", "longding", "note", "song", "songs", "poem",
    "grammar", "composition", "dictionary", "syntax", "preface", "book",
    "text", "school", "class", "lesson", "standard", "reader", "volume",
    "price", "high", "primary", "middle", "board", "education", "contents",
    "index", "appendix", "rupees",
}


def plausible_ratios(tokens):
    """Return (fraction len>=3, fraction with a vowel) over alpha tokens."""
    alpha = [re.sub(r"[^A-Za-z']", "", t) for t in tokens]
    alpha = [t for t in alpha if t]
    if not alpha:
        return (0.0, 0.0)
    ge3 = sum(1 for t in alpha if len(t) >= 3) / len(alpha)
    vow = sum(1 for t in alpha if re.search(r"[aeiouAEIOU]", t)) / len(alpha)
    return (ge3, vow)

PAGE_HEADER_RE = re.compile(r"pa[il]te\s+(sintute\s+tehna|late\s+leh\s+thute)",
                            re.IGNORECASE)
ROMAN_LINE_RE = re.compile(r"^[\s.,'`()|]*[ivxlcIVXLC]{1,6}[\s.,'`()|]*$")
MARKER_RE = re.compile(r"\(\s*[abAB]\s*\)")
ABBR_RE = re.compile(r"\b(?:[A-Za-z]\.){2,}[A-Za-z]?\.?")


def normalise_word(w):
    """Lowercase, keep a-z only, collapse repeated letters -> folds OCR
    doubling (Geeltui->geltui, luun->lun) for matching."""
    w = re.sub(r"[^a-z]", "", w.lower())
    w = re.sub(r"(.)\1+", r"\1", w)
    return w


def is_garbage_token(tok):
    core = tok.strip(".,;:!?'`")
    if not core:
        return True
    letters = re.sub(r"[^A-Za-z]", "", core)
    if not letters:
        return True
    # internal capital (camelCase OCR artefact) e.g. ktewWhh, baW
    if re.search(r"[a-z][A-Z]", core):
        return True
    # length >=3 with no vowel -> not a Paite word
    if len(letters) >= 3 and not re.search(r"[aeiouAEIOU]", letters):
        return True
    # lone stray letters except genuine Paite one-letter words
    if len(letters) == 1 and letters.lower() not in {"a", "e", "i", "o"}:
        return True
    return False


def clean_line(line):
    line = MARKER_RE.sub(" ", line)                 # (a) (b)
    line = ABBR_RE.sub(" ", line)                   # dotted abbreviations
    # normalise curly apostrophes, strip other non-Paite symbols
    line = line.replace("’", "'").replace("‘", "'")
    line = re.sub(r"[^A-Za-z'\s.,;:!?]", " ", line)  # keep letters/apostrophe/basic punct
    line = re.sub(r"\d+", " ", line)                # (already gone, belt-and-braces)

    kept = []
    for tok in line.split():
        alpha = re.sub(r"[^A-Za-z]", "", tok)
        low = re.sub(r"[^a-z']", "", tok.lower())
        if low in EN_WORDS:
            continue
        if alpha.isupper() and len(alpha) >= 2:   # ALL-CAPS stamps / titles
            continue
        if is_garbage_token(tok):
            continue
        kept.append(tok)

    # plausibility gate: drop OCR-garbage lines (calibrated on clean Paite)
    if len(kept) >= 3:
        ge3, vow = plausible_ratios(kept)
        if ge3 < 0.50 or vow < 0.90:
            return ""

    out = " ".join(kept)
    out = re.sub(r"\s+([,.;:!?])", r"\1", out)
    out = re.sub(r"\s{2,}", " ", out).strip(" .,;:-'")
    return out


def clean_book(raw_text):
    lines_out = []
    for line in raw_text.splitlines():
        s = line.strip()
        if not s or s.startswith("===PAGE") or "SKIPPED" in s:
            continue
        if PAGE_HEADER_RE.search(s):
            continue
        if ROMAN_LINE_RE.match(s):
            continue
        cleaned = clean_line(s)
        if len(cleaned.split()) >= 2:
            lines_out.append(cleaned)
    return " ".join(lines_out)


def chunk_text(text):
    sentences = re.split(r"(?<=[.!?;])\s+", text)
    chunks, cur, n = [], [], 0
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        wc = len(s.split())
        if n + wc > MAX_WORDS and n >= MIN_WORDS:
            chunks.append(" ".join(cur))
            cur, n = [s], wc
        else:
            cur.append(s)
            n += wc
    if cur:
        if chunks and n < MIN_WORDS // 2:
            chunks[-1] += " " + " ".join(cur)
        else:
            chunks.append(" ".join(cur))
    return chunks


def four_grams(text):
    ws = [normalise_word(w) for w in text.split()]
    ws = [w for w in ws if w]
    return {tuple(ws[i:i + 4]) for i in range(len(ws) - 3)}


def main():
    d = os.path.dirname(__file__)
    scratch = os.environ.get("OCR_SCRATCH", os.path.join(d, "..", "data", "raw"))
    jsonl = os.path.join(d, "..", "data", "processed", "dataset_paite.jsonl")

    existing = [json.loads(l) for l in open(jsonl, encoding="utf-8") if l.strip()]
    seen_grams = set()
    for e in existing:
        seen_grams |= four_grams(e["text"])
    print(f"Existing entries: {len(existing)}  (4-gram index: {len(seen_grams)})")

    existing_vocab = set()
    for e in existing:
        for w in e["text"].split():
            nw = normalise_word(w)
            if nw:
                existing_vocab.add(nw)

    books = [
        ("Sintute Tehna", "sintute_tehna_raw.txt"),
        ("Late leh Thute", "late_leh_thute_raw.txt"),
    ]

    new_entries, kept, dropped_dup = [], 0, 0
    new_vocab = set()
    for title, fname in books:
        path = os.path.join(scratch, fname)
        raw = open(path, encoding="utf-8").read()
        text = clean_book(raw)
        chunks = chunk_text(text)
        bk_keep = 0
        for ch in chunks:
            ge3, vow = plausible_ratios(ch.split())
            if ge3 < 0.55 or vow < 0.95:      # chunk-level garbage guard
                continue
            grams = four_grams(ch)
            if len(grams) < 4:
                continue
            seen = sum(1 for g in grams if g in seen_grams)
            if seen / len(grams) > DUP_4GRAM_THRESHOLD:
                dropped_dup += 1
                continue
            seen_grams |= grams          # so later chunks dedup against this one
            new_entries.append({"text": ch})
            for w in ch.split():
                nw = normalise_word(w)
                if nw and nw not in existing_vocab:
                    new_vocab.add(nw)
            bk_keep += 1
        kept += bk_keep
        print(f"  {title}: {len(chunks)} chunks -> {bk_keep} kept")

    print(f"\nKept new entries: {kept}   dropped as near-duplicate: {dropped_dup}")
    print(f"New unique word-types introduced: {len(new_vocab)}")

    with open(jsonl, "w", encoding="utf-8") as f:
        for e in existing + new_entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"Total dataset entries: {len(existing) + len(new_entries)}")


if __name__ == "__main__":
    main()
