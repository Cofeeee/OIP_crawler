import argparse
import time
from collections import deque
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from langdetect import detect, DetectorFactory
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DetectorFactory.seed = 0


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def create_session() -> requests.Session:
    session = requests.Session()

    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})

    return session


def is_html_response(response: requests.Response) -> bool:
    content_type = response.headers.get("Content-Type", "").lower()
    return "text/html" in content_type


def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    return " ".join(text.split())


def detect_language(text: str) -> str | None:
    try:
        if len(text) < 50:
            return None
        return detect(text)
    except Exception:
        return None


def normalize_url(base_url: str, href: str) -> str | None:
    if not href:
        return None

    absolute = urljoin(base_url, href)
    absolute, _ = urldefrag(absolute)

    parsed = urlparse(absolute)

    if parsed.scheme not in {"http", "https"}:
        return None

    return absolute


def is_same_allowed_domain(url: str, allowed_domains: set[str]) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == domain or host.endswith("." + domain) for domain in allowed_domains)


def extract_links(html: str, base_url: str, allowed_domains: set[str]) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    result = []

    for a in soup.find_all("a", href=True):
        normalized = normalize_url(base_url, a["href"])
        if not normalized:
            continue

        if allowed_domains and not is_same_allowed_domain(normalized, allowed_domains):
            continue

        result.append(normalized)

    return result


def save_page(output_dir: Path, file_number: int, html: str) -> str:
    filename = f"{file_number:04d}.html"
    file_path = output_dir / filename
    file_path.write_text(html, encoding="utf-8", errors="ignore")
    return filename


def crawl_by_depth(
    seeds: list[str],
    output_dir: Path,
    index_path: Path,
    limit: int,
    max_depth: int,
    lang: str,
    allowed_domains: set[str],
    timeout: int,
    delay: float,
) -> None:
    session = create_session()
    output_dir.mkdir(parents=True, exist_ok=True)

    visited: set[str] = set()
    saved_count = 0
    index_lines: list[str] = []

    queue = deque((url, 0) for url in seeds)

    while queue and saved_count < limit:
        url, depth = queue.popleft()

        if url in visited:
            continue

        visited.add(url)

        try:
            response = session.get(url, timeout=timeout)
        except requests.RequestException:
            continue

        if response.status_code != 200:
            continue

        if not is_html_response(response):
            continue

        html = response.text
        text = extract_visible_text(html)

        if len(text) < 200:
            continue

        detected = detect_language(text)
        if lang and detected != lang:
            continue

        saved_count += 1
        filename = save_page(output_dir, saved_count, html)
        index_lines.append(f"{saved_count}\t{filename}\t{url}")

        print(f"[{saved_count}/{limit}] saved: {url}")

        if depth < max_depth:
            child_links = extract_links(html, url, allowed_domains)
            for child_url in child_links:
                if child_url not in visited:
                    queue.append((child_url, depth + 1))

        if delay > 0:
            time.sleep(delay)

    index_path.write_text("\n".join(index_lines), encoding="utf-8")
    print(f"Done. Saved {saved_count} pages.")
    print(f"Index file: {index_path}")
    print(f"Output dir: {output_dir}")


def read_lines(path: Path) -> list[str]:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Depth crawler for saving HTML pages with markup."
    )
    parser.add_argument("--seeds", required=True, help="Path to file with seed URLs")
    parser.add_argument("--out", default="dump_depth", help="Output directory")
    parser.add_argument("--index", default="index_depth.txt", help="Index file path")
    parser.add_argument("--limit", type=int, default=100, help="Maximum saved pages")
    parser.add_argument("--max-depth", type=int, default=2, help="Crawl depth")
    parser.add_argument("--lang", default="ru", help="Required language, e.g. ru")
    parser.add_argument(
        "--allowed-domains",
        nargs="*",
        default=[],
        help="Allowed domains, e.g. ru.wikipedia.org",
    )
    parser.add_argument("--timeout", type=int, default=15, help="Request timeout")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests")

    args = parser.parse_args()

    seeds_path = Path(args.seeds)
    output_dir = Path(args.out)
    index_path = Path(args.index)

    seeds = read_lines(seeds_path)
    allowed_domains = {domain.lower() for domain in args.allowed_domains}

    crawl_by_depth(
        seeds=seeds,
        output_dir=output_dir,
        index_path=index_path,
        limit=args.limit,
        max_depth=args.max_depth,
        lang=args.lang,
        allowed_domains=allowed_domains,
        timeout=args.timeout,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()