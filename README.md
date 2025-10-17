# 📘 AIMA Splitter — Tự động cắt sách *Artificial Intelligence: A Modern Approach* theo từng chương

Công cụ này giúp bạn **tự động chia file PDF của sách AIMA** (Artificial Intelligence: A Modern Approach) thành **từng chương riêng biệt**, dựa trên bảng mục lục (TOC) và số trang bắt đầu từng chương.

---

## 🧩 Cấu trúc thư mục

```
split_AIMA/
│
├── AI.pdf                   # File PDF gốc (AIMA)
├── aima_toc.tsv             # Bảng TOC gồm tên chương và số trang bắt đầu
├── split_pdf_by_chapters.py # Script cắt PDF
└── README.md
```

---

## ⚙️ Cài đặt

### 1. Cài thư viện phụ thuộc
Chỉ cần `pypdf` để đọc và ghi PDF:
```bash
pip install pypdf
```

---

## 🚀 Cách dùng

### 🧠 Thông tin cơ bản
- File TOC (`aima_toc.tsv`) chứa số trang bắt đầu của từng chương (đã trích thủ công từ sách).  
- Trong bản PDF chính thức, **book page 1 tương ứng với PDF page 20**,  
  nên cần đặt `--page-offset 19`.

---

### ▶️ Cách chạy trên Linux / WSL / macOS
```bash
python split_pdf_by_chapters.py   --pdf "AI.pdf"   --toc-tsv "aima_toc.tsv"   --outdir "AIMA_Split"   --page-offset 19
```

### ▶️ Cách chạy trên Windows PowerShell / CMD
```powershell
python split_pdf_by_chapters.py --pdf "AI.pdf" --toc-tsv "aima_toc.tsv" --outdir "AIMA_Split" --page-offset 19
```

---

## 📁 Kết quả sau khi chạy

Thư mục `AIMA_Split/` sẽ được tạo, chứa:
```
AIMA_Split/
├── Ch01_Introduction.pdf
├── Ch02_Intelligent_Agents.pdf
├── Ch03_Solving_Problems_by_Searching.pdf
...
├── Ch27_AI_The_Present_and_Future.pdf
├── Appendix_A_Mathematical_background.pdf
├── Appendix_B_Notes_on_Languages_and_Algorithms.pdf
├── Bibliography.pdf
└── SPLIT_INDEX.tsv  # Log chứa phạm vi trang cắt cho từng chương
```

---

## 🧾 File TOC: `aima_toc.tsv`

Đã được định dạng sẵn với 2 cột:  
`<book_page_number>   <chapter_title>`

Ví dụ:
```
1	1 Introduction
34	2 Intelligent Agents
64	3 Solving Problems by Searching
120	4 Beyond Classical Search
161	5 Adversarial Search
...
1044	27 AI: The Present and Future
1053	Appendix A - Mathematical background
1060	Appendix B - Notes on Languages and Algorithms
1063	Bibliography
```

---

## 🧮 Giải thích `--page-offset`

**`page-offset` = (PDF_page_bắt_đầu_book_1) - 1**

Ví dụ:
- Nếu trang 1 trong sách tương ứng với trang 20 trong PDF → `--page-offset 19`
- Nếu PDF bắt đầu ngay từ trang 1 của sách → `--page-offset 0`

---

## 🧰 Tuỳ chọn nâng cao

### Dùng TOC dạng JSON thay vì TSV
Bạn có thể chuyển TOC sang JSON, ví dụ:
```json
{
  "1 Introduction": 1,
  "2 Intelligent Agents": 34,
  "3 Solving Problems by Searching": 64
}
```

Chạy:
```bash
python split_pdf_by_chapters.py --pdf "AI.pdf" --toc-json "aima_toc.json" --page-offset 19
```

---

## 🧑‍💻 Ghi chú kỹ thuật

- Script sử dụng [PyPDF](https://pypi.org/project/pypdf/) (phiên bản 3+)
- Hoạt động tốt với file PDF gốc AIMA 4th Edition (Pearson)
- Hỗ trợ UTF-8 (có thể xử lý tiêu đề tiếng Việt)
- Tự động sắp xếp chương theo thứ tự số trang trong TOC

---

## 📄 Giấy phép

MIT License © 2025 — bạn có thể sử dụng tự do cho mục đích cá nhân hoặc học tập.  
Tác giả cấu trúc script và TOC: **TienCD**

---

## ✨ Mẹo nhỏ

Sau khi tách chương, bạn có thể:
- Đưa từng chương vào Kindle / iPad để đọc riêng.
- Dùng các chương nhỏ để huấn luyện mô hình NLP hoặc RAG.
- Gắn metadata (programmatically) để tạo index cho chatbot học theo từng chương.

---

**Enjoy reading & experimenting with AIMA! 🚀**
