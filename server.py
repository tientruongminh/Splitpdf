# server.py
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
from main import split_pdf, load_toc_from_json, load_toc_from_tsv  # import trực tiếp
import json

BASE_DIR   = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

@app.route('/api/split', methods=['POST'])
def api_split():
    pdf_file = request.files.get('pdf')
    toc_file = request.files.get('toc')
    toc_type = request.form.get('toc_type', 'json')
    page_offset = int(request.form.get('page_offset', '0'))
    outdir = request.form.get('outdir', 'AIMA_Split')

    if not pdf_file or not toc_file:
        return jsonify({'error': 'Missing files'}), 400

    pdf_path = UPLOAD_DIR / pdf_file.filename
    toc_path = UPLOAD_DIR / toc_file.filename
    pdf_file.save(pdf_path)
    toc_file.save(toc_path)

    # parse TOC
    if toc_type == 'json':
        toc = load_toc_from_json(toc_path)
    else:
        toc = load_toc_from_tsv(toc_path)

    target_outdir = OUTPUT_DIR / outdir
    target_outdir.mkdir(parents=True, exist_ok=True)

    try:
        split_pdf(pdf_path, toc, target_outdir, page_offset=page_offset)
        files = sorted(p.name for p in target_outdir.iterdir() if p.suffix.lower() == '.pdf')
        return jsonify({
            'ok': True,
            'parts': [{'name': f} for f in files],
            'index_tsv': str(target_outdir / 'SPLIT_INDEX.tsv')
        })
    except Exception as e:
        return jsonify({'error': str(e)})
