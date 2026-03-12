import argparse
import math
from collections import Counter, defaultdict
from pathlib import Path

import nltk
import regex as re
from bs4 import BeautifulSoup
from pymorphy3 import MorphAnalyzer


CUSTOM_GARBAGE = {
    "nbsp", "html", "body", "div", "span", "href", "http", "https",
    "img", "src", "script", "style", "php", "wiki"
}


def ensure_nltk_resources() -> None:
    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords")


def load_stopwords(lang: str) -> set[str]:
    from nltk.corpus import stopwords

    if lang == "ru":
        return set(stopwords.words("russian"))
    if lang == "en":
        return set(stopwords.words("english"))
    raise ValueError(f"Unsupported language: {lang}")


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_tokens(text: str, stop_words: set[str]) -> list[str]:
    raw_tokens = re.findall(r"\p{L}+", text.lower())

    result = []
    for token in raw_tokens:
        if len(token) < 2:
            continue
        if token in stop_words:
            continue
        if token in CUSTOM_GARBAGE:
            continue
        result.append(token)

    return result


def read_mapping(index_txt_path: Path) -> dict[str, dict]:
    """
    Формат index.txt:
    <номер>\t<имя_файла>\t<url>
    """
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


def parse_documents(
    dump_dir: Path,
    mapping_path: Path,
    lang: str,
) -> tuple[dict[str, dict], dict[str, list[str]], dict[str, list[str]]]:
    ensure_nltk_resources()
    stop_words = load_stopwords(lang)
    morph = MorphAnalyzer()

    documents = read_mapping(mapping_path)
    doc_tokens: dict[str, list[str]] = {}
    doc_lemmas_from_tokens: dict[str, list[str]] = {}

    for doc_id, meta in documents.items():
        file_path = dump_dir / meta["filename"]
        if not file_path.exists():
            continue

        html = file_path.read_text(encoding="utf-8", errors="ignore")
        text = html_to_text(html)
        tokens = extract_tokens(text, stop_words)
        lemmas = [morph.parse(token)[0].normal_form for token in tokens]

        doc_tokens[doc_id] = tokens
        doc_lemmas_from_tokens[doc_id] = lemmas

    return documents, doc_tokens, doc_lemmas_from_tokens


def compute_idf_for_terms(doc_tokens: dict[str, list[str]]) -> dict[str, float]:
    doc_freq = Counter()
    num_docs = len(doc_tokens)

    for tokens in doc_tokens.values():
        unique_terms = set(tokens)
        for term in unique_terms:
            doc_freq[term] += 1

    idf = {}
    for term, df in doc_freq.items():
        idf[term] = math.log(num_docs / df) if df else 0.0

    return idf


def compute_idf_for_lemmas(doc_lemmas: dict[str, list[str]]) -> dict[str, float]:
    doc_freq = Counter()
    num_docs = len(doc_lemmas)

    for lemmas in doc_lemmas.values():
        unique_lemmas = set(lemmas)
        for lemma in unique_lemmas:
            doc_freq[lemma] += 1

    idf = {}
    for lemma, df in doc_freq.items():
        idf[lemma] = math.log(num_docs / df) if df else 0.0

    return idf


def compute_tf_for_terms(tokens: list[str]) -> dict[str, float]:
    total_terms = len(tokens)
    counts = Counter(tokens)

    if total_terms == 0:
        return {}

    tf = {}
    for term, count in counts.items():
        tf[term] = count / total_terms

    return tf


def compute_tf_for_lemmas(lemmas: list[str]) -> dict[str, float]:
    total_terms = len(lemmas)
    counts = Counter(lemmas)

    if total_terms == 0:
        return {}

    tf = {}
    for lemma, count in counts.items():
        tf[lemma] = count / total_terms

    return tf


def save_term_tfidf(
    output_dir: Path,
    documents: dict[str, dict],
    doc_tokens: dict[str, list[str]],
    idf_terms: dict[str, float],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for doc_id, tokens in doc_tokens.items():
        tf_terms = compute_tf_for_terms(tokens)
        filename = documents[doc_id]["filename"]
        out_name = Path(filename).stem + "_terms.txt"
        out_path = output_dir / out_name

        lines = []
        for term in sorted(tf_terms.keys()):
            idf = idf_terms.get(term, 0.0)
            tfidf = tf_terms[term] * idf
            lines.append(f"{term} {idf:.6f} {tfidf:.6f}")

        out_path.write_text("\n".join(lines), encoding="utf-8")


def save_lemma_tfidf(
    output_dir: Path,
    documents: dict[str, dict],
    doc_lemmas: dict[str, list[str]],
    idf_lemmas: dict[str, float],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for doc_id, lemmas in doc_lemmas.items():
        tf_lemmas = compute_tf_for_lemmas(lemmas)
        filename = documents[doc_id]["filename"]
        out_name = Path(filename).stem + "_lemmas.txt"
        out_path = output_dir / out_name

        lines = []
        for lemma in sorted(tf_lemmas.keys()):
            idf = idf_lemmas.get(lemma, 0.0)
            tfidf = tf_lemmas[lemma] * idf
            lines.append(f"{lemma} {idf:.6f} {tfidf:.6f}")

        out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute TF-IDF for terms and lemmas for each downloaded HTML document."
    )
    parser.add_argument("--dump", default="dump", help="Directory with HTML files")
    parser.add_argument("--mapping", default="index.txt", help="index.txt mapping file")
    parser.add_argument("--lang", default="ru", choices=["ru", "en"], help="Language")
    parser.add_argument("--terms-out", default="tfidf_terms", help="Output dir for term tf-idf files")
    parser.add_argument("--lemmas-out", default="tfidf_lemmas", help="Output dir for lemma tf-idf files")

    args = parser.parse_args()

    dump_dir = Path(args.dump)
    mapping_path = Path(args.mapping)
    terms_out_dir = Path(args.terms_out)
    lemmas_out_dir = Path(args.lemmas_out)

    if not dump_dir.exists():
        raise FileNotFoundError(f"Dump directory not found: {dump_dir}")
    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_path}")

    documents, doc_tokens, doc_lemmas = parse_documents(
        dump_dir=dump_dir,
        mapping_path=mapping_path,
        lang=args.lang,
    )

    idf_terms = compute_idf_for_terms(doc_tokens)
    idf_lemmas = compute_idf_for_lemmas(doc_lemmas)

    save_term_tfidf(
        output_dir=terms_out_dir,
        documents=documents,
        doc_tokens=doc_tokens,
        idf_terms=idf_terms,
    )

    save_lemma_tfidf(
        output_dir=lemmas_out_dir,
        documents=documents,
        doc_lemmas=doc_lemmas,
        idf_lemmas=idf_lemmas,
    )

    print(f"Processed documents: {len(doc_tokens)}")
    print(f"Term output directory: {terms_out_dir}")
    print(f"Lemma output directory: {lemmas_out_dir}")
    print(f"Unique terms with IDF: {len(idf_terms)}")
    print(f"Unique lemmas with IDF: {len(idf_lemmas)}")


if __name__ == "__main__":
    main()