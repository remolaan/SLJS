#!/usr/bin/env python3
"""Collect a Sri Lankan legal corpus for RAG.

Fetches primary statutes, the Constitution, and the Code of Criminal Procedure
Act from official/authoritative English sources (via the VPS SOCKS proxy), saves
the raw files under corpus/raw/, and extracts clean text under corpus/raw/<act>.txt.

Usage:
  python corpus/collect.py                 # run all known sources
  python corpus/collect.py --only cpc      # run only the CPC Act

Provenance is recorded in corpus/docs/PROVENANCE.md (license + source URL).
"""
from __future__ import annotations

import argparse
import os
import re
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
os.makedirs(RAW, exist_ok=True)

PROXY = os.environ.get(
    "CRAWLER_PROXY",
    "socks5h://sinhala:qlU9VQNOALG7ulGBt1hj7Y0sSOb4tFcZ@104.37.188.153:1080",
)
PROXIES = {"http": PROXY, "https": PROXY}
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) SL-legal-corpus research crawler"}


def fetch(url: str, timeout: int = 40) -> bytes:
    r = requests.get(url, proxies=PROXIES, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.content


def html_to_text(html: bytes) -> str:
    """Strip HTML tags from a law page, preserving section structure."""
    text = html.decode("utf-8", errors="ignore")
    # keep section markers roughly
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|tr|h[1-6]|li)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def pdf_to_text(data: bytes) -> str:
    from pypdf import PdfReader
    import io

    reader = PdfReader(io.BytesIO(data))
    parts = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(parts).strip()


def save(name: str, raw: bytes, text: str, source: str) -> None:
    raw_path = os.path.join(RAW, f"{name}.bin")
    txt_path = os.path.join(RAW, f"{name}.txt")
    with open(raw_path, "wb") as f:
        f.write(raw)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[OK] {name}: {len(text)} chars from {source}")


def collect_cpc() -> None:
    url = (
        "https://lankalaw.net/wp-content/uploads/2025/02/1956Y1V20C.html"
    )
    print("Fetching Code of Criminal Procedure Act ...")
    html = fetch(url)
    text = html_to_text(html)
    save("cpc_act", html, text, url)


def collect_penal_code() -> None:
    url = "https://lankalaw.net/wp-content/uploads/2025/03/Penal-Code-Consolidated2024.pdf"
    print("Fetching Penal Code (Consolidated) 2024 ...")
    data = fetch(url, timeout=90)
    text = pdf_to_text(data)
    save("penal_code", data, text, url)


def collect_evidence_ordinance() -> None:
    url = "https://lankalaw.net/wp-content/uploads/2025/03/Evidence-Ordinance-Consolidated-2024.pdf"
    print("Fetching Evidence Ordinance (Consolidated) 2024 ...")
    data = fetch(url, timeout=90)
    text = pdf_to_text(data)
    save("evidence_ordinance", data, text, url)


def collect_constitution() -> None:
    # Official Parliament Constitution PDF (public-domain official text).
    candidates = [
        "https://www.parliament.lk/uploads/constitution/constitution.pdf",
        "https://www.parliament.lk/uploads/acts/gbills/english/constitution.pdf",
    ]
    for url in candidates:
        try:
            print(f"Fetching Constitution ({url}) ...")
            data = fetch(url)
            text = pdf_to_text(data)
            save("constitution", data, text, url)
            return
        except Exception as e:  # noqa: BLE001
            print(f"  miss {url}: {str(e)[:60]}")
    print("Could not fetch constitution from known URLs")


SOURCES = {
    "cpc": collect_cpc,
    "penal_code": collect_penal_code,
    "evidence_ordinance": collect_evidence_ordinance,
    "constitution": collect_constitution,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(SOURCES) + ["all"], default="all")
    args = ap.parse_args()
    targets = list(SOURCES) if args.only == "all" else [args.only]
    for t in targets:
        SOURCES[t]()


if __name__ == "__main__":
    main()