from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from langdetect import DetectorFactory, detect
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DetectorFactory.seed = 0

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)


def build_session(timeout: int) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    session.request_timeout = timeout  # type: ignore[attr-defined]
    return session


def read_urls(path: Path) -> list[str]:
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def is_html_response(response: requests.Response) -> bool:
    content_type = response.headers.get("Content-Type", "").lower()
    return "text/html" in content_type or "application/xhtml+xml" in content_type


def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_lang_safe(text: str) -> str | None:
    try:
        if len(text) < 60:
            return None
        return detect(text)
    except Exception:
        return None


def safe_filename(index: int, url: str) -> str:
    domain = urlparse(url).netloc.replace(":", "_") or "page"
    digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    return f"{index:03d}_{domain}_{digest}.html"


def fetch_html(session: requests.Session, url: str) -> tuple[str | None, str | None]:
    timeout = getattr(session, "request_timeout", 15)
    try:
        response = session.get(url, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        if not is_html_response(response):
            return None, f"SKIP not html: {url}"
        response.encoding = response.apparent_encoding or response.encoding
        return response.text, None
    except requests.RequestException as exc:
        return None, f"ERROR {url}: {exc}"


def crawl(
    urls: Iterable[str],
    output_dir: Path,
    index_path: Path,
    expected_lang: str,
    min_text_chars: int,
    delay: float,
    timeout: int,
    limit: int,
) -> None:
    session = build_session(timeout=timeout)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved = 0
    seen_hashes: set[str] = set()
    lines: list[str] = []

    for url in urls:
        if saved >= limit:
            break

        html, error = fetch_html(session, url)
        if error:
            print(error)
            continue
        if html is None:
            continue

        page_hash = hashlib.md5(html.encode("utf-8", errors="ignore")).hexdigest()
        if page_hash in seen_hashes:
            print(f"SKIP duplicate content: {url}")
            continue

        visible_text = extract_visible_text(html)
        if len(visible_text) < min_text_chars:
            print(f"SKIP too short text ({len(visible_text)}): {url}")
            continue

        detected_lang = detect_lang_safe(visible_text)
        if expected_lang and detected_lang and detected_lang != expected_lang:
            print(f"SKIP wrong language ({detected_lang}): {url}")
            continue

        file_number = saved + 1
        filename = safe_filename(file_number, url)
        file_path = output_dir / filename
        file_path.write_text(html, encoding="utf-8", errors="ignore")

        lines.append(f"{file_number}\t{filename}\t{url}")
        seen_hashes.add(page_hash)
        saved += 1
        print(f"OK {file_number:03d}: {url} -> {filename}")

        if delay > 0:
            time.sleep(delay)

    index_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(f"\nSaved pages: {saved}")
    print(f"Index file: {index_path}")
    print(f"Pages folder: {output_dir}")

    if saved < limit:
        print(
            f"WARNING: requested {limit} pages, but only saved {saved}. "
            "Add more URLs to the source list or reduce filters."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download HTML pages from a prepared URL list and create index.txt"
    )
    parser.add_argument("--urls", default="urls.txt", help="Path to the file with URLs")
    parser.add_argument("--out", default="dump", help="Directory for saved HTML files")
    parser.add_argument("--index", default="index.txt", help="Output index file")
    parser.add_argument(
        "--lang",
        default="ru",
        help="Expected language code for visible text: ru, en, etc. Empty string disables check",
    )
    parser.add_argument(
        "--min-text-chars",
        type=int,
        default=800,
        help="Minimum number of visible text characters on a page",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests in seconds",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="HTTP timeout in seconds",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="How many pages to save",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    urls_path = Path(args.urls)
    if not urls_path.exists():
        print(f"URL file not found: {urls_path}")
        return 1

    urls = read_urls(urls_path)
    if not urls:
        print("URL file is empty")
        return 1

    crawl(
        urls=urls,
        output_dir=Path(args.out),
        index_path=Path(args.index),
        expected_lang=args.lang,
        min_text_chars=args.min_text_chars,
        delay=args.delay,
        timeout=args.timeout,
        limit=args.limit,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
