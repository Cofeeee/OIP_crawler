import argparse
import json
from pathlib import Path

from pymorphy3 import MorphAnalyzer


OPERATORS = {"AND", "OR", "NOT", "(", ")"}


def load_index(index_path: Path) -> dict:
    return json.loads(index_path.read_text(encoding="utf-8"))


def tokenize_query(query: str) -> list[str]:
    spaced = (
        query.replace("(", " ( ")
             .replace(")", " ) ")
    )
    parts = spaced.split()
    return parts


def normalize_query_tokens(tokens: list[str], morph: MorphAnalyzer) -> list[str]:
    result = []

    for token in tokens:
        upper = token.upper()
        if upper in OPERATORS:
            result.append(upper)
        else:
            lemma = morph.parse(token.lower())[0].normal_form
            result.append(lemma)

    return result


def to_postfix(tokens: list[str]) -> list[str]:
    precedence = {
        "NOT": 3,
        "AND": 2,
        "OR": 1,
    }

    output = []
    stack = []

    for token in tokens:
        if token not in OPERATORS:
            output.append(token)
        elif token == "(":
            stack.append(token)
        elif token == ")":
            while stack and stack[-1] != "(":
                output.append(stack.pop())
            if not stack:
                raise ValueError("Mismatched parentheses")
            stack.pop()
        else:
            while (
                stack
                and stack[-1] != "("
                and precedence.get(stack[-1], 0) >= precedence[token]
            ):
                output.append(stack.pop())
            stack.append(token)

    while stack:
        if stack[-1] in {"(", ")"}:
            raise ValueError("Mismatched parentheses")
        output.append(stack.pop())

    return output


def evaluate_postfix(postfix: list[str], index_data: dict) -> set[str]:
    all_docs = set(index_data["documents"].keys())
    inverted_index = index_data["index"]

    stack = []

    for token in postfix:
        if token not in {"AND", "OR", "NOT"}:
            docs = set(inverted_index.get(token, []))
            stack.append(docs)
        elif token == "NOT":
            if not stack:
                raise ValueError("Invalid query: NOT without operand")
            operand = stack.pop()
            stack.append(all_docs - operand)
        elif token in {"AND", "OR"}:
            if len(stack) < 2:
                raise ValueError(f"Invalid query: {token} without two operands")
            right = stack.pop()
            left = stack.pop()

            if token == "AND":
                stack.append(left & right)
            else:
                stack.append(left | right)

    if len(stack) != 1:
        raise ValueError("Invalid query")

    return stack[0]


def format_results(result_doc_ids: set[str], index_data: dict) -> str:
    if not result_doc_ids:
        return "Ничего не найдено."

    lines = ["Найденные документы:"]
    for doc_id in sorted(result_doc_ids, key=lambda x: int(x)):
        meta = index_data["documents"][doc_id]
        lines.append(f"{doc_id}\t{meta['filename']}\t{meta['url']}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Boolean search over inverted index.")
    parser.add_argument("--index", default="inverted_index.json", help="Path to JSON inverted index")
    parser.add_argument("--query", required=True, help="Boolean query string")
    args = parser.parse_args()

    index_path = Path(args.index)
    if not index_path.exists():
        raise FileNotFoundError(f"Index file not found: {index_path}")

    index_data = load_index(index_path)
    morph = MorphAnalyzer()

    query_tokens = tokenize_query(args.query)
    normalized_tokens = normalize_query_tokens(query_tokens, morph)
    postfix = to_postfix(normalized_tokens)
    result_doc_ids = evaluate_postfix(postfix, index_data)

    print("Исходный запрос:", args.query)
    print("Нормализованный запрос:", " ".join(normalized_tokens))
    print()
    print(format_results(result_doc_ids, index_data))


if __name__ == "__main__":
    main()