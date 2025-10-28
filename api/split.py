# api/split.py  (Vercel Python Runtime - Flask WSGI)
import io
import json
import zipfile
from pathlib import Path
from typing import List, Tuple

from flask import Flask, request, send_file, jsonify

from splitter import split_pdf  # bạn đã có file splitter.py

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
        if not request.content_type or "multipart/form-data" not in request.content_type:
            return jsonify({"error": "Content-Type must be multipart/form-data"}), 400

        pdf_file = request.files.get("pdf")
        toc_file = request.files.get("toc")
        if not pdf_file or not toc_file:
            return jsonify({"error": "Missing PDF or TOC file"}), 400

        toc_type = request.form.get("toc_type", "json")
        page_offset = int(request.form.get("page_offset", "0"))
        outdir_name = request.form.get("outdir", "AIMA_Split")

        # lưu vào /tmp (chỉ tồn tại trong 1 request)
        tmpdir = Path("/tmp")
        tmpdir.mkdir(exist_ok=True)
        pdf_path = tmpdir / pdf_file.filename
        pdf_file.save(pdf_path)

        toc_text = toc_file.read().decode("utf-8", errors="ignore")
        toc = parse_json_toc(toc_text) if toc_type == "json" else parse_tsv(toc_text)

        # outdir tạm
        outdir = tmpdir / outdir_name
        outdir.mkdir(exist_ok=True)

        # gọi hàm xử lý của bạn: nên trả về danh sách tên file đã viết
        # ví dụ: written = ["Ch01_Intro.pdf", "Ch02_Search.pdf", ...]
        written = split_pdf(pdf_path, toc, outdir, page_offset=page_offset)

        # nén ZIP vào memory
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in written:
                file_path = outdir / fname
                # arcname để trong zip chỉ có tên file, không chứa path đầy đủ
                zf.write(file_path, arcname=fname)
        zip_buf.seek(0)

        # trả file zip trực tiếp cho client
        download_name = f"{outdir_name}.zip"
        return send_file(
            zip_buf,
            mimetype="application/zip",
            as_attachment=True,
            download_name=download_name
        )

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

# Vercel sẽ tự phát hiện biến `app` (Flask WSGI)
