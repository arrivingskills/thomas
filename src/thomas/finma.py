from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Optional


RSS_URL = "https://www.finma.ch/en/rss/news/"


@dataclass
class RssItem:
    title: Optional[str]
    link: Optional[str]
    pubDate: Optional[str]
    description: Optional[str]


def fetch_rss(url: str = RSS_URL, timeout: float = 20.0) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read()


def parse_rss(xml_bytes: bytes) -> List[RssItem]:
    root = ET.fromstring(xml_bytes)

    # RSS can be in formats rss/channel/item or feed/entry
    items: List[RssItem] = []

    # Try RSS 2.0 structure
    channel = root.find("channel")
    if channel is not None:
        for item in channel.findall("item"):
            items.append(
                RssItem(
                    title=_text(item.find("title")),
                    link=_text(item.find("link")),
                    pubDate=_text(item.find("pubDate")) or _text(item.find("dc:date")),
                    description=_text(item.find("description")),
                )
            )
        return items

    # Try Atom as a fallback
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "dc": "http://purl.org/dc/elements/1.1/",
    }
    for entry in root.findall("atom:entry", ns):
        link_el = entry.find("atom:link", ns)
        link = link_el.get("href") if link_el is not None else None
        items.append(
            RssItem(
                title=_text(entry.find("atom:title", ns)),
                link=link,
                pubDate=_text(entry.find("atom:updated", ns)) or _text(entry.find("atom:published", ns)),
                description=_text(entry.find("atom:summary", ns)) or _text(entry.find("atom:content", ns)),
            )
        )
    return items


def _text(el: Optional[ET.Element]) -> Optional[str]:
    if el is None:
        return None
    txt = el.text or ""
    return txt.strip() or None


def write_ndjson(items: Iterable[RssItem], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(asdict(it), ensure_ascii=False))
            f.write("\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Download FINMA RSS and write newline-delimited JSON file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("../../data/finma.txt"),
        help="Output file path (default: data/finma.txt)",
    )
    parser.add_argument("--url", default=RSS_URL, help="RSS URL to fetch (default: FINMA news RSS)")
    args = parser.parse_args(argv)

    try:
        xml_bytes = fetch_rss(args.url)
        items = parse_rss(xml_bytes)
        write_ndjson(items, args.output)
        print(f"Wrote {len(items)} items to {args.output}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
