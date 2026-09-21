#!/usr/bin/env python3
"""Self-check: builds a synthetic PDF with PII in each region, asserts redact_pdf
removes only the targeted region's PII and leaves the rest intact."""

import pymupdf as fitz

from redact import redact_pdf

HEADER_EMAIL = "header@example.com"
BODY_PHONE = "555-123-4567"
FOOTER_EMAIL = "footer@example.com"


def build_doc() -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # letter size
    page.insert_text((50, 30), f"Contact: {HEADER_EMAIL}")   # top ~4% -> header
    page.insert_text((50, 400), f"Call {BODY_PHONE} now")    # ~50% -> body
    page.insert_text((50, 780), f"Reach {FOOTER_EMAIL}")     # bottom ~98% -> footer
    return doc


def test_header_only():
    doc = build_doc()
    count = redact_pdf(doc, "header")
    text = doc[0].get_text()
    assert count == 1, f"expected 1 redaction, got {count}"
    assert HEADER_EMAIL not in text
    assert BODY_PHONE in text
    assert FOOTER_EMAIL in text


def test_body_only():
    doc = build_doc()
    count = redact_pdf(doc, "body")
    text = doc[0].get_text()
    assert count == 1, f"expected 1 redaction, got {count}"
    assert BODY_PHONE not in text
    assert HEADER_EMAIL in text
    assert FOOTER_EMAIL in text


def test_footer_only():
    doc = build_doc()
    count = redact_pdf(doc, "footer")
    text = doc[0].get_text()
    assert count == 1, f"expected 1 redaction, got {count}"
    assert FOOTER_EMAIL not in text
    assert HEADER_EMAIL in text
    assert BODY_PHONE in text


def test_all():
    doc = build_doc()
    count = redact_pdf(doc, "all")
    text = doc[0].get_text()
    assert count == 3, f"expected 3 redactions, got {count}"
    assert HEADER_EMAIL not in text
    assert BODY_PHONE not in text
    assert FOOTER_EMAIL not in text


if __name__ == "__main__":
    for fn in (test_header_only, test_body_only, test_footer_only, test_all):
        fn()
        print(f"PASS: {fn.__name__}")
    print("all tests passed")
