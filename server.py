from flask import Flask, request, jsonify, send_from_directory, Response, send_file
from pathlib import Path
from splitter import split_pdf
import json
import zipfile
import io
import time
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins='*', methods=['GET', 'POST', 'OPTIONS'], allow_headers=['Content-Type'])
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

def parse_tsv(s: str):
    out = []
    for line in s.splitlines():
        line = line.strip()
        if not line or line.startswith("#"): 
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            raise ValueError("Định dạng TSV không hợp lệ")
        start = int(parts[0])
        title = parts[1].strip()
        out.append((title, start))
    out.sort(key=lambda x: x[1])
    return out

def parse_json_toc(s: str):
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
        raise ValueError("Định dạng JSON không được hỗ trợ")
    entries.sort(key=lambda x: x[1])
    return entries

def sanitize_filename(name: str) -> str:
    import re
    name = re.sub(r"[^\w\s\-\.]", "", name).strip()
    name = re.sub(r"\s+", "_", name)
    return name[:180]

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/split', methods=['POST', 'OPTIONS'])
def api_split():
    if request.method == 'OPTIONS':
        response = jsonify({'ok': True})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    try:
        pdf_file = request.files.get('pdf')
        toc_file = request.files.get('toc')
        toc_type = request.form.get('toc_type', 'json')
        page_offset = int(request.form.get('page_offset', '0'))
        outdir_name = request.form.get('outdir', 'AIMA_Split')

        if not pdf_file or not toc_file:
            return jsonify({'error': 'Thiếu file PDF hoặc file TOC'}), 400

        pdf_filename = pdf_file.filename
        pdf_path = UPLOAD_DIR / pdf_filename
        pdf_file.save(pdf_path)

        toc_text = toc_file.read().decode('utf-8', errors='ignore')
        
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

    def generate():
        try:
            import re
            from pypdf import PdfReader, PdfWriter
            
            yield f'data: {json.dumps({"type": "log", "message": "✅ Đã tải file lên thành công"})}\n\n'
            yield f'data: {json.dumps({"type": "log", "message": "📖 Đang đọc mục lục..."})}\n\n'
            
            if toc_type == 'json':
                toc = parse_json_toc(toc_text)
            else:
                toc = parse_tsv(toc_text)

            yield f'data: {json.dumps({"type": "log", "message": f"📚 Tìm thấy {len(toc)} chương"})}\n\n'

            outdir = OUTPUT_DIR / outdir_name
            outdir.mkdir(parents=True, exist_ok=True)
            
            yield f'data: {json.dumps({"type": "log", "message": "🔍 Đang đọc file PDF..."})}\n\n'
            
            reader = PdfReader(str(pdf_path))
            total = len(reader.pages)
            yield f'data: {json.dumps({"type": "log", "message": f"📄 PDF có {total} trang"})}\n\n'
            
            ranges = []
            
            for i, (title, start_book) in enumerate(toc):
                pdf_start = start_book + page_offset - 1
                pdf_end = (toc[i+1][1] + page_offset - 2) if i < len(toc)-1 else total-1
                pdf_end = min(pdf_end, total-1)
                if pdf_start < 0 or pdf_start >= total or pdf_end < pdf_start:
                    raise ValueError(f"Trang bắt đầu không hợp lệ cho chương: {title}")
                ranges.append((title, pdf_start, pdf_end))

            yield f'data: {json.dumps({"type": "log", "message": "✂️ Bắt đầu tách PDF thành các chương..."})}\n\n'
            
            written = []
            for idx, (title, s, e) in enumerate(ranges, 1):
                yield f'data: {json.dumps({"type": "progress", "current": idx, "total": len(ranges), "message": f"Đang xử lý: {title}"})}\n\n'
                
                m = re.match(r"^(\d+)\s+(.+)$", title.strip())
                if m:
                    chapter_num = int(m.group(1))
                    chapter_title = m.group(2)
                    fname = f"Ch{chapter_num:02d}_{sanitize_filename(chapter_title)}.pdf"
                else:
                    fname = f"Part_{idx:02d}_{sanitize_filename(title)}.pdf"
                
                out_path = outdir / fname
                w = PdfWriter()
                for p in range(s, e+1):
                    w.add_page(reader.pages[p])
                with open(out_path, "wb") as f:
                    w.write(f)
                written.append(fname)
                yield f'data: {json.dumps({"type": "log", "message": f"✅ Đã tạo: {fname}"})}\n\n'

            yield f'data: {json.dumps({"type": "log", "message": "🗜️ Đang nén các file thành ZIP..."})}\n\n'
            
            zip_filename = f"{outdir_name}.zip"
            zip_path = OUTPUT_DIR / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for fname in written:
                    file_path = outdir / fname
                    zipf.write(file_path, fname)
            
            yield f'data: {json.dumps({"type": "ok", "message": "🎉 Hoàn thành! Tất cả các chương đã được tách thành công"})}\n\n'
            yield f'data: {json.dumps({"type": "done", "payload": {"ok": True, "parts": [{"name": n} for n in written], "zip_url": f"/download/{zip_filename}", "total": len(written)}})}\n\n'

        except Exception as e:
            import traceback
            yield f'data: {json.dumps({"type": "error", "message": f"❌ Có lỗi xảy ra: {str(e)}", "traceback": traceback.format_exc()})}\n\n'

    return Response(generate(), mimetype='text/event-stream', headers={
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    })

@app.route('/api/split-supabase', methods=['POST', 'OPTIONS'])
def api_split_supabase():
    if request.method == 'OPTIONS':
        response = jsonify({'ok': True})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Không nhận được dữ liệu'}), 400

        source = data.get('source')
        pdf_url = data.get('url')
        toc_text = data.get('toc')
        toc_type = data.get('toc_type', 'json')
        page_offset = int(data.get('page_offset', 0))
        outdir_name = data.get('outdir', 'AIMA_Split')

        if source != 'supabase' or not pdf_url or not toc_text:
            return jsonify({'error': 'Thiếu thông tin bắt buộc'}), 400

        import requests
        response = requests.get(pdf_url, timeout=60)
        response.raise_for_status()
        
        pdf_path = UPLOAD_DIR / "temp_supabase.pdf"
        pdf_path.write_bytes(response.content)

        def generate():
            try:
                import re
                from pypdf import PdfReader, PdfWriter
                
                yield f'data: {json.dumps({"type": "log", "message": "✅ Đã tải PDF từ Supabase"})}\n\n'
                yield f'data: {json.dumps({"type": "log", "message": "📖 Đang đọc mục lục..."})}\n\n'
                
                if toc_type == 'json':
                    toc = parse_json_toc(toc_text)
                else:
                    toc = parse_tsv(toc_text)

                yield f'data: {json.dumps({"type": "log", "message": f"📚 Tìm thấy {len(toc)} chương"})}\n\n'

                outdir = OUTPUT_DIR / outdir_name
                outdir.mkdir(parents=True, exist_ok=True)
                
                yield f'data: {json.dumps({"type": "log", "message": "🔍 Đang đọc file PDF..."})}\n\n'
                
                reader = PdfReader(str(pdf_path))
                total = len(reader.pages)
                yield f'data: {json.dumps({"type": "log", "message": f"📄 PDF có {total} trang"})}\n\n'
                
                ranges = []
                
                for i, (title, start_book) in enumerate(toc):
                    pdf_start = start_book + page_offset - 1
                    pdf_end = (toc[i+1][1] + page_offset - 2) if i < len(toc)-1 else total-1
                    pdf_end = min(pdf_end, total-1)
                    if pdf_start < 0 or pdf_start >= total or pdf_end < pdf_start:
                        raise ValueError(f"Trang bắt đầu không hợp lệ cho chương: {title}")
                    ranges.append((title, pdf_start, pdf_end))

                yield f'data: {json.dumps({"type": "log", "message": "✂️ Bắt đầu tách PDF thành các chương..."})}\n\n'
                
                written = []
                for idx, (title, s, e) in enumerate(ranges, 1):
                    yield f'data: {json.dumps({"type": "progress", "current": idx, "total": len(ranges), "message": f"Đang xử lý: {title}"})}\n\n'
                    
                    m = re.match(r"^(\d+)\s+(.+)$", title.strip())
                    if m:
                        chapter_num = int(m.group(1))
                        chapter_title = m.group(2)
                        fname = f"Ch{chapter_num:02d}_{sanitize_filename(chapter_title)}.pdf"
                    else:
                        fname = f"Part_{idx:02d}_{sanitize_filename(title)}.pdf"
                    
                    out_path = outdir / fname
                    w = PdfWriter()
                    for p in range(s, e+1):
                        w.add_page(reader.pages[p])
                    with open(out_path, "wb") as f:
                        w.write(f)
                    written.append(fname)
                    yield f'data: {json.dumps({"type": "log", "message": f"✅ Đã tạo: {fname}"})}\n\n'

                yield f'data: {json.dumps({"type": "log", "message": "🗜️ Đang nén các file thành ZIP..."})}\n\n'
                
                zip_filename = f"{outdir_name}.zip"
                zip_path = OUTPUT_DIR / zip_filename
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for fname in written:
                        file_path = outdir / fname
                        zipf.write(file_path, fname)
                
                yield f'data: {json.dumps({"type": "ok", "message": "🎉 Hoàn thành! Tất cả các chương đã được tách thành công"})}\n\n'
                yield f'data: {json.dumps({"type": "done", "payload": {"ok": True, "parts": [{"name": n} for n in written], "zip_url": f"/download/{zip_filename}", "total": len(written)}})}\n\n'

            except Exception as e:
                import traceback
                yield f'data: {json.dumps({"type": "error", "message": f"❌ Có lỗi xảy ra: {str(e)}", "traceback": traceback.format_exc()})}\n\n'

        return Response(generate(), mimetype='text/event-stream', headers={
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        })

    except Exception as e:
        import traceback
        return jsonify({'error': f'Lỗi hệ thống: {str(e)}', 'traceback': traceback.format_exc()}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(
        OUTPUT_DIR / filename,
        as_attachment=True,
        download_name=filename
    )

@app.route('/toc-generator')
def toc_generator():
    return send_from_directory('.', 'toc_generator.html')
@app.route('/api/test', methods=['GET'])
def test_api():
    return jsonify({
        "status": "success", 
        "message": "API is working!",
        "timestamp": time.time()
    })
if __name__ == '__main__':
    # QUAN TRỌNG: Sửa port binding cho Render
    port = int(os.environ.get('PORT', 3000))
    app.run(
        host='0.0.0.0',  # ← THAY ĐỔI QUAN TRỌNG
        port=port, 
        debug=False  # ← Tắt debug mode trên production
    )