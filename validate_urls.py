from __future__ import annotations

import argparse
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from langdetect import DetectorFactory, detect

DetectorFactory.seed = 0

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)


def read_urls(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)


def detect_lang_safe(text: str) -> str | None:
    try:
        if len(text) < 60:
            return None
        return detect(text)
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Check URL list before crawling")
    parser.add_argument("--urls", default="urls.txt")
    parser.add_argument("--lang", default="ru")
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    urls = read_urls(Path(args.urls))
    ok = 0
    for i, url in enumerate(urls, start=1):
        try:
            response = session.get(url, timeout=args.timeout)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type.lower():
                print(f"[{i}] SKIP non-html: {url}")
                continue
            response.encoding = response.apparent_encoding or response.encoding
            text = visible_text(response.text)
            lang = detect_lang_safe(text)
            if args.lang and lang and lang != args.lang:
                print(f"[{i}] SKIP lang={lang}: {url}")
                continue
            print(f"[{i}] OK lang={lang or 'unknown'} len={len(text)} {url}")
            ok += 1
        except Exception as exc:
            print(f"[{i}] ERROR {url} -> {exc}")

    print(f"\nSuitable URLs: {ok} / {len(urls)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
