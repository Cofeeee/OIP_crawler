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


def compute_idf(doc_lemmas: dict[str, list[str]]) -> dict[str, float]:
    num_docs = len(doc_lemmas)
    df_counter = Counter()

    for lemmas in doc_lemmas.values():
        for lemma in set(lemmas):
            df_counter[lemma] += 1

    idf = {}
    for lemma, df in df_counter.items():
        idf[lemma] = math.log(num_docs / df) if df else 0.0

    return idf


def compute_doc_vectors(doc_lemmas: dict[str, list[str]], idf: dict[str, float]) -> dict[str, dict[str, float]]:
    doc_vectors = {}

    for doc_id, lemmas in doc_lemmas.items():
        total_terms = len(lemmas)
        if total_terms == 0:
            doc_vectors[doc_id] = {}
            continue

        counts = Counter(lemmas)
        vector = {}

        for lemma, count in counts.items():
            tf = count / total_terms
            vector[lemma] = tf * idf.get(lemma, 0.0)

        doc_vectors[doc_id] = vector

    return doc_vectors


def normalize_query(query: str) -> list[str]:
    return [part.strip().lower() for part in query.split() if part.strip()]


def build_query_vector(query_lemmas: list[str], idf: dict[str, float]) -> dict[str, float]:
    total_terms = len(query_lemmas)
    if total_terms == 0:
        return {}

    counts = Counter(query_lemmas)
    vector = {}

    for lemma, count in counts.items():
        tf = count / total_terms
        vector[lemma] = tf * idf.get(lemma, 0.0)

    return vector


def cosine_similarity(vec1: dict[str, float], vec2: dict[str, float]) -> float:
    if not vec1 or not vec2:
        return 0.0

    common_keys = set(vec1.keys()) & set(vec2.keys())
    dot_product = sum(vec1[k] * vec2[k] for k in common_keys)

    norm1 = math.sqrt(sum(v * v for v in vec1.values()))
    norm2 = math.sqrt(sum(v * v for v in vec2.values()))

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    return dot_product / (norm1 * norm2)


def search(
    query: str,
    documents: dict[str, dict],
    doc_vectors: dict[str, dict[str, float]],
    idf: dict[str, float],
    top_k: int,
) -> list[tuple[str, float]]:
    query_lemmas = normalize_query(query)
    query_vector = build_query_vector(query_lemmas, idf)

    results = []
    for doc_id, doc_vector in doc_vectors.items():
        score = cosine_similarity(query_vector, doc_vector)
        if score > 0:
            results.append((doc_id, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


def print_results(results: list[tuple[str, float]], documents: dict[str, dict]) -> None:
    if not results:
        print("Ничего не найдено.")
        return

    print("Результаты поиска:")
    for rank, (doc_id, score) in enumerate(results, start=1):
        meta = documents[doc_id]
        print(
            f"{rank}. doc_id={doc_id} "
            f"filename={meta['filename']} "
            f"score={score:.6f} "
            f"url={meta['url']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Vector search over per-document lemma files.")
    parser.add_argument("--lemmas-dir", default="lemmas_by_doc", help="Directory with *_lemmas.txt")
    parser.add_argument("--mapping", default="index.txt", help="index.txt mapping file")
    parser.add_argument("--query", required=True, help="Search query string")
    parser.add_argument("--top-k", type=int, default=10, help="Number of top results")

    args = parser.parse_args()

    lemmas_dir = Path(args.lemmas_dir)
    mapping_path = Path(args.mapping)

    if not lemmas_dir.exists():
        raise FileNotFoundError(f"Lemmas directory not found: {lemmas_dir}")
    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_path}")

    documents = read_mapping(mapping_path)
    doc_lemmas = load_doc_lemmas(lemmas_dir, documents)
    idf = compute_idf(doc_lemmas)
    doc_vectors = compute_doc_vectors(doc_lemmas, idf)

    results = search(
        query=args.query,
        documents=documents,
        doc_vectors=doc_vectors,
        idf=idf,
        top_k=args.top_k,
    )

    print(f"Запрос: {args.query}")
    print()
    print_results(results, documents)


if __name__ == "__main__":
    main()