import asyncio
import platform
import os
import json
import re
from flask import Flask, request, jsonify
from g4f.client import Client
import pdfplumber

# Cấu hình event loop cho Windows
if platform.system() == "Windows":
    from asyncio import WindowsSelectorEventLoopPolicy
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

client = Client()
app = Flask(__name__)

instruction = """
Bạn là trợ lý AI đại diện cho Joynest, đóng vai trò là một **cố vấn học tập** hỗ trợ học sinh tiểu học trong quá trình rèn luyện và phát triển kỹ năng **công dân số**.

# 1. Vai trò chính:
- Cung cấp thông tin **chính xác**, **dễ hiểu** và **đáng tin cậy** về:
  - Bảo vệ thông tin cá nhân khi dùng mạng
  - Ứng xử văn minh, an toàn trên môi trường số
  - Cách phân biệt thông tin thật – giả
  - Tôn trọng bản quyền và người khác khi sử dụng nội dung trên mạng
- **Tuyệt đối không tự tạo thông tin** nếu nội dung không có trong tài liệu đã xác thực.
- Nếu không có thông tin phù hợp, hãy trả lời:
  > "Hiện tại mình chưa có thông tin về điều này, bạn nhỏ có thể nói rõ hơn được không? Mình sẽ cố gắng giúp bạn tìm hiểu nhé!"

# 2. Phong cách giao tiếp:
- Giọng điệu: **Thân thiện**, **gần gũi**, **ngắn gọn**, **phù hợp với học sinh tiểu học**
- Xưng hô: Gọi người dùng là "**bạn nhỏ**", xưng là "**mình**" hoặc "**trợ lý học tập**"
- Tránh dùng từ ngữ phức tạp; nếu buộc phải dùng, cần **giải thích đơn giản, dễ hiểu**

# 3. Nguyên tắc xử lý câu hỏi:
- Nếu câu hỏi **rõ ràng** và **nằm trong nội dung kỹ năng công dân số** → Trả lời chính xác theo nội dung đã cung cấp
- Nếu câu hỏi **chưa rõ nghĩa** → Hỏi lại để làm rõ:
  > "Bạn nhỏ đang muốn hỏi điều gì vậy? Bạn có thể nói cụ thể hơn không để mình giúp tốt hơn nhé!"
- Nếu câu hỏi **vượt ngoài nội dung kỹ năng công dân số** → Gợi ý bạn nhỏ hỏi thầy cô hoặc người lớn:
  > "Câu này hơi khó rồi, bạn nhỏ thử hỏi thầy cô hoặc bố mẹ xem sao nhé. Mình sẽ luôn sẵn sàng giúp khi bạn cần học kỹ năng công dân số!"

# 4. Mục tiêu của bạn:
- Hỗ trợ học sinh **hiểu và thực hành đúng kỹ năng công dân số**
- Giúp các bạn nhỏ **tự tin, an toàn và có trách nhiệm** khi tham gia vào môi trường số
- Đồng hành cùng học sinh trong hành trình trở thành **công dân số thông minh và tử tế**
"""

# Hàm đọc PDF
def read_pdf(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        return f"Lỗi khi đọc file PDF: {str(e)}"

# Hàm đọc JSON
def read_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)

# Gợi ý file liên quan
def answer_with_related_files(question, file_dict):
    for keyword in file_dict:
        if keyword.lower() in question.lower():
            file_list = file_dict[keyword]
            file_links = []
            for file in file_list:
                if isinstance(file, dict) and 'name' in file and 'path' in file:
                    file_links.append({
                        "name": file['name'],
                        "url": file['path']
                    })
            return file_links
    return None
def convert_markdown_links_to_html(text):
    return re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)

# Đọc tài liệu 1 lần khi khởi động
pdf_file_path = "D1.pdf"
pdf_text = read_pdf(pdf_file_path)

file_dict_path = "Data2_file.json"
file_dict = read_json(file_dict_path)

# Hàm xử lý câu hỏi
async def generate_response_async(question, pdf_text, file_dict):
    try:
        context = pdf_text[:6000] if len(pdf_text) > 6000 else pdf_text
        prompt = f"{instruction}\n\nDữ liệu tài liệu:\n{context}\n\nCâu hỏi: {question}\nTrả lời:"

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        answer = response.choices[0].message.content.strip()
        answer = convert_markdown_links_to_html(answer)

        # Thêm link tài liệu nếu có
        file_response = answer_with_related_files(question, file_dict)
        if file_response:
            html_links = "".join(
                [f'<li>📘 <a href="{f["url"]}" target="_blank"><strong>{f["name"]}</strong></a></li>' for f in file_response]
            )
            related_links_html = f'<br><br>📎 <strong>Dưới đây là tài liệu liên quan bạn có thể tham khảo:</strong><ul>{html_links}</ul>'
            answer += related_links_html

        return answer

    except Exception as e:
        return f"❌ Đã xảy ra lỗi khi tạo phản hồi: {str(e)}"

# API hỏi đáp
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "")
    if not question:
        return jsonify({"error": "Bạn chưa gửi câu hỏi."}), 400

    # Gọi hàm async một cách an toàn
    try:
        answer = asyncio.run(generate_response_async(question, pdf_text, file_dict))
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": f"❌ Đã xảy ra lỗi: {str(e)}"}), 500

# Giao diện chính
@app.route("/")
def index():
    return "API trợ lý công dân số đang chạy.", 200

# ... giữ nguyên phần cuối ...
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5500))
    app.run(host="0.0.0.0", port=port)
