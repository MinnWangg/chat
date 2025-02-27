import sys
import asyncio
import re
from g4f.client import Client
import pdfplumber
from flask import Flask, request, jsonify
from flask_cors import CORS
sys.stdout.reconfigure(encoding='utf-8')
client = Client()

app = Flask(__name__)  # Tạo ứng dụng Flask
CORS(app)
def read_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def generate_response(question, pdf_text):
    try:
        context = pdf_text[:6000] if len(pdf_text) > 6000 else pdf_text
        prompt = f"Đây là một đoạn văn từ tài liệu: {context}\n\nCâu hỏi: {question}\nTrả lời:"

        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[{"role": "user", "content": prompt}],
        )

        answer = response.choices[0].message.content.strip()
        answer = re.sub(r'(\d+)\.\s', r'<li>\1. ', answer)
        return answer.strip()
    except Exception as e:
        return f"Lỗi: {str(e)}"

# Đọc file PDF một lần khi khởi động server
pdf_file_path = "test.pdf"  # Đặt file PDF trong cùng thư mục
pdf_text = read_pdf(pdf_file_path)

@app.route("/", methods=["GET"])
def home():
    return "Chatbot API đang chạy!"

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "")
    if not question:
        return jsonify({"error": "Thiếu câu hỏi"}), 400

    answer = generate_response(question, pdf_text)
    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
