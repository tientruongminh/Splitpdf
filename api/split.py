# api/split.py
import io
import json
import zipfile
import requests
from pathlib import Path
from typing import List, Tuple

def parse_tsv(s: str) -> List[Tuple[str, int]]:
    out = []
    for line in s.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            raise ValueError("TSV line invalid")
        start = int(parts[0])
        title = parts[1].strip()
        out.append((title, start))
    out.sort(key=lambda x: x[1])
    return out

def parse_json_toc(s: str) -> List[Tuple[str, int]]:
    data = json.loads(s)
    entries = []
    if isinstance(data, list):
        for item in data:
            entries.append((str(item["title"]), int(item["start"])))
    elif isinstance(data, dict):
        def rec(d):
            for k, v in d.items():
                if isinstance(v, dict):
                    yield from rec(v)
                else:
                    yield (str(k), int(v))
        entries = list(rec(data))
    else:
        raise ValueError("Unsupported JSON structure")
    entries.sort(key=lambda x: x[1])
    return entries

def sanitize_filename(name: str) -> str:
    import re
    name = re.sub(r"[^\w\s\-\.]", "", name).strip()
    name = re.sub(r"\s+", "_", name)
    return name[:180]

def split_pdf_vercel(pdf_buffer, toc: List[Tuple[str,int]], page_offset: int = 0):
    from pypdf import PdfReader, PdfWriter
    import re
    
    reader = PdfReader(pdf_buffer)
    total = len(reader.pages)
    ranges = []
    
    for i, (title, start_book) in enumerate(toc):
        pdf_start = start_book + page_offset - 1
        pdf_end = (toc[i+1][1] + page_offset - 2) if i < len(toc)-1 else total-1
        pdf_end = min(pdf_end, total-1)
        if pdf_start < 0 or pdf_start >= total or pdf_end < pdf_start:
            raise ValueError("Invalid TOC or page_offset")
        ranges.append((title, pdf_start, pdf_end))

    written_files = {}
    
    for idx, (title, s, e) in enumerate(ranges, 1):
        # tên file như trong script của bạn
        m = re.match(r"^(\d+)\s+(.+)$", title.strip())
        if m:
            fname = f"Ch{int(m.group(1)):02d}_{sanitize_filename(m.group(2))}.pdf"
        else:
            fname = f"Part_{idx:02d}_{sanitize_filename(title)}.pdf"
        
        w = PdfWriter()
        for p in range(s, e+1):
            w.add_page(reader.pages[p])
        
        # Save to bytes buffer
        pdf_buffer = io.BytesIO()
        w.write(pdf_buffer)
        pdf_buffer.seek(0)
        
        written_files[fname] = pdf_buffer.getvalue()
    
    return written_files

def handler(request):
    import json as json_module
    
    if request.method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        }

    try:
        # Parse JSON body
        body = request.get_json()
        
        if not body:
            return {
                "statusCode": 400,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json"
                },
                "body": json_module.dumps({"error": "Expect JSON body"})
            }

        source = body.get("source", "supabase")
        if source != "supabase":
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"},
                "body": json_module.dumps({"error": "Unsupported source"})
            }

        file_url = body.get("url")
        toc_type = body.get("toc_type", "json")
        toc_text = body.get("toc", "")
        page_offset = int(body.get("page_offset", 0))
        outdir_name = body.get("outdir", "AIMA_Split")

        if not file_url or not toc_text:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"},
                "body": json_module.dumps({"error": "Missing url or toc"})
            }

        # Download PDF from Supabase
        r = requests.get(file_url, timeout=60)
        r.raise_for_status()
        pdf_buffer = io.BytesIO(r.content)

        # Parse TOC
        toc = parse_json_toc(toc_text) if toc_type == "json" else parse_tsv(toc_text)

        # Split PDF
        written_files = split_pdf_vercel(pdf_buffer, toc, page_offset=page_offset)

        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname, content in written_files.items():
                zf.writestr(fname, content)
        zip_buffer.seek(0)

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/zip",
                "Content-Disposition": f"attachment; filename={outdir_name}.zip"
            },
            "body": zip_buffer.getvalue().decode('latin-1')  # For binary data in Vercel
        }

    except Exception as e:
        import traceback
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*", 
                "Content-Type": "application/json"
            },
            "body": json_module.dumps({
                "error": str(e),
                "traceback": traceback.format_exc()
            })
        }