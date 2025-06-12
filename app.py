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
