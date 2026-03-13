import argparse
import math
from collections import Counter
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


def load_doc_terms(tokens_dir: Path, documents: dict[str, dict]) -> dict[str, list[str]]:
    stem_to_doc_id = build_doc_id_map(documents)
    doc_terms = {}

    for path in sorted(tokens_dir.glob("*_tokens.txt")):
        stem = path.stem.replace("_tokens", "")
        doc_id = stem_to_doc_id.get(stem)
        if not doc_id:
            continue
        doc_terms[doc_id] = read_values(path)

    return doc_terms


def load_doc_lemmas(lemmas_dir: Path, documents: dict[str, dict]) -> dict[str, list[str]]:
    stem_to_doc_id = build_doc_id_map(documents)
    doc_lemmas = {}

    for path in sorted(lemmas_dir.glob("*_lemmas.txt")):
        stem = path.stem.replace("_lemmas", "")
        doc_id = stem_to_doc_id.get(stem)
        if not doc_id:
            continue
        doc_lemmas[doc_id] = read_values(path)

    return doc_lemmas


def compute_idf(doc_values: dict[str, list[str]]) -> dict[str, float]:
    doc_freq = Counter()
    num_docs = len(doc_values)

    for values in doc_values.values():
        for item in set(values):
            doc_freq[item] += 1

    idf = {}
    for item, df in doc_freq.items():
        idf[item] = math.log(num_docs / df) if df else 0.0

    return idf


def compute_tf(values: list[str]) -> dict[str, float]:
    total = len(values)
    if total == 0:
        return {}

    counts = Counter(values)
    return {item: count / total for item, count in counts.items()}


def save_tfidf(
    output_dir: Path,
    documents: dict[str, dict],
    doc_values: dict[str, list[str]],
    idf_values: dict[str, float],
    suffix: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for doc_id, values in doc_values.items():
        tf_values = compute_tf(values)
        filename = documents[doc_id]["filename"]
        out_name = Path(filename).stem + suffix
        out_path = output_dir / out_name

        lines = []
        for item in sorted(tf_values.keys()):
            idf = idf_values.get(item, 0.0)
            tfidf = tf_values[item] * idf
            lines.append(f"{item} {idf:.6f} {tfidf:.6f}")

        out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute TF-IDF from per-document token and lemma files.")
    parser.add_argument("--mapping", default="index.txt", help="index.txt mapping file")
    parser.add_argument("--tokens-dir", default="tokens_by_doc", help="Directory with *_tokens.txt")
    parser.add_argument("--lemmas-dir", default="lemmas_by_doc", help="Directory with *_lemmas.txt")
    parser.add_argument("--terms-out", default="tfidf_terms", help="Output dir for term tf-idf files")
    parser.add_argument("--lemmas-out", default="tfidf_lemmas", help="Output dir for lemma tf-idf files")

    args = parser.parse_args()

    mapping_path = Path(args.mapping)
    tokens_dir = Path(args.tokens_dir)
    lemmas_dir = Path(args.lemmas_dir)
    terms_out_dir = Path(args.terms_out)
    lemmas_out_dir = Path(args.lemmas_out)

    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_path}")
    if not tokens_dir.exists():
        raise FileNotFoundError(f"Tokens directory not found: {tokens_dir}")
    if not lemmas_dir.exists():
        raise FileNotFoundError(f"Lemmas directory not found: {lemmas_dir}")

    documents = read_mapping(mapping_path)
    doc_terms = load_doc_terms(tokens_dir, documents)
    doc_lemmas = load_doc_lemmas(lemmas_dir, documents)

    idf_terms = compute_idf(doc_terms)
    idf_lemmas = compute_idf(doc_lemmas)

    save_tfidf(
        output_dir=terms_out_dir,
        documents=documents,
        doc_values=doc_terms,
        idf_values=idf_terms,
        suffix="_terms.txt",
    )

    save_tfidf(
        output_dir=lemmas_out_dir,
        documents=documents,
        doc_values=doc_lemmas,
        idf_values=idf_lemmas,
        suffix="_lemmas.txt",
    )

    print(f"Processed documents: {len(documents)}")
    print(f"Term output directory: {terms_out_dir}")
    print(f"Lemma output directory: {lemmas_out_dir}")
    print(f"Unique terms with IDF: {len(idf_terms)}")
    print(f"Unique lemmas with IDF: {len(idf_lemmas)}")


if __name__ == "__main__":
    main()