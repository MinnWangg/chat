import sys
import asyncio
import re
from g4f.client import Client
import pdfplumber

sys.stdout.reconfigure(encoding='utf-8')
client = Client()

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
        # answer = f"<ol>{answer}</ol>"
        return answer.strip()
    except Exception as e:
        return "Đã xảy ra lỗi trong quá trình xử lý câu hỏi."

pdf_file_path = 'test.pdf' 
pdf_text = read_pdf(pdf_file_path)

if __name__ == "__main__":
    question = sys.argv[1]
    answer = generate_response(question, pdf_text)
    print(answer)
