import re
import json
import os

def chunk_text(text, min_words=80, max_words=200):
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


def parse_sections(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    section_re = re.compile(r"^=== (.+?) ===$", re.MULTILINE)
    parts = section_re.split(text)

    sections = {}
    i = 1
    while i < len(parts) - 1:
        section_name = parts[i].strip()
        section_body = parts[i + 1].strip()
        section_body = re.sub(r"\s+", " ", section_body).strip()
        if section_name and section_body and len(section_body.split()) >= 10:
            sections[section_name] = section_body
        i += 2

    return sections


def main():
    script_dir = os.path.dirname(__file__)
    raw_file = os.path.join(script_dir, "..", "data", "raw", "paite_la_gousiah_1960.txt")
    jsonl_path = os.path.join(script_dir, "..", "data", "processed", "dataset_paite.jsonl")

    existing_entries = []
    if os.path.exists(jsonl_path):
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    existing_entries.append(json.loads(line))

    print(f"Existing dataset entries: {len(existing_entries)}")

    sections = parse_sections(raw_file)
    print(f"Found {len(sections)} sections in La Gousiah")

    new_entries = []
    for section_name, body in sections.items():
        prefix = f"PAITE LA GOUSIAH - {section_name}"
        chunks = chunk_text(body)
        for chunk in chunks:
            chunk = chunk.strip()
            if len(chunk.split()) >= 10:
                new_entries.append({"text": f"{prefix}: {chunk}"})

    print(f"New entries from La Gousiah: {len(new_entries)}")

    all_entries = existing_entries + new_entries

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for entry in all_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Total dataset entries: {len(all_entries)}")
    print(f"Dataset saved to: {jsonl_path}")

    word_counts = [len(e["text"].split()) for e in new_entries]
    if word_counts:
        print(f"New entries - Avg words/chunk: {sum(word_counts) / len(word_counts):.0f}")
        print(f"New entries - Min words/chunk: {min(word_counts)}")
        print(f"New entries - Max words/chunk: {max(word_counts)}")


if __name__ == "__main__":
    main()
