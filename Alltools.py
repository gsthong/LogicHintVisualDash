#tập hợp 4 file code còn lại , chứa CLI vs Backend API, frontend render nếu muốn ổn định
#############


#project/
#├── .env              # Chứa GROQ_API_KEY
#├── Alltools.py       # File xử lý logic AI của bạn
#├── main.py           # Backend API (FastAPI)
#└── index.html        # Frontend (Giao diện người dùng)


#Nguyễn Đức Minh - 25521111 - UIT - K20


import sys
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

############################
# CONFIG
############################

MODELS = {
    "offline": "qwen2.5:14b",
    "online": "llama-3.3-70b-versatile"
}

LLAMA_URL = "http://localhost:11434/api/generate"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

GROQ_KEY = os.getenv("GROQ_API_KEY")

############################
# PROMPTS
############################

PROMPT_1 = """
Bạn là API tạo Mermaid Flowchart chính xác.

Nhiệm vụ: Phân tích code và tạo flowchart Mermaid.

QUY TẮC:

1. KHÔNG viết: graph TD, markdown, ```mermaid, giải thích.
2. Chỉ trả về các dòng flowchart.
3. Node chỉ dùng:
   A[Text]
   B{Condition}
4. KHÔNG dùng ký tự: ( ) " ' : ;
5. Text trong node chỉ dùng: a-z A-Z 0-9 space + - * / < > =
6. Node ID ngắn: A tới Z hoặc AA AB AC nếu cần.
7. Edge chỉ dùng:
   -->
   -->|Yes|
   -->|No|
8. KHÔNG viết code trong node.
9. Text node tối đa 8 từ.
10. Nếu vi phạm quy tắc hãy tự sửa trước khi trả kết quả.

Ví dụ hợp lệ:

A[Start] --> B[Read n]
B --> C{n > 0}
C -->|Yes| D[Process]
C -->|No| E[End]
D --> E

Code cần phân tích:
{doc}
"""

PROMPT_2 = """
Bạn là chuyên gia phân tích chương trình.

Nhiệm vụ :

Phân tích đoạn code sau và mô tả logic hoạt động của chương trình (code) hoặc bài toán.

Mô tả đúng trình tự thực thi.

Giải thích rõ các điều kiện rẽ nhánh và vòng lặp (nếu có).

Không viết lại code.

Không giải thích lan man.

Trả về đúng format bên dưới.

• Format trả về:

Logic Description:

1. ...

2. ...

3. ...

Code hoặc bài toán đây:

{doc}

CHỈ TRẢ VỀ ĐÚNG FORMAT ĐÓ!
"""

PROMPT_3 = """
Bạn là chuyên gia phân tích độ phức tạp thuật toán trong code.

Nhiệm vụ:

Phân tích đoạn code sau và trả về theo format:

Algorithm :

Time Complexity (Big-O) :

Space Complexity (Big-O) :

Giải thích ngắn gọn tối đa .

Code đây:

{doc}

CHỈ TRẢ VỀ ĐÚNG FORMAT ĐÓ!
"""

############################
# CLEAN MERMAID
############################

def clean_mermaid(doc: str):

    lines = doc.splitlines()
    cleaned = ["graph TD"]

    for line in lines:

        line = line.strip()

        if not line:
            continue

        line = line.replace("```mermaid", "")
        line = line.replace("```", "")

        if line.lower().startswith("graph"):
            continue

        line = line.replace(";", "")

        line = re.sub(r"\((.*?)\)", r"[\1]", line)

        def clean_square(match):
            text = match.group(1)
            text = re.sub(r"[\"':()]", "", text)
            text = re.sub(r"[^a-zA-Z0-9_ +\-*/<>=%]", " ", text)
            text = re.sub(r"\s+", " ", text)
            return "[" + text.strip() + "]"

        line = re.sub(r"\[(.*?)\]", clean_square, line)

        cleaned.append("    " + line)

    return "\n".join(cleaned)

############################
# AI CALL
############################

def call_ai(mode, prompt):

    if mode == "offline":

        payload = {
            "model": MODELS["offline"],
            "prompt": prompt,
            "stream": False
        }

        r = requests.post(LLAMA_URL, json=payload, timeout=30)

        if r.status_code != 200:
            raise Exception("goi_nguoi_den_sua_:))")

        return r.json().get("response", "")

    elif mode == "online":

        if not GROQ_KEY:
            raise Exception("goi_nguoi_den_sua_:))")

        headers = {
            "Authorization": f"Bearer {GROQ_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MODELS["online"],
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }

        r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=20)

        if r.status_code != 200:
            raise Exception("Groq API error")

        return r.json()["choices"][0]["message"]["content"]

    else:
        raise Exception("Invalid mode")

############################
# MAIN TOOL FUNCTION
############################

def analyze_code(mode, choice, doc):

    doc = doc.strip()

    if not doc:
        return {"error": "empty input"}

    if len(doc) > 20000:
        return {"error": "input too large"}

    if choice == "1":

        prompt = PROMPT_1.replace("{doc}", doc)

        result = call_ai(mode, prompt)

        fixed = clean_mermaid(result)

        return {
            "type": "mermaid",
            "data": fixed
        }

    elif choice == "2":

        prompt = PROMPT_2.replace("{doc}", doc)

        result = call_ai(mode, prompt)

        return {
            "type": "logic",
            "data": result.strip()
        }

    elif choice == "3":

        prompt = PROMPT_3.replace("{doc}", doc)

        result = call_ai(mode, prompt)

        return {
            "type": "complexity",
            "data": result.strip()
        }

    else:

        return {"error": "invalid option"}

############################
# TERMINAL TEST
############################

if __name__ == "__main__":

    print("Mode: offline / online")
    mode = input("> ")

    print("Option:")
    print("1 Flowchart")
    print("2 Logic")
    print("3 Complexity")

    choice = input("> ")

    print("Paste code then CTRL+D\n")

    doc = sys.stdin.read()

    result = analyze_code(mode, choice, doc)

    print("\nRESULT:\n")

    print(result)