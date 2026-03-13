import argparse
from pathlib import Path

import nltk
import regex as re
from bs4 import BeautifulSoup
from pymorphy3 import MorphAnalyzer


CUSTOM_GARBAGE = {
    "nbsp", "html", "body", "div", "span", "href", "http", "https",
    "img", "src", "script", "style", "php", "wiki", "org", "www",
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


def is_russian_word(token: str) -> bool:
    return bool(re.fullmatch(r"[а-яё]+", token, flags=re.IGNORECASE))


def is_english_word(token: str) -> bool:
    return bool(re.fullmatch(r"[a-z]+", token, flags=re.IGNORECASE))


def is_valid_token(token: str, stop_words_ru: set[str], stop_words_en: set[str]) -> bool:
    if len(token) < 2:
        return False

    if token in CUSTOM_GARBAGE:
        return False

    if is_russian_word(token):
        if token in stop_words_ru:
            return False
        return True

    if is_english_word(token):
        if token in stop_words_en:
            return False
        return True

    return False


def extract_tokens(text: str, stop_words_ru: set[str], stop_words_en: set[str]) -> list[str]:
    raw_tokens = re.findall(r"\p{L}+", text.lower())

    result = []
    for token in raw_tokens:
        if is_valid_token(token, stop_words_ru, stop_words_en):
            result.append(token)

    return result


def lemmatize_token(token: str, morph: MorphAnalyzer) -> str:
    if is_russian_word(token):
        return morph.parse(token)[0].normal_form
    return token


def save_list(values: list[str], output_path: Path) -> None:
    output_path.write_text("\n".join(values), encoding="utf-8")


def process_directory(
    input_dir: Path,
    tokens_out_dir: Path,
    lemmas_out_dir: Path,
) -> None:
    ensure_nltk_resources()

    stop_words_ru = load_stopwords("ru")
    stop_words_en = load_stopwords("en")
    morph = MorphAnalyzer()

    tokens_out_dir.mkdir(parents=True, exist_ok=True)
    lemmas_out_dir.mkdir(parents=True, exist_ok=True)

    html_files = sorted(input_dir.glob("*.html"))

    if not html_files:
        raise FileNotFoundError(f"No HTML files found in {input_dir}")

    for file_path in html_files:
        html = file_path.read_text(encoding="utf-8", errors="ignore")
        text = html_to_text(html)

        tokens = extract_tokens(text, stop_words_ru, stop_words_en)
        unique_tokens = sorted(set(tokens))

        lemmas = [lemmatize_token(token, morph) for token in unique_tokens]
        unique_lemmas = sorted(set(lemmas))

        stem = file_path.stem
        tokens_path = tokens_out_dir / f"{stem}_tokens.txt"
        lemmas_path = lemmas_out_dir / f"{stem}_lemmas.txt"

        save_list(unique_tokens, tokens_path)
        save_list(unique_lemmas, lemmas_path)

        print(f"Processed: {file_path.name}")
        print(f"  tokens -> {tokens_path}")
        print(f"  lemmas -> {lemmas_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create per-document token and lemma files from downloaded HTML pages."
    )
    parser.add_argument("--input", default="dump", help="Directory with downloaded HTML files")
    parser.add_argument("--tokens-out-dir", default="tokens_by_doc", help="Output directory for token files")
    parser.add_argument("--lemmas-out-dir", default="lemmas_by_doc", help="Output directory for lemma files")

    args = parser.parse_args()

    input_dir = Path(args.input)
    tokens_out_dir = Path(args.tokens_out_dir)
    lemmas_out_dir = Path(args.lemmas_out_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    process_directory(
        input_dir=input_dir,
        tokens_out_dir=tokens_out_dir,
        lemmas_out_dir=lemmas_out_dir,
    )


if __name__ == "__main__":
    main()