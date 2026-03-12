import argparse
import json
from collections import defaultdict
from pathlib import Path

import nltk
import regex as re
from bs4 import BeautifulSoup
from pymorphy3 import MorphAnalyzer


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


CUSTOM_GARBAGE = {
    "nbsp", "html", "body", "div", "span", "href", "http", "https",
    "img", "src", "script", "style", "php", "wiki"
}


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


def read_index_mapping(index_txt_path: Path) -> dict[str, dict]:
    """
    Читает index.txt формата:
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


def build_inverted_index(
    dump_dir: Path,
    index_txt_path: Path,
    lang: str,
) -> dict:
    ensure_nltk_resources()
    stop_words = load_stopwords(lang)
    morph = MorphAnalyzer()

    documents = read_index_mapping(index_txt_path)
    inverted_index = defaultdict(set)

    for doc_id, meta in documents.items():
        file_path = dump_dir / meta["filename"]
        if not file_path.exists():
            continue

        html = file_path.read_text(encoding="utf-8", errors="ignore")
        text = html_to_text(html)
        tokens = extract_tokens(text, stop_words)

        lemmas_in_doc = set()
        for token in tokens:
            lemma = morph.parse(token)[0].normal_form
            lemmas_in_doc.add(lemma)

        for lemma in lemmas_in_doc:
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
        line = f"{lemma} " + " ".join(doc_ids)
        lines.append(line)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build inverted index from saved HTML pages.")
    parser.add_argument("--dump", default="dump", help="Directory with HTML files")
    parser.add_argument("--mapping", default="index.txt", help="index.txt with file mapping")
    parser.add_argument("--lang", default="ru", choices=["ru", "en"], help="Document language")
    parser.add_argument("--json-out", default="inverted_index.json", help="JSON index output")
    parser.add_argument("--txt-out", default="inverted_index.txt", help="TXT index output")

    args = parser.parse_args()

    dump_dir = Path(args.dump)
    mapping_path = Path(args.mapping)
    json_out = Path(args.json_out)
    txt_out = Path(args.txt_out)

    if not dump_dir.exists():
        raise FileNotFoundError(f"Dump directory not found: {dump_dir}")
    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_path}")

    index_data = build_inverted_index(
        dump_dir=dump_dir,
        index_txt_path=mapping_path,
        lang=args.lang,
    )

    save_json_index(index_data, json_out)
    save_txt_index(index_data, txt_out)

    print(f"Saved JSON index to: {json_out}")
    print(f"Saved TXT index to: {txt_out}")
    print(f"Indexed terms: {len(index_data['index'])}")
    print(f"Documents: {len(index_data['documents'])}")


if __name__ == "__main__":
    main()