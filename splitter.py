from pathlib import Path
from typing import List, Tuple
from pypdf import PdfReader, PdfWriter
import re

def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^\w\s\-\.]", "", name).strip()
    name = re.sub(r"\s+", "_", name)
    return name[:180]

def split_pdf(pdf_path: Path, toc: List[Tuple[str,int]], outdir: Path, page_offset: int = 0):
    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    ranges = []
    for i, (title, start_book) in enumerate(toc):
        pdf_start = start_book + page_offset - 1
        pdf_end = (toc[i+1][1] + page_offset - 2) if i < len(toc)-1 else total-1
        pdf_end = min(pdf_end, total-1)
        if pdf_start < 0 or pdf_start >= total or pdf_end < pdf_start:
            raise ValueError("Invalid TOC or page_offset")
        ranges.append((title, pdf_start, pdf_end))

    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for idx, (title, s, e) in enumerate(ranges, 1):
        # tên file như trong script của bạn
        m = re.match(r"^(\d+)\s+(.+)$", title.strip())
        if m:
            fname = f"Ch{int(m.group(1)):02d}_{sanitize_filename(m.group(2))}.pdf"
        else:
            fname = f"Part_{idx:02d}_{sanitize_filename(title)}.pdf"
        out_path = outdir / fname
        w = PdfWriter()
        for p in range(s, e+1):
            w.add_page(reader.pages[p])
        with open(out_path, "wb") as f:
            w.write(f)
        written.append(out_path.name)
    return written
