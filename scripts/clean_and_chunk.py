import re
import json
import sys
import os

BOOKS_RE = (
    r"GENESIS|EXODUS|LEVITICUS|NUMBERS|DEUTERONOMY|JOSHUA|JUDGES|RUTH|"
    r"1 SAMUEL|2 SAMUEL|1 KINGS|2 KINGS|1 CHRONICLES|2 CHRONICLES|EZRA|"
    r"NEHEMIAH|ESTHER|JOB|PSALMS?|PROVERBS|ECCLESIASTES|"
    r"SONG OF SOLOMON|ISAIAH|JEREMIAH|LAMENTATIONS|EZEKIEL|DANIEL|HOSEA|"
    r"JOEL|AMOS|OBADIAH|JONAH|MICAH|NAHUM|HABAKKUK|ZEPHANIAH|HAGGAI|"
    r"ZECHARIAH|MALACHI|MATTHEW|MARK|LUKE|JOHN|ACTS|ROMANS|"
    r"1 CORINTHIANS|2 CORINTHIANS|GALATIANS|EPHESIANS|PHILIPPIANS|"
    r"COLOSSIANS|1 THESSALONIANS|2 THESSALONIANS|1 TIMOTHY|2 TIMOTHY|"
    r"TITUS|PHILEMON|HEBREWS|JAMES|1 PETER|2 PETER|1 JOHN|2 JOHN|"
    r"3 JOHN|JUDE|KILAKNA|REVELATION|NASEPTE"
)

NOISE_PATTERNS = [
    re.compile(
        r"Currently Selected:\s*(?:" + BOOKS_RE + r")\s+\d+:\s*PAITBSIHighlightCopyCompareShare"
        r"Want to have your highlights saved across all your devices\?\s*Sign up or sign in\s*"
        r"(?:Paite OV \(Re-edited\) Bible - Pathian Laisiangthou\s*"
        r"Copyright © \d+ by The Bible Society of India\s*"
        r"Used by permission\. All rights reserved worldwide\.\s*"
        r"Learn More About Pathian Laisiangthou \(BSI\)\s*)?"
    ),
    re.compile(
        r"Currently Selected:\s*(?:" + BOOKS_RE + r")\s+\d+:\s*PAITBSIHighlightCopyCompareShare"
        r"Want to have your highlights saved across all your devices\?\s*Sign up or sign in\s*"
    ),
    re.compile(
        r"Paite OV \(Re-edited\) Bible - Pathian Laisiangthou\s*"
        r"Copyright © \d+ by The Bible Society of India\s*"
        r"Used by permission\. All rights reserved worldwide\.\s*"
        r"Learn More About Pathian Laisiangthou \(BSI\)\s*"
    ),
    re.compile(r"file:///\S*"),
    re.compile(r"###\s+###"),
]


def remove_noise(text):
    for pat in NOISE_PATTERNS:
        text = pat.sub("", text)
    text = re.sub(r"[‍​‌‎‏﻿]", "", text)
    return text


def parse_file_chapters(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    text = remove_noise(text)

    chapter_re = re.compile(
        r"((?:" + BOOKS_RE + r")\s+\d+)"
    )

    parts = chapter_re.split(text)
    chapters = {}

    i = 1
    while i < len(parts) - 1:
        chapter_name = parts[i].strip().upper()
        chapter_body = parts[i + 1].strip()
        chapter_body = re.sub(r"\s+", " ", chapter_body).strip()

        if chapter_name not in chapters:
            chapters[chapter_name] = chapter_body

        i += 2

    return chapters


def extract_verses_first_only(text):
    text = re.sub(r"\s+", " ", text).strip()

    verse_re = re.compile(r"(?:^|(?<=\s))(\d{1,3})\s*(?=[A-Z\"])")
    matches = list(verse_re.finditer(text))

    if not matches:
        return text

    verses = {}
    for idx, m in enumerate(matches):
        vnum = int(m.group(1))
        start = m.start()
        if idx + 1 < len(matches):
            end = matches[idx + 1].start()
        else:
            end = len(text)
        verse_text = text[start:end].strip()

        if vnum not in verses:
            verses[vnum] = verse_text

    preamble = text[: matches[0].start()].strip()

    section_titles = re.findall(
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+(?:\s+[A-Z][a-z]+)*)", preamble
    )

    result = []
    if preamble:
        cleaned_preamble = re.sub(r"\d+\s*$", "", preamble).strip()
        if cleaned_preamble and len(cleaned_preamble) > 3:
            result.append(cleaned_preamble)

    for vnum in sorted(verses.keys()):
        result.append(verses[vnum])

    return " ".join(result)


def post_clean(text):
    text = re.sub(r"###\s*###", "", text)
    text = re.sub(r"\b(NASEPTE|GENESIS|EXODUS|KILAKNA)\s+\d+\s*$", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunk_text(text, min_words=150, max_words=300):
    sentences = re.split(r"(?<=[.!?;])\s+", text)
    chunks = []
    current_chunk = []
    current_word_count = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        word_count = len(sentence.split())

        if current_word_count + word_count > max_words and current_word_count >= min_words:
            chunks.append(" ".join(current_chunk))
            current_chunk = [sentence]
            current_word_count = word_count
        else:
            current_chunk.append(sentence)
            current_word_count += word_count

    if current_chunk:
        if chunks and current_word_count < min_words // 2:
            chunks[-1] += " " + " ".join(current_chunk)
        else:
            chunks.append(" ".join(current_chunk))

    return chunks


BOOK_ORDER = [
    "GENESIS", "EXODUS", "LEVITICUS", "NUMBERS", "DEUTERONOMY",
    "JOSHUA", "JUDGES", "RUTH", "1 SAMUEL", "2 SAMUEL",
    "1 KINGS", "2 KINGS", "1 CHRONICLES", "2 CHRONICLES",
    "EZRA", "NEHEMIAH", "ESTHER", "JOB", "PSALM", "PSALMS",
    "PROVERBS", "ECCLESIASTES", "SONG OF SOLOMON",
    "ISAIAH", "JEREMIAH", "LAMENTATIONS", "EZEKIEL", "DANIEL",
    "HOSEA", "JOEL", "AMOS", "OBADIAH", "JONAH", "MICAH",
    "NAHUM", "HABAKKUK", "ZEPHANIAH", "HAGGAI", "ZECHARIAH", "MALACHI",
    "MATTHEW", "MARK", "LUKE", "JOHN", "ACTS", "NASEPTE", "ROMANS",
    "1 CORINTHIANS", "2 CORINTHIANS", "GALATIANS", "EPHESIANS",
    "PHILIPPIANS", "COLOSSIANS", "1 THESSALONIANS", "2 THESSALONIANS",
    "1 TIMOTHY", "2 TIMOTHY", "TITUS", "PHILEMON", "HEBREWS",
    "JAMES", "1 PETER", "2 PETER", "1 JOHN", "2 JOHN", "3 JOHN",
    "JUDE", "KILAKNA", "REVELATION",
]


def chapter_sort_key(name):
    match = re.match(r"(.+?)\s+(\d+)$", name)
    if match:
        book = match.group(1)
        chapter_num = int(match.group(2))
    else:
        book = name
        chapter_num = 0
    try:
        book_idx = BOOK_ORDER.index(book)
    except ValueError:
        book_idx = 999
    return (book_idx, chapter_num)


def main():
    input_files = sys.argv[1:] if len(sys.argv) > 1 else []
    if not input_files:
        input_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
        if os.path.isdir(input_dir):
            input_files = [
                os.path.join(input_dir, f)
                for f in sorted(os.listdir(input_dir))
                if f.endswith(".txt")
            ]

    if not input_files:
        print("Usage: python clean_and_chunk.py <file1.txt> [file2.txt ...]")
        sys.exit(1)

    output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
    os.makedirs(output_dir, exist_ok=True)

    all_chapters = {}

    for filepath in input_files:
        print(f"Processing {os.path.basename(filepath)}...")
        chapters = parse_file_chapters(filepath)
        for name, body in chapters.items():
            if name not in all_chapters:
                all_chapters[name] = body

    print(f"\nFound {len(all_chapters)} unique chapters")

    cleaned_path = os.path.join(output_dir, "bible_paite_cleaned.txt")
    jsonl_path = os.path.join(output_dir, "dataset_paite.jsonl")

    all_chunks = []

    with open(cleaned_path, "w", encoding="utf-8") as f_clean:
        for chapter_name in sorted(all_chapters.keys(), key=chapter_sort_key):
            raw_body = all_chapters[chapter_name]
            clean_body = extract_verses_first_only(raw_body)
            clean_body = post_clean(clean_body)

            if len(clean_body.split()) < 10:
                continue

            f_clean.write(f"\n=== {chapter_name} ===\n\n")
            f_clean.write(clean_body)
            f_clean.write("\n")

            chunks = chunk_text(clean_body)
            for chunk in chunks:
                chunk = chunk.strip()
                if len(chunk.split()) >= 10:
                    all_chunks.append({"text": f"{chapter_name}: {chunk}"})

    with open(jsonl_path, "w", encoding="utf-8") as f_jsonl:
        for entry in all_chunks:
            f_jsonl.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Cleaned text saved to: {cleaned_path}")
    print(f"JSONL dataset saved to: {jsonl_path}")
    print(f"Total chunks: {len(all_chunks)}")

    word_counts = [len(c["text"].split()) for c in all_chunks]
    if word_counts:
        print(f"Avg words/chunk: {sum(word_counts) / len(word_counts):.0f}")
        print(f"Min words/chunk: {min(word_counts)}")
        print(f"Max words/chunk: {max(word_counts)}")


if __name__ == "__main__":
    main()
