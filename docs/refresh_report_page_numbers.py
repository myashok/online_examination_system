import re
from pathlib import Path

import fitz
from docx import Document


ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "docs" / "ONLINE-EXAMINATION-SYSTEM-MCSP-232-FINAL.docx"
PDF = ROOT / "docs" / "ONLINE-EXAMINATION-SYSTEM-MCSP-232-FINAL.pdf"


def normalized(value):
    return re.sub(r"\s+", " ", value.replace("\u00ad", "")).strip().lower()


def page_for(title, pages):
    key = normalized(title)
    if not key:
        return None
    start = 0 if title in {
        "Approved Proforma and Guide Bio-data",
        "Certificate of Originality",
        "Declaration",
        "Acknowledgement",
        "Abstract",
    } else 9
    for index, text in enumerate(pages[start:], start=start):
        if key in text:
            return index + 1
    # Long captions can be split by Writer in ways that defeat exact matching.
    prefix = normalized(re.split(r"[.—:]", title, maxsplit=1)[0])
    if len(prefix) >= 12:
        for index, text in enumerate(pages[start:], start=start):
            if prefix in text:
                return index + 1
    return None


def main():
    pdf = fitz.open(PDF)
    pages = [normalized(page.get_text()) for page in pdf]
    document = Document(DOCX)
    changed = 0
    missed = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if "\t" not in text:
            continue
        title, old_page = text.rsplit("\t", 1)
        if not old_page.strip().isdigit():
            continue
        actual = page_for(title.strip(), pages)
        if actual is None:
            missed.append(title.strip())
            continue
        if str(actual) != old_page.strip():
            paragraph.text = f"{title.strip()}\t{actual}"
            changed += 1
    document.save(DOCX)
    print(f"updated={changed} missed={len(missed)}")
    for title in missed:
        print(f"MISSED {title}")


if __name__ == "__main__":
    main()
