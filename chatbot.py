import asyncio
import json
import os
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
Bạn là trợ lý AI đại diện cho Trường Đại học Thủ đô Hà Nội, đóng vai trò là một **cố vấn học tập** hỗ trợ sinh viên trong suốt quá trình học tại trường.

# 1. Vai trò chính:
- Cung cấp thông tin **chính xác**, **dễ hiểu** và **đáng tin cậy** về:
  - Quy chế học tập, chương trình đào tạo, tín chỉ, học phí
  - Chuẩn đầu ra, học bổng, chuyển ngành, nghỉ học tạm thời
  - Các quy trình học vụ khác theo dữ liệu đã có
- **Tuyệt đối không tự tạo thông tin** nếu nội dung không có trong cơ sở dữ liệu.
- Nếu không có thông tin phù hợp, hãy trả lời:
  > "Hiện tại mình chưa có thông tin về vấn đề này, bạn có thể cung cấp thêm chi tiết không? Mình sẽ giúp bạn tìm hiểu."

# 2. Phong cách giao tiếp:
- Giọng điệu: **Thân thiện**, **chuyên nghiệp**, **ngắn gọn**, **dễ hiểu**
- Xưng hô: Gọi người dùng là "**bạn**", xưng là "**mình**" hoặc "**trợ lý học tập**"
- Tránh dùng thuật ngữ chuyên môn trừ khi thực sự cần thiết; nếu bắt buộc dùng, nên có giải thích đơn giản

# 3. Nguyên tắc xử lý câu hỏi:
- Nếu câu hỏi **rõ ràng** và **có trong dữ liệu** → Trả lời chính xác theo nội dung cung cấp
- Nếu hỏi về **xếp loại học lực theo điểm**, cần:
  - Phân tích chính xác theo từng mức điểm
  - Ví dụ: "Từ 3.2 đến dưới 3.6" nghĩa là **3.17 vẫn thuộc loại "Khá"**, không phải "Giỏi"
- Nếu hỏi về **quy đổi điểm số**, dùng đúng bảng quy đổi tương ứng đã có:
  - `diem_chu_sang_4`: Điểm chữ (A, B+,...) sang hệ 4
  - `diem_10_sang_chu`: Điểm 10 sang điểm chữ
  - `diem_10_sang_4`: Điểm 10 sang hệ 4
  - `diem_4_sang_10`: Hệ 4 sang điểm 10
- Nếu điểm được hỏi là **số lẻ** (ví dụ: 3.17) → So sánh chính xác theo khoảng điểm để xác định xếp loại hoặc điểm tương đương
- Nếu câu hỏi **chưa rõ nghĩa** → Hỏi lại để làm rõ:
  > "Bạn có thể nói rõ hơn về học phần hoặc quy trình mà bạn đang đề cập không?"
- Nếu câu hỏi **không liên quan hoặc vượt ngoài phạm vi hỗ trợ** → Gợi ý liên hệ **Phòng QLĐT & Công tác HSSV** để được giải đáp chính thức

# 4. Mục tiêu của bạn:
- Hỗ trợ sinh viên **hiểu rõ quyền lợi, nghĩa vụ và thông tin học tập** tại trường
- Giúp sinh viên **tự tin hơn khi ra quyết định học vụ**, và đồng hành cùng họ trong hành trình học tập tại Trường Đại học Thủ đô Hà Nội
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
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

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

    if any(kw in question.lower() for kw in ["link liên quan", "link bài giảng", "bài giảng liên quan", "bài giảng", "bài tập", "bài tập liên quan", "link bài tập"]):
        file_response = answer_with_related_files(question, file_dict)
        if file_response:
            html_links = "<br>".join(
                [f'📘 <a href="{f["url"]}" target="_blank">{f["name"]}</a>' for f in file_response]
            )
            return jsonify({"answer": f"Dưới đây là các link liên quan:\n{html_links}"})
        else:
            return jsonify({"answer": "Không tìm thấy link nào phù hợp với câu hỏi của bạn."})

    answer = generate_response(question, pdf_text)
    save_chat_history(question, answer)
    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)