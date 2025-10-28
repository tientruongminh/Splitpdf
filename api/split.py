import json, os
from pathlib import Path
from typing import List, Tuple
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs
from io import BytesIO
from splitter import split_pdf
import tempfile

def parse_tsv(s: str) -> List[Tuple[str,int]]:
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

def parse_json_toc(s: str) -> List[Tuple[str,int]]:
    import json as _json
    data = _json.loads(s)
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

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            ctype = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in ctype:
                self.send_json(400, {"error":"Content-Type must be multipart/form-data"})
                return

            # parse multipart
            import cgi
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={"REQUEST_METHOD":"POST","CONTENT_TYPE":ctype}
            )
            pdf_item = form["pdf"] if "pdf" in form else None
            toc_item = form["toc"] if "toc" in form else None
            toc_type = form.getvalue("toc_type", "json")
            page_offset = int(form.getvalue("page_offset", "0"))
            outdir_name = form.getvalue("outdir", "AIMA_Split")

            if not pdf_item or not toc_item:
                self.send_json(400, {"error":"Missing files"})
                return

            # lưu file vào /tmp
            tmpdir = Path("/tmp")
            pdf_path = tmpdir / pdf_item.filename
            with open(pdf_path, "wb") as f:
                f.write(pdf_item.file.read())

            toc_text = toc_item.file.read().decode("utf-8", errors="ignore")
            if toc_type == "json":
                toc = parse_json_toc(toc_text)
            else:
                toc = parse_tsv(toc_text)

            outdir = tmpdir / outdir_name
            written = split_pdf(pdf_path, toc, outdir, page_offset=page_offset)

            # trả danh sách file đã viết, bạn có thể đổi sang zip rồi trả URL tạm nếu muốn
            self.send_json(200, {
                "ok": True,
                "parts": [{"name": n} for n in written],
                "index_tsv": str(outdir / "SPLIT_INDEX.tsv")  # nếu bạn cũng ghi file index trong split_pdf
            })
        except Exception as e:
            self.send_json(500, {"error": str(e)})

    def send_json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
