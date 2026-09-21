# PII Redaction Tool

CLI that permanently redacts PII (email addresses, phone numbers) from PDF files, scoped to a page region.

Uses [PyMuPDF](https://pymupdf.readthedocs.io/) redaction annotations — matched text is removed from the PDF content stream (not just visually covered), boxed over, and the document is metadata-scrubbed.

## Install

```
pip install -r requirements.txt
```

## Usage

```
python3 redact.py <location> <path> [options]
```

- `location` — one of `header`, `footer`, `body`, `all`
  - A text span counts as **header** if it sits fully within the top 10% of the page height, **footer** if fully within the bottom 10%, otherwise **body**.
  - `all` redacts every region.
- `path` — a single `.pdf` file, or a directory (all top-level `*.pdf` files in it are processed, non-recursive)

### Options

- `--inplace` — overwrite the original file. Without this flag, output is written next to the original as `<name>_redacted.pdf`.
- `--box-width {fixed,tight}` (default: `fixed`) — `fixed` draws a canonical box width per PII type (email/phone), so the box size can't be used to guess the original text's length; `tight` hugs the exact matched text instead.
- `--label` / `--no-label` (default: on) — draw a `[EMAIL]` / `[PHONE]` text label inside the redaction box, instead of a blank black box.
- `--scrub` / `--no-scrub` (default: on) — also strip document metadata, embedded files, JavaScript, thumbnails (like Adobe Acrobat's "Sanitize Document").

### Examples

```
python3 redact.py header contract.pdf
python3 redact.py all contract.pdf
python3 redact.py body ./invoices --inplace
python3 redact.py all contract.pdf --box-width tight --no-label --no-scrub
```

## What gets redacted

Regex-based detection only:

- Email addresses
- Phone numbers (common formats, optional country code)

Person names and generic user IDs are **not** detected — regex can't reliably distinguish those from other text, and false positives would break document content.

## Testing

```
python3 test_redact.py
```

Builds a synthetic PDF with known PII in each region and asserts each region flag redacts only its own PII, leaving the rest intact.

## License

[MIT](LICENSE)
