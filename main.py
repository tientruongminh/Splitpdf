#!/usr/bin/env python3
"""
Split a PDF into per-chapter PDFs using a table of contents of start pages.

Two input TOC formats are supported:
1) JSON (--toc-json): either
   - List of objects: [{"title": "Introduction", "start": 1}, ...]
   - Dict mapping title to start page: {"Introduction": 1, "Intelligent Agents": 34, ...}
   - Nested dicts by Part are also ok; they will be flattened.
2) TSV (--toc-tsv): each line "start<TAB>title"
   Example:
     1	Introduction
     34	Intelligent Agents
     64	Solving Problems by Searching

Important concepts:
- "start" is the BOOK page number (1-based). If your PDF page 1 is not book page 1,
  use --page-offset to align. Effective PDF index = (start + page_offset - 1).
  Example: if book page 1 is at PDF page 17, use --page-offset 16.
- The script infers each chapter's end page as (next_start - 1) except the last
  which goes to the end of the PDF.
- Output files are named "ChXX_Title.pdf" if a title starts with a numeric prefix,
  else an incremental counter is used.

Usage examples:
  python split_pdf_by_chapters.py --pdf aima.pdf --toc-json aima_toc.json --outdir out --page-offset 16
  python split_pdf_by_chapters.py --pdf aima.pdf --toc-tsv aima_toc.tsv --outdir out

Dependencies:
  pip install pypdf
"""

import argparse
import json
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any

from pypdf import PdfReader, PdfWriter


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^\w\s\-\.]", "", name, flags=re.UNICODE).strip()
    name = re.sub(r"\s+", "_", name)
    return name[:180] if len(name) > 180 else name


def load_toc_from_json(path: Path) -> List[Tuple[str, int]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict) or "title" not in item or "start" not in item:
                raise ValueError("JSON list items must have 'title' and 'start' keys")
            entries.append((str(item["title"]), int(item["start"])))
    elif isinstance(data, dict):
        # flatten any nested dicts
        def flatten(d: Dict[str, Any]):
            for k, v in d.items():
                if isinstance(v, dict):
                    for t, s in load_dict(v):
                        entries.append((t, s))
                else:
                    # value should be start page
                    entries.append((str(k), int(v)))

        def load_dict(d: Dict[str, Any]):
            for k, v in d.items():
                if isinstance(v, dict):
                    for sub in load_dict(v):
                        yield sub
                else:
                    yield (str(k), int(v))

        flatten(data)
    else:
        raise ValueError("Unsupported JSON structure for TOC")
    # sort by start page
    entries.sort(key=lambda x: x[1])
    return entries


def load_toc_from_tsv(path: Path) -> List[Tuple[str, int]]:
    entries: List[Tuple[str, int]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            raise ValueError(f"Invalid TSV line (need 'start<TAB>title'): {line}")
        start = int(parts[0])
        title = parts[1].strip()
        entries.append((title, start))
    entries.sort(key=lambda x: x[1])
    return entries


def infer_filename(idx: int, title: str) -> str:
    # Try to detect "Chapter NN" at start of title
    m = re.match(r"^(\d+)\s+(.+)$", title.strip())
    if m:
        num = int(m.group(1))
        rest = m.group(2)
        return f"Ch{num:02d}_{sanitize_filename(rest)}.pdf"
    else:
        return f"Part_{idx:02d}_{sanitize_filename(title)}.pdf"


def split_pdf(pdf_path: Path, toc: List[Tuple[str, int]], outdir: Path, page_offset: int = 0) -> None:
    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    if not toc:
        raise ValueError("TOC entries are empty")

    # Build ranges as list of (title, pdf_start_index, pdf_end_index_inclusive)
    ranges = []
    for i, (title, start_book_page) in enumerate(toc):
        pdf_start = start_book_page + page_offset - 1  # zero-based
        if pdf_start < 0 or pdf_start >= total:
            raise ValueError(f"Computed start page {pdf_start+1} out of range for title '{title}'. "
                             f"Check page_offset or start page.")
        if i < len(toc) - 1:
            next_start_book = toc[i + 1][1]
            pdf_end = (next_start_book + page_offset - 2)  # inclusive
        else:
            pdf_end = total - 1  # until last page
        pdf_end = min(pdf_end, total - 1)
        if pdf_end < pdf_start:
            raise ValueError(f"End before start for '{title}'. Check TOC ordering and page_offset.")
        ranges.append((title, pdf_start, pdf_end))

    outdir.mkdir(parents=True, exist_ok=True)

    for idx, (title, start_i, end_i) in enumerate(ranges, start=1):
        writer = PdfWriter()
        for p in range(start_i, end_i + 1):
            writer.add_page(reader.pages[p])
        fname = infer_filename(idx, title)
        out_path = outdir / fname
        with open(out_path, "wb") as f:
            writer.write(f)
        print(f"Wrote {out_path.name}  [{start_i+1}..{end_i+1} / {total}]")

    # Also write a simple index file
    index_path = outdir / "SPLIT_INDEX.tsv"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("pdf_start\tpdf_end\tbook_start\ttitle\n")
        for (title, start_book), (_, s, e) in zip(toc, ranges):
            f.write(f"{s+1}\t{e+1}\t{start_book}\t{title}\n")
    print(f"Wrote index: {index_path}")


def parse_args():
    ap = argparse.ArgumentParser(description="Split a PDF into chapters by TOC start pages")
    ap.add_argument("--pdf", required=True, help="Input PDF path")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--toc-json", help="Path to JSON TOC")
    group.add_argument("--toc-tsv", help="Path to TSV TOC with 'start<TAB>title'")
    ap.add_argument("--outdir", default="AIMA_Split", help="Output directory")
    ap.add_argument("--page-offset", type=int, default=0,
                    help="Offset to map book page 1 to PDF page (zero if same). Example: if book page 1 is PDF page 17, use 16")
    return ap.parse_args()


def main():
    args = parse_args()
    pdf_path = Path(args.pdf).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()

    if args.toc_json:
        toc = load_toc_from_json(Path(args.toc_json).expanduser().resolve())
    else:
        toc = load_toc_from_tsv(Path(args.toc_tsv).expanduser().resolve())

    split_pdf(pdf_path, toc, outdir, page_offset=args.page_offset)


if __name__ == "__main__":
    main()
