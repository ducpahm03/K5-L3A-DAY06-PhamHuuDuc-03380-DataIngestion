from pathlib import Path
from pypdf import PdfReader, PdfWriter

# Đường dẫn file gốc của bạn
input_pdf_path = Path(r"C:\Users\phamd\Downloads\Workplace_Software_and_Skills_-_WEB_IlfJtcP.pdf")

# Thư mục đích lưu trong project
output_dir = Path("data")
output_dir.mkdir(parents=True, exist_ok=True)
output_pdf_path = output_dir / "chapter1_workplace_skills.pdf"

print(f"Đang đọc: {input_pdf_path}...")
reader = PdfReader(str(input_pdf_path))
writer = PdfWriter()

# Trang bắt đầu Chapter 1 là index 16, kết thúc Chapter Review là index 66 (tổng 51 trang)
start_page = 16
end_page = 66

for page_idx in range(start_page, end_page + 1):
    writer.add_page(reader.pages[page_idx])

with open(output_pdf_path, "wb") as f:
    writer.write(f)

print(f"Đã cắt thành công {len(writer.pages)} trang sang: {output_pdf_path.resolve()}")