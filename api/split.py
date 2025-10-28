# api/split.py
import io
import json
import zipfile
import requests
from pathlib import Path

def handler(request):
    # Set CORS headers
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }
    
    if request.method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": headers
        }

    try:
        # Parse JSON body
        if hasattr(request, 'body'):
            body = json.loads(request.body)
        else:
            return {
                "statusCode": 400,
                "headers": {**headers, "Content-Type": "application/json"},
                "body": json.dumps({"error": "No body received"})
            }

        print("Received request body:", body)  # Debug log

        source = body.get("source", "supabase")
        if source != "supabase":
            return {
                "statusCode": 400,
                "headers": {**headers, "Content-Type": "application/json"},
                "body": json.dumps({"error": "Unsupported source"})
            }

        file_url = body.get("url")
        toc_type = body.get("toc_type", "json")
        toc_text = body.get("toc", "")
        page_offset = int(body.get("page_offset", 0))
        outdir_name = body.get("outdir", "AIMA_Split")

        if not file_url or not toc_text:
            return {
                "statusCode": 400,
                "headers": {**headers, "Content-Type": "application/json"},
                "body": json.dumps({"error": "Missing url or toc"})
            }

        print(f"Downloading PDF from: {file_url}")  # Debug log

        # Download PDF from Supabase
        response = requests.get(file_url, timeout=60)
        response.raise_for_status()
        
        print(f"PDF downloaded, size: {len(response.content)} bytes")  # Debug log

        # Parse TOC
        if toc_type == "json":
            toc_data = json.loads(toc_text)
            if isinstance(toc_data, list):
                toc = [(str(item["title"]), int(item["start"])) for item in toc_data]
            else:
                def extract_toc(d):
                    entries = []
                    for k, v in d.items():
                        if isinstance(v, dict):
                            entries.extend(extract_toc(v))
                        else:
                            entries.append((str(k), int(v)))
                    return entries
                toc = extract_toc(toc_data)
        else:  # TSV
            toc = []
            for line in toc_text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    toc.append((parts[1].strip(), int(parts[0])))
        
        toc.sort(key=lambda x: x[1])
        print(f"Parsed TOC with {len(toc)} chapters")  # Debug log

        # Process PDF
        from pypdf import PdfReader, PdfWriter
        
        pdf_buffer = io.BytesIO(response.content)
        reader = PdfReader(pdf_buffer)
        total_pages = len(reader.pages)
        
        print(f"PDF has {total_pages} pages")  # Debug log

        # Calculate page ranges
        ranges = []
        for i, (title, start_book) in enumerate(toc):
            pdf_start = start_book + page_offset - 1
            pdf_end = (toc[i+1][1] + page_offset - 2) if i < len(toc)-1 else total_pages-1
            pdf_end = min(pdf_end, total_pages-1)
            
            if pdf_start < 0 or pdf_start >= total_pages or pdf_end < pdf_start:
                raise ValueError(f"Invalid page range for chapter: {title}")
                
            ranges.append((title, pdf_start, pdf_end))

        # Create PDF files in memory
        written_files = {}
        for idx, (title, start, end) in enumerate(ranges, 1):
            print(f"Processing chapter {idx}: {title} (pages {start}-{end})")  # Debug log
            
            writer = PdfWriter()
            for page_num in range(start, end + 1):
                writer.add_page(reader.pages[page_num])
            
            # Generate filename
            import re
            def sanitize_filename(name):
                name = re.sub(r"[^\w\s\-\.]", "", name).strip()
                name = re.sub(r"\s+", "_", name)
                return name[:180]
            
            match = re.match(r"^(\d+)\s+(.+)$", title.strip())
            if match:
                filename = f"Ch{int(match.group(1)):02d}_{sanitize_filename(match.group(2))}.pdf"
            else:
                filename = f"Part_{idx:02d}_{sanitize_filename(title)}.pdf"
            
            # Save to bytes buffer
            chapter_buffer = io.BytesIO()
            writer.write(chapter_buffer)
            written_files[filename] = chapter_buffer.getvalue()

        # Create ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename, content in written_files.items():
                zipf.writestr(filename, content)
        
        zip_data = zip_buffer.getvalue()
        print(f"Created ZIP file, size: {len(zip_data)} bytes")  # Debug log

        # Return ZIP file
        return {
            "statusCode": 200,
            "headers": {
                **headers,
                "Content-Type": "application/zip",
                "Content-Disposition": f"attachment; filename={outdir_name}.zip"
            },
            "body": zip_data.hex()  # Encode binary as hex for Vercel
        }

    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback_msg = traceback.format_exc()
        print(f"Error: {error_msg}")  # Debug log
        print(f"Traceback: {traceback_msg}")  # Debug log
        
        return {
            "statusCode": 500,
            "headers": {**headers, "Content-Type": "application/json"},
            "body": json.dumps({
                "error": error_msg,
                "traceback": traceback_msg
            })
        }