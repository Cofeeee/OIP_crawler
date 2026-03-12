import argparse
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
    raise ValueError(f"Unsupported language for stopwords: {lang}")


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_tokens(text: str, stop_words: set[str]) -> list[str]:
    """
    Оставляем только слова из букв:
    - без цифр
    - без смешанных букв+цифр
    - без html-мусора
    - без стоп-слов
    """
    raw_tokens = re.findall(r"\p{L}+", text.lower())

    cleaned = []
    for token in raw_tokens:
        if len(token) < 2:
            continue
        if token in stop_words:
            continue
        cleaned.append(token)

    return cleaned


def process_directory(input_dir: Path, lang: str) -> tuple[list[str], dict[str, list[str]]]:
    ensure_nltk_resources()
    stop_words = load_stopwords(lang)
    morph = MorphAnalyzer()

    unique_tokens = set()
    lemma_to_tokens = defaultdict(set)

    html_files = sorted(input_dir.glob("*.html"))

    for file_path in html_files:
        html = file_path.read_text(encoding="utf-8", errors="ignore")
        text = html_to_text(html)
        tokens = extract_tokens(text, stop_words)

        for token in tokens:
            unique_tokens.add(token)
            lemma = morph.parse(token)[0].normal_form
            lemma_to_tokens[lemma].add(token)

    sorted_tokens = sorted(unique_tokens)

    sorted_lemmas = {
        lemma: sorted(tokens)
        for lemma, tokens in sorted(lemma_to_tokens.items(), key=lambda x: x[0])
    }

    return sorted_tokens, sorted_lemmas


def save_tokens(tokens: list[str], output_path: Path) -> None:
    output_path.write_text("\n".join(tokens), encoding="utf-8")


def save_lemmas(lemma_to_tokens: dict[str, list[str]], output_path: Path) -> None:
    lines = []
    for lemma, tokens in lemma_to_tokens.items():
        line = " ".join([lemma] + tokens)
        lines.append(line)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tokenization and lemmatization for saved HTML pages."
    )
    parser.add_argument("--input", default="dump", help="Directory with downloaded HTML files")
    parser.add_argument("--tokens-out", default="tokens.txt", help="Output txt with unique tokens")
    parser.add_argument("--lemmas-out", default="lemmas.txt", help="Output txt with lemmas and tokens")
    parser.add_argument("--lang", default="ru", choices=["ru", "en"], help="Language of texts")

    args = parser.parse_args()

    input_dir = Path(args.input)
    tokens_out = Path(args.tokens_out)
    lemmas_out = Path(args.lemmas_out)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    tokens, lemma_to_tokens = process_directory(input_dir, args.lang)

    save_tokens(tokens, tokens_out)
    save_lemmas(lemma_to_tokens, lemmas_out)

    print(f"Saved {len(tokens)} unique tokens to {tokens_out}")
    print(f"Saved {len(lemma_to_tokens)} lemmas to {lemmas_out}")


if __name__ == "__main__":
    main()