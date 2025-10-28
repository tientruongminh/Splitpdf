Dưới đây là phiên bản **README.md** chuyên nghiệp, ngắn gọn, không dùng icon — phù hợp cho GitHub hoặc Vercel public repo:

---

# Split AIMA – PDF Chapter Splitter with TOC

### Overview

Split AIMA is a lightweight web application for splitting large PDF documents into chapters based on a provided Table of Contents (TOC).
The system supports both JSON and TSV TOC formats, can be run locally with Flask, or deployed serverlessly on Vercel.

---

## Features

* Upload a PDF file and a TOC file (JSON or TSV)
* Support for `page_offset` to align TOC numbering with actual PDF pages
* Automatically generates and returns a single ZIP file containing all split chapters
* Fully compatible with Vercel’s Python runtime (serverless)
* CORS-enabled API for easy frontend integration

---

## Project Structure

```
split_AIMA/
├─ api/
│  └─ split.py              # Serverless API endpoint for Vercel
├─ splitter.py              # Core logic for PDF splitting
├─ index.html               # Main web interface
├─ toc_generator.html       # TOC generator page
├─ requirements.txt         # Dependencies
├─ vercel.json              # Vercel configuration
├─ README.md
├─ uploads/                 # Temporary folder (ignored in deployment)
├─ outputs/                 # Temporary folder (ignored in deployment)
└─ server.py                # Local Flask server for testing
```

---

## Local Development

### 1. Create and activate virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run locally

```bash
python server.py
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Deploying to Vercel

### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<yourname>/split_AIMA.git
git push -u origin main
```

### Step 2: Deploy

1. Go to [https://vercel.com](https://vercel.com)
2. Select “New Project” → “Import from GitHub”
3. Choose the `split_AIMA` repository
4. Wait for the build to complete

---

## Vercel Configuration

**vercel.json**

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "api/**/*.py": {
      "maxDuration": 60
    }
  },
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

**.vercelignore**

```
.venv/
__pycache__/
uploads/
outputs/
*.pdf
*.zip
*.npy
*.pkl
*.joblib
*.parquet
*.log
tests/
docs/
```

---

## API Usage Example

```js
const form = new FormData();
form.append('pdf', pdfInput.files[0]);
form.append('toc', tocInput.files[0]);
form.append('toc_type', 'json');  // or 'tsv'
form.append('page_offset', '0');
form.append('outdir', 'AIMA_Split');

const res = await fetch('/api/split', { method: 'POST', body: form });
if (res.ok) {
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'AIMA_Split.zip';
  a.click();
  URL.revokeObjectURL(url);
}
```

---

## TOC Formats

**JSON format**

```json
[
  { "title": "1 Introduction", "start": 1 },
  { "title": "2 Search Algorithms", "start": 35 },
  { "title": "3 Knowledge Representation", "start": 87 }
]
```

**TSV format**

```
1   Introduction
35  Search Algorithms
87  Knowledge Representation
```

---

## Example Output

```
AIMA_Split.zip
 ├─ Ch01_Introduction.pdf
 ├─ Ch02_Search_Algorithms.pdf
 └─ Ch03_Knowledge_Representation.pdf
```

---

## Dependencies

| Package | Purpose                         |
| ------- | ------------------------------- |
| Flask   | Local and serverless web server |
| pypdf   | PDF reading and writing         |
| json    | TOC parsing                     |
| zipfile | Create ZIP output file          |

---

## License

MIT License © 2025 MinhTienCD

