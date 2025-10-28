# api/split.py
import io
import json
import zipfile
import requests
from pathlib import Path
from typing import List, Tuple
from flask import Flask, request, send_file, jsonify
from splitter import split_pdf

app = Flask(__name__)

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

@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp

@app.route("/", methods=["POST", "OPTIONS"])
def split_endpoint():
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        payload = request.get_json(silent=True) or {}
        if not payload:
            return jsonify({"error": "Expect JSON body"}), 400

        source = payload.get("source", "supabase")
        if source != "supabase":
            return jsonify({"error": "Unsupported source"}), 400

        file_url = payload.get("url")
        toc_type = payload.get("toc_type", "json")
        toc_text = payload.get("toc", "")
        page_offset = int(payload.get("page_offset", 0))
        outdir_name = payload.get("outdir", "AIMA_Split")

        if not file_url or not toc_text:
            return jsonify({"error": "Missing url or toc"}), 400

        # tải file vào /tmp
        tmpdir = Path("/tmp")
        tmpdir.mkdir(exist_ok=True)
        pdf_path = tmpdir / "input.pdf"

        r = requests.get(file_url, timeout=60)
        r.raise_for_status()
        pdf_path.write_bytes(r.content)

        # parse TOC
        toc = parse_json_toc(toc_text) if toc_type == "json" else parse_tsv(toc_text)

        # chạy split
        outdir = tmpdir / outdir_name
        outdir.mkdir(exist_ok=True)
        written = split_pdf(pdf_path, toc, outdir, page_offset=page_offset)

        # nén ZIP vào memory
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in written:
                fp = outdir / fname
                zf.write(fp, arcname=fname)
        zip_buf.seek(0)

        return send_file(
            zip_buf,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{outdir_name}.zip"
        )

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

# Vercel sẽ dùng biến app
