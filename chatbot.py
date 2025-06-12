import asyncio
import json
import os
from flask_cors import CORS
import sys
import platform
import pdfplumber
from flask import Flask, request, jsonify
from g4f.client import Client

if os.name == "nt":
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

def read_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)

def read_pdf(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        return f"Lỗi khi đọc file PDF: {str(e)}"


def save_chat_history(question, answer, file_path="chat_history.json"):
    try:
        history = []
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        history.append({"question": question, "answer": answer})
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Lỗi khi lưu lịch sử:", e)

def load_chat_history(file_path="chat_history.json"):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return [(item["question"], item["answer"]) for item in json.load(f)]
    return []

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


context_history = load_chat_history()

def generate_response(question, json_data):
    try:
        context = json.dumps(json_data, ensure_ascii=False, indent=2)
        context_prompt = "\n".join([f"Câu hỏi: {q}\nTrả lời: {a}" for q, a in context_history])

        prompt = f"{instruction}\n\nDữ liệu từ hệ thống:\n{context}\n\n{context_prompt}\n\nCâu hỏi: {question}\nTrả lời:"

        response = client.chat.completions.create(
            # model="gpt-3.5-turbo",
            model="gpt-4o-mini", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        print("RESPONSE:", response)  # ✅ Thêm log

        if not response.choices:
            return "Hiện tại mình chưa nhận được phản hồi từ hệ thống. Bạn nhỏ thử hỏi lại một câu khác nhé!"

        answer = response.choices[0].message.content.strip()
        
        if "Tôi chưa có thông tin" in answer or len(answer) < 5:
            return "Hiện tại tôi chưa có thông tin về vấn đề này, bạn có thể cung cấp thêm thông tin về nội dung bạn quan tâm không, mình sẽ giúp bạn tìm kiếm thêm nhé."
        
        context_history.append((question, answer))
        return answer

    except Exception as e:
        return f"Lỗi trong quá trình xử lý: {str(e)}"


@app.route("/")
def index():
    return "API trợ lý công dân số đang chạy.", 200

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('question')
    
    if not question:
        return jsonify({"error": "Không nhận được câu hỏi."}), 400

    pdf_file_path = "DOL.pdf"
    pdf_text = read_pdf(pdf_file_path)

    file_dict_path = "Data2_file.json"  
    file_dict = read_json(file_dict_path)

    answer = generate_response(question, pdf_text)
    save_chat_history(question, answer)

    file_response = answer_with_related_files(question, file_dict)
    if file_response:
        html_links = "<br>".join(
            [f'📘 <a href="{f["url"]}" target="_blank">{f["name"]}</a>' for f in file_response]
        )
        answer += f"\n\n📎 Dưới đây là tài liệu liên quan bạn có thể tham khảo:\n{html_links}"

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
    