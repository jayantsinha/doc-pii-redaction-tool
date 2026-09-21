#!/usr/bin/env python3
"""CLI to permanently redact PII (email, phone) from PDFs, scoped by page region."""

import argparse
import re
import sys
from pathlib import Path

import pymupdf as fitz

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
PII_PATTERNS = (EMAIL_RE, PHONE_RE)

HEADER_FRACTION = 0.10
FOOTER_FRACTION = 0.90


def classify_region(y0: float, y1: float, page_height: float) -> str:
    if y1 <= HEADER_FRACTION * page_height:
        return "header"
    if y0 >= FOOTER_FRACTION * page_height:
        return "footer"
    return "body"


def region_matches(span_region: str, location: str) -> bool:
    return location == "all" or span_region == location


def redact_pdf(doc: fitz.Document, location: str) -> int:
    """Add + apply redactions for PII spans matching location. Returns count redacted."""
    count = 0
    for page in doc:
        height = page.rect.height
        spans = [
            span
            for block in page.get_text("dict")["blocks"]
            if "lines" in block
            for line in block["lines"]
            for span in line["spans"]
        ]
        for span in spans:
            x0, y0, x1, y1 = span["bbox"]
            region = classify_region(y0, y1, height)
            if not region_matches(region, location):
                continue
            text = span["text"]
            for pattern in PII_PATTERNS:
                for match in pattern.finditer(text):
                    hits = page.search_for(match.group(), clip=fitz.Rect(x0, y0, x1, y1))
                    for rect in hits:
                        page.add_redact_annot(rect, fill=(0, 0, 0))
                        count += 1
        if count:
            page.apply_redactions()
    return count


def find_pdfs(path: Path) -> list[Path]:
    if path.is_file():
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"{path} is not a PDF")
        return [path]
    if path.is_dir():
        pdfs = sorted(path.glob("*.pdf"))
        if not pdfs:
            raise ValueError(f"no PDFs found in {path}")
        return pdfs
    raise ValueError(f"{path} does not exist")


def process_file(path: Path, location: str, inplace: bool) -> tuple[Path, int]:
    doc = fitz.open(path)
    count = redact_pdf(doc, location)
    out_path = path if inplace else path.with_name(f"{path.stem}_redacted.pdf")
    if inplace:
        tmp = path.with_suffix(".tmp.pdf")
        doc.save(tmp)
        doc.close()
        tmp.replace(path)
    else:
        doc.save(out_path)
        doc.close()
    return out_path, count


def main() -> None:
    parser = argparse.ArgumentParser(description="Redact PII from PDF files.")
    parser.add_argument("location", choices=["header", "footer", "body", "all"])
    parser.add_argument("path", type=Path)
    parser.add_argument("--inplace", action="store_true", help="overwrite original file")
    args = parser.parse_args()

    try:
        pdfs = find_pdfs(args.path)
    except ValueError as exc:
        sys.exit(f"error: {exc}")

    for pdf in pdfs:
        out_path, count = process_file(pdf, args.location, args.inplace)
        print(f"{pdf.name}: redacted {count} match(es) -> {out_path}")


if __name__ == "__main__":
    main()
