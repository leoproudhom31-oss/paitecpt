"""Clean dataset_paite.jsonl so it holds 100% Paite text.

Operations per entry:
  1. Drop the source-label prefix (e.g. "GENESIS 24: ", "PAITE LA GOUSIAH - JAWL LA: ").
  2. Remove every ASCII digit (Bible verse/chapter numbers glued to words like
     "2Lei" / "26Pathian", plus standalone verse numbers and dates).
  3. Remove clearly non-Paite tokens: dotted abbreviations (A.D., U.N., U.S.A.,
     P.N.C., I.A.S., T.S.) and English editorial words (The Chairman, Textbook
     Committee, Mission Compound, month names, Copyright, telephone, ...).
  4. Repair punctuation/space artifacts left behind by the removals.

Entries that end up too short (< 5 words) after cleaning are dropped.
"""

import json
import re
import os

# Dotted abbreviations: A.D., U.N., U.S.A., P.N.C., I.A.S., T.S., etc.
ABBR_RE = re.compile(r"\b(?:[A-Za-z]\.){2,}[A-Za-z]?\.?")

# English / foreign editorial tokens that are not Paite words.
EN_WORDS = [
    "The", "Chairman", "Author", "Copyright", "Copyrights", "reserved",
    "Committee", "Textbook", "Literature", "Vernacular", "Varnacular",
    "telephone", "Independence", "Press", "Convention", "Society", "Litt",
    "Mission", "Compound", "Edition", "Copy", "Aman", "Rs", "Dedicated",
    "Pioneer", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
    "New", "York", "USA", "NEFA", "Longding", "Published", "printed",
    "culture", "Hills",
]
EN_RE = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in EN_WORDS) + r")\b",
                   re.IGNORECASE)


def strip_prefix(text):
    m = re.match(r"^.*?:\s(.*)$", text, re.DOTALL)
    return m.group(1) if m else text


def clean_body(body):
    body = ABBR_RE.sub(" ", body)          # dotted abbreviations
    body = re.sub(r"\d+", " ", body)        # every digit
    body = EN_RE.sub(" ", body)             # english editorial words

    body = re.sub(r"\(\s*[-'’.,;:\s]*\)", " ", body)   # empty/junk parentheses
    body = re.sub(r"\s+([,.;:!?])", r"\1", body)       # space before punctuation
    body = re.sub(r"(?<!\w)[-'’](?!\w)", " ", body)    # orphaned dashes/apostrophes
    body = re.sub(r"([,;:.!?])(?:\s*[,;:])+", r"\1", body)  # punctuation runs
    body = re.sub(r"\s{2,}", " ", body).strip()

    # trim stray leading/trailing separators (but keep a final . ! ?)
    body = re.sub(r"^[\s,;:.\-'’]+", "", body)
    body = re.sub(r"[\s,;:\-'’]+$", "", body)
    return body


def main():
    script_dir = os.path.dirname(__file__)
    path = os.path.join(script_dir, "..", "data", "processed", "dataset_paite.jsonl")

    with open(path, encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]

    cleaned = []
    dropped = 0
    for e in entries:
        body = clean_body(strip_prefix(e["text"]))
        if len(body.split()) >= 5:
            cleaned.append({"text": body})
        else:
            dropped += 1

    with open(path, "w", encoding="utf-8") as f:
        for e in cleaned:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(f"Input entries:   {len(entries)}")
    print(f"Cleaned entries: {len(cleaned)}")
    print(f"Dropped (too short after cleaning): {dropped}")

    # sanity checks
    digits = sum(len(re.findall(r"\d", e["text"])) for e in cleaned)
    print(f"Remaining digit characters: {digits}")


if __name__ == "__main__":
    main()
