#!/usr/bin/env python3
"""CLI to permanently redact PII (email, phone) from PDFs, scoped by page region."""

import argparse
import re
import sys
from pathlib import Path

import pymupdf as fitz

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")

# (pattern, label, canonical box width in points) — fixed width hides the true
# match length so a redacted box can't be sized-up to guess the original text.
PII_TYPES = (
    (EMAIL_RE, "EMAIL", 90),
    (PHONE_RE, "PHONE", 70),
)

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


def build_box(match_rect: fitz.Rect, box_width: str, target_width: float) -> fitz.Rect:
    if box_width == "tight":
        return match_rect
    width = max(match_rect.width, target_width)
    return fitz.Rect(match_rect.x0, match_rect.y0, match_rect.x0 + width, match_rect.y1)


def redact_pdf(doc: fitz.Document, location: str, box_width: str = "fixed", label: bool = True) -> int:
    """Add + apply redactions for PII spans matching location. Returns count redacted."""
    count = 0
    for page in doc:
        height = page.rect.height
        page_annots = 0
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
            for pattern, pii_label, fixed_width in PII_TYPES:
                for match in pattern.finditer(text):
                    hits = page.search_for(match.group(), clip=fitz.Rect(x0, y0, x1, y1))
                    for match_rect in hits:
                        rect = build_box(match_rect, box_width, fixed_width)
                        page.add_redact_annot(
                            rect,
                            text=f"[{pii_label}]" if label else None,
                            fill=(0, 0, 0),
                            text_color=(1, 1, 1),
                        )
                        page_annots += 1
        if page_annots:
            page.apply_redactions()
            count += page_annots
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


def process_file(
    path: Path,
    location: str,
    inplace: bool,
    box_width: str = "fixed",
    label: bool = True,
    scrub: bool = True,
) -> tuple[Path, int]:
    doc = fitz.open(path)
    count = redact_pdf(doc, location, box_width=box_width, label=label)
    if scrub:
        doc.scrub()
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
    parser.add_argument(
        "--box-width",
        choices=["fixed", "tight"],
        default="fixed",
        help="'fixed' (default) draws a canonical box width per PII type so the box "
        "size can't be used to guess the original text length; 'tight' hugs the exact match",
    )
    parser.add_argument(
        "--label",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="draw a '[EMAIL]'/'[PHONE]' text label inside the redaction box (default: on)",
    )
    parser.add_argument(
        "--scrub",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="also strip document metadata, embedded files, JS, thumbnails (default: on)",
    )
    args = parser.parse_args()

    try:
        pdfs = find_pdfs(args.path)
    except ValueError as exc:
        sys.exit(f"error: {exc}")

    for pdf in pdfs:
        out_path, count = process_file(
            pdf, args.location, args.inplace,
            box_width=args.box_width, label=args.label, scrub=args.scrub,
        )
        print(f"{pdf.name}: redacted {count} match(es) -> {out_path}")


if __name__ == "__main__":
    main()
