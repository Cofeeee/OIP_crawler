import argparse
import json
from collections import defaultdict
from pathlib import Path


def read_mapping(index_txt_path: Path) -> dict[str, dict]:
    documents = {}

    for line in index_txt_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split("\t")
        if len(parts) < 3:
            continue

        doc_id, filename, url = parts[0], parts[1], parts[2]
        documents[doc_id] = {
            "filename": filename,
            "url": url,
        }

    return documents


def build_doc_id_map(documents: dict[str, dict]) -> dict[str, str]:
    """
    Преобразует:
    0001.html -> 1
    """
    result = {}
    for doc_id, meta in documents.items():
        stem = Path(meta["filename"]).stem
        result[stem] = doc_id
    return result


def read_values(path: Path) -> list[str]:
    values = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            values.append(line)
    return values


def build_inverted_index(
    lemmas_dir: Path,
    index_txt_path: Path,
) -> dict:
    documents = read_mapping(index_txt_path)
    stem_to_doc_id = build_doc_id_map(documents)

    inverted_index = defaultdict(set)

    lemma_files = sorted(lemmas_dir.glob("*_lemmas.txt"))

    for lemma_file in lemma_files:
        stem = lemma_file.stem.replace("_lemmas", "")
        doc_id = stem_to_doc_id.get(stem)

        if not doc_id:
            continue

        lemmas = set(read_values(lemma_file))

        for lemma in lemmas:
            inverted_index[lemma].add(doc_id)

    serializable_index = {
        "documents": documents,
        "index": {
            lemma: sorted(doc_ids, key=lambda x: int(x))
            for lemma, doc_ids in sorted(inverted_index.items(), key=lambda x: x[0])
        },
    }
    return serializable_index


def save_json_index(index_data: dict, output_path: Path) -> None:
    output_path.write_text(
        json.dumps(index_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_txt_index(index_data: dict, output_path: Path) -> None:
    lines = []
    for lemma, doc_ids in index_data["index"].items():
        lines.append(f"{lemma} " + " ".join(doc_ids))
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build inverted index from per-document lemma files.")
    parser.add_argument("--lemmas-dir", default="lemmas_by_doc", help="Directory with *_lemmas.txt files")
    parser.add_argument("--mapping", default="index.txt", help="index.txt mapping file")
    parser.add_argument("--json-out", default="inverted_index.json", help="JSON index output")
    parser.add_argument("--txt-out", default="inverted_index.txt", help="TXT index output")

    args = parser.parse_args()

    lemmas_dir = Path(args.lemmas_dir)
    mapping_path = Path(args.mapping)
    json_out = Path(args.json_out)
    txt_out = Path(args.txt_out)

    if not lemmas_dir.exists():
        raise FileNotFoundError(f"Lemmas directory not found: {lemmas_dir}")
    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_path}")

    index_data = build_inverted_index(
        lemmas_dir=lemmas_dir,
        index_txt_path=mapping_path,
    )

    save_json_index(index_data, json_out)
    save_txt_index(index_data, txt_out)

    print(f"Saved JSON index to: {json_out}")
    print(f"Saved TXT index to: {txt_out}")
    print(f"Indexed terms: {len(index_data['index'])}")
    print(f"Documents: {len(index_data['documents'])}")


if __name__ == "__main__":
    main()