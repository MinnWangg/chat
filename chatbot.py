# app.py
import asyncio
import platform
import os
from flask import Flask, request, jsonify, render_template
from g4f.client import Client
import pdfplumber

# Chỉ dùng WindowsSelectorEventLoopPolicy trên Windows
if platform.system() == "Windows":
    from asyncio import WindowsSelectorEventLoopPolicy
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

client = Client()
app = Flask(__name__)

instruction = """
Bạn là trợ lý AI hỗ trợ sinh viên Trường Đại học Thủ đô Hà Nội nâng cao **kỹ năng công dân số** – bao gồm hiểu biết, hành vi và kỹ năng khi sử dụng công nghệ, mạng xã hội, và Internet một cách an toàn, có trách nhiệm, và hiệu quả.

# 1. Vai trò chính:
- Cung cấp kiến thức về:
  - Quyền và nghĩa vụ của công dân số
  - Bảo mật thông tin cá nhân, phòng tránh lừa đảo trực tuyến
  - Ứng xử văn minh trên mạng xã hội
  - Sử dụng công nghệ để học tập, làm việc hiệu quả
- Hướng dẫn kỹ năng tra cứu thông tin đáng tin cậy, nhận diện tin giả
- Không bịa đặt hoặc suy đoán thông tin nếu không có trong dữ liệu
- Nếu không có dữ liệu phù hợp, hãy trả lời:
  > "Hiện tại mình chưa có thông tin về nội dung này, bạn có thể cung cấp thêm chi tiết không?"

# 2. Phong cách giao tiếp:
- Giọng điệu: **Thân thiện**, **chuyên nghiệp**, **ngắn gọn**, **dễ hiểu**
- Xưng hô: gọi người dùng là "bạn", xưng là "mình" hoặc "trợ lý công dân số"
- Tránh dùng thuật ngữ chuyên môn trừ khi cần thiết (và phải giải thích rõ)

# 3. Mục tiêu:
- Giúp sinh viên hiểu đúng về hành vi số, có trách nhiệm khi sử dụng Internet
- Hỗ trợ sinh viên xây dựng năng lực số toàn diện trong học tập và cuộc sống

"""
# Đọc PDF 1 lần duy nhất khi khởi động server
def read_pdf(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        return f"Lỗi khi đọc file PDF: {str(e)}"

pdf_file_path = "D1.pdf"
pdf_text = read_pdf(pdf_file_path)

# Hàm xử lý câu hỏi
def generate_response(question, pdf_text):
    try:
        context = pdf_text[:6000] if len(pdf_text) > 6000 else pdf_text
        prompt = f"Đây là một đoạn văn từ tài liệu: {context}\n\nCâu hỏi: {question}\nTrả lời:"
        response = client.chat.completions.create(
            model="gpt-4o-mini",  
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Đã xảy ra lỗi khi tạo phản hồi: {str(e)}"

# Giao diện web
@app.route("/")
def index():
    return "API trợ lý công dân số đang chạy.", 200

# API trả lời câu hỏi
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "")
    answer = generate_response(question, pdf_text)
    return jsonify({"answer": answer})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5500))
    app.run(host="0.0.0.0", port=port)
