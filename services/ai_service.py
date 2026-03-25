"""
AI Service — powered by Groq (llama-3.3-70b-versatile).
Handles: hints, bug analysis, complexity, flowchart, testcase generation,
         syllabus parsing, success explanation, problem parsing from text.
"""
import os
import json
import re
import requests
from typing import Optional

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
MODEL        = "llama-3.3-70b-versatile"


def _call(system: str, user: str, temperature: float = 0.2, max_tokens: int = 1500) -> str:
    if not GROQ_API_KEY:
        return "⚠️ GROQ_API_KEY not set. Configure it in Settings."
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    }
    try:
        r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"AI Error: {e}"


def get_hint(problem_description: str, code: str, hint_level: int, previous_hints: list) -> str:
    prev = "\n".join(f"Hint {h['level']}: {h['content']}" for h in previous_hints) if previous_hints else "None"
    system = """Bạn là AI hỗ trợ sinh viên lập trình. Nhiệm vụ: đưa gợi ý KHÔNG tiết lộ đáp án.
Hint level 1: gợi ý khái niệm, tư duy thuật toán.
Hint level 2: gợi ý cụ thể hơn về cách tiếp cận.
Hint level 3: gợi ý gần lời giải nhưng vẫn để sinh viên tự code.
KHÔNG viết code hoàn chỉnh. KHÔNG đưa đáp án trực tiếp."""
    user = f"""Đề bài: {problem_description}

Code hiện tại của sinh viên:
```
{code or '(chưa có code)'}
```

Gợi ý trước đó: {prev}

Hãy đưa gợi ý cấp độ {hint_level}. Trả lời bằng tiếng Việt, ngắn gọn, súc tích."""
    return _call(system, user)


def analyze_bugs(code: str, language: str, error_message: str, problem_description: str) -> dict:
    system = """Bạn là chuyên gia phân tích lỗi code. Phân tích lỗi và trả về JSON theo format:
{"bugs": [{"type": "...", "line": N, "message": "...", "fix": "..."}], "summary": "..."}
Các loại lỗi: syntax_error, logic_error, off_by_one, infinite_loop, uninitialized_var, missing_base_case, edge_case, tle_risk."""
    user = f"""Ngôn ngữ: {language}
Đề bài: {problem_description}
Lỗi: {error_message or 'WA - kết quả sai'}

Code:
```{language}
{code}
```

Trả về JSON hợp lệ."""
    result = _call(system, user, temperature=0.1)
    try:
        match = re.search(r'\{.*\}', result, re.DOTALL)
        return json.loads(match.group()) if match else {"bugs": [], "summary": result}
    except Exception:
        return {"bugs": [], "summary": result}


def analyze_complexity(code: str, language: str) -> dict:
    system = """Phân tích độ phức tạp thuật toán và trả về JSON:
{"algorithm": "...", "time_complexity": "O(...)", "space_complexity": "O(...)", "explanation": "..."}"""
    user = f"""Ngôn ngữ: {language}
```{language}
{code}
```
Trả về JSON hợp lệ."""
    result = _call(system, user, temperature=0.1)
    try:
        match = re.search(r'\{.*\}', result, re.DOTALL)
        return json.loads(match.group()) if match else {"time_complexity": "?", "space_complexity": "?", "explanation": result}
    except Exception:
        return {"time_complexity": "?", "space_complexity": "?", "explanation": result}


def generate_flowchart(code: str, language: str) -> str:
    system = """Tạo Mermaid flowchart từ code. QUY TẮC:
1. KHÔNG viết graph TD, markdown, ```mermaid.
2. Chỉ trả về các dòng flowchart.
3. Node dùng A[Text] hoặc B{Condition}.
4. KHÔNG dùng ký tự: ( ) " ' : ;
5. Text trong node chỉ dùng a-z A-Z 0-9 space + - * / < > =
6. Edge dùng --> hoặc -->|Yes| hoặc -->|No|
7. Node ID ngắn A-Z hoặc AA-AZ."""
    user = f"""```{language}
{code}
```"""
    raw = _call(system, user, temperature=0.1, max_tokens=800)
    # Clean and wrap
    lines = ["graph TD"]
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("graph") or line.startswith("```"):
            continue
        line = line.replace(";", "").replace("(", "[").replace(")", "]")
        line = re.sub(r'["\':()]', '', line)
        lines.append("    " + line)
    return "\n".join(lines)


def generate_testcases(problem_description: str, examples: list) -> list:
    system = """Tạo test cases cho bài lập trình. Trả về JSON array:
[{"input": "...", "expected_output": "...", "type": "happy_path|boundary|corner|stress"}]
Tạo đủ 4 loại: happy path, boundary (min/max), corner cases, stress test."""
    user = f"""Đề bài: {problem_description}
Ví dụ có sẵn: {json.dumps(examples, ensure_ascii=False)}
Tạo 8-10 test case đa dạng. Trả về JSON array hợp lệ."""
    result = _call(system, user, temperature=0.3, max_tokens=1500)
    try:
        match = re.search(r'\[.*\]', result, re.DOTALL)
        return json.loads(match.group()) if match else []
    except Exception:
        return []


def explain_success(code: str, language: str, problem_description: str,
                    user_time: str, user_space: str, optimal_time: str, optimal_space: str) -> str:
    system = """Bạn là mentor lập trình. Khi sinh viên làm đúng, hãy:
1. Giải thích tư duy giải thuật của họ
2. So sánh với cách tối ưu hơn (nếu có)
3. Đề xuất cải tiến
Viết bằng tiếng Việt, thân thiện, khuyến khích."""
    user = f"""Đề bài: {problem_description}
Code của sinh viên ({language}):
```{language}
{code}
```
Độ phức tạp của sinh viên: Time={user_time}, Space={user_space}
Độ phức tạp tối ưu: Time={optimal_time}, Space={optimal_space}"""
    return _call(system, user, temperature=0.4, max_tokens=600)


def parse_syllabus(text: str) -> list:
    system = """Phân tích đề cương học phần lập trình và trích xuất danh sách chủ đề. Trả về JSON array:
[{"name": "...", "description": "...", "subtopics": ["...", "..."], "difficulty": "easy|medium|hard"}]"""
    user = f"""Đề cương:
{text[:4000]}

Trả về JSON array các chủ đề chính. JSON hợp lệ."""
    result = _call(system, user, temperature=0.2, max_tokens=1500)
    try:
        match = re.search(r'\[.*\]', result, re.DOTALL)
        return json.loads(match.group()) if match else []
    except Exception:
        return []


def parse_problem_from_text(text: str) -> dict:
    system = """Đọc đề bài lập trình và trích xuất thông tin. Trả về JSON:
{
  "title": "...",
  "description": "...",
  "difficulty": "easy|medium|hard",
  "tags": ["..."],
  "examples": [{"input": "...", "output": "...", "explanation": "..."}],
  "constraints": "...",
  "time_limit": 2.0,
  "memory_limit": 256
}"""
    user = f"""Đề bài:
{text[:3000]}

Trả về JSON hợp lệ."""
    result = _call(system, user, temperature=0.1, max_tokens=1200)
    try:
        match = re.search(r'\{.*\}', result, re.DOTALL)
        return json.loads(match.group()) if match else {}
    except Exception:
        return {}
