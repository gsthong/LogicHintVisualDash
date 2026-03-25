"""
OCR Service — tích hợp từ:
  - ocr_sinhtc.py          (Gemini Vision → sinh testcases)
  - chuyen_de_bai_thanh_json.py  (Gemini Vision → JSON đề bài)
  - pdf___đề_bài.ipynb     (EasyOCR + pdfplumber + Groq)

Ưu tiên: Gemini Vision (tốt nhất) → EasyOCR fallback → pdfplumber text layer.
"""
import os
import io
import re
import json
import base64
import requests
from typing import Optional

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")
GEMINI_MODEL   = "gemini-2.5-flash"
GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL     = "llama-3.3-70b-versatile"


# ─── Gemini Vision ─────────────────────────────────────────────────────────────

def _gemini_vision(prompt: str, image_bytes: bytes, mime: str = "image/png") -> str:
    """Call Gemini Vision API with an image."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    b64 = base64.b64encode(image_bytes).decode()
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime, "data": b64}},
            ]
        }],
        "generationConfig": {"temperature": 0.2},
    }
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


# ─── Groq text fallback ────────────────────────────────────────────────────────

def _groq_text(system: str, user: str) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set")
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.1,
        "max_tokens": 2000,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


# ─── PDF text extraction ───────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Try pdfplumber (text layer) first, then EasyOCR on images."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(f"--- Trang {i+1} ---\n{text}")
                    # Also extract tables
                    for j, table in enumerate(page.extract_tables() or []):
                        rows = [" | ".join(str(c or "") for c in row) for row in table if row]
                        if rows:
                            pages.append(f"[Bảng {j+1}]\n" + "\n".join(rows))
            if pages:
                return "\n".join(pages)
    except Exception:
        pass

    # Fallback: EasyOCR on rendered pages
    try:
        import easyocr
        import numpy as np
        from pdf2image import convert_from_bytes
        from PIL import ImageEnhance, Image

        reader = easyocr.Reader(["vi", "en"], gpu=False)
        images = convert_from_bytes(pdf_bytes, dpi=200)
        all_text = []
        for i, img in enumerate(images):
            # Preprocess
            img = img.convert("L")
            img = ImageEnhance.Contrast(img).enhance(2.0)
            img = img.point(lambda x: 0 if x < 140 else 255).convert("RGB")
            result = reader.readtext(np.array(img))
            page_text = "\n".join(t for _, t, conf in result if conf >= 0.4)
            all_text.append(f"--- Trang {i+1} ---\n{page_text}")
        return "\n".join(all_text)
    except Exception as e:
        return f"[OCR failed: {e}]"


def extract_text_from_image(image_bytes: bytes) -> str:
    """OCR an image using EasyOCR."""
    try:
        import easyocr
        import numpy as np
        from PIL import Image, ImageEnhance

        reader = easyocr.Reader(["vi", "en"], gpu=False)
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = img.point(lambda x: 0 if x < 140 else 255).convert("RGB")
        result = reader.readtext(np.array(img))
        return "\n".join(t for _, t, conf in result if conf >= 0.4)
    except Exception as e:
        return f"[OCR failed: {e}]"


# ─── Problem JSON extraction ───────────────────────────────────────────────────

PROBLEM_JSON_PROMPT = """
Bạn là hệ thống trích xuất dữ liệu đề bài lập trình tự động.
Đọc nội dung và trả về JSON CẤU TRÚC CHÍNH XÁC sau:
{
    "title": "Tên bài toán",
    "description": "Mô tả yêu cầu đầy đủ",
    "difficulty": "easy|medium|hard",
    "tags": ["Array", "DP", ...],
    "input_format": "Mô tả định dạng input",
    "output_format": "Mô tả định dạng output",
    "constraints": "Ràng buộc",
    "examples": [
        {"input": "...", "output": "...", "explanation": "..."}
    ],
    "time_limit": 2.0,
    "memory_limit": 256
}
QUY TẮC:
1. CHỈ trả về JSON thuần, KHÔNG markdown, KHÔNG giải thích.
2. GIỮ NGUYÊN chuỗi output (không thêm dấu tiếng Việt).
3. examples phải có ít nhất 1 phần tử.
"""


def image_to_problem_json(image_bytes: bytes, mime: str = "image/png") -> dict:
    """
    From notebook: chuyen_de_bai_thanh_json.py
    Dùng Gemini Vision → extract problem JSON.
    Fallback: EasyOCR + Groq.
    """
    # Try Gemini Vision first
    if GEMINI_API_KEY:
        try:
            raw = _gemini_vision(PROBLEM_JSON_PROMPT, image_bytes, mime)
            raw = raw.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass

    # Fallback: OCR text → Groq
    text = extract_text_from_image(image_bytes)
    return text_to_problem_json(text)


def pdf_to_problem_json(pdf_bytes: bytes) -> dict:
    """
    From notebook: pdf___đề_bài.ipynb
    PDF → text → Groq → problem JSON.
    Also tries Gemini Vision on first page if available.
    """
    # Try Gemini Vision on first page
    if GEMINI_API_KEY:
        try:
            from pdf2image import convert_from_bytes
            import io as _io
            pages = convert_from_bytes(pdf_bytes, dpi=150, first_page=1, last_page=1)
            if pages:
                buf = _io.BytesIO()
                pages[0].save(buf, format="PNG")
                result = image_to_problem_json(buf.getvalue(), "image/png")
                if result.get("title"):
                    return result
        except Exception:
            pass

    # Fallback: extract text → Groq
    text = extract_text_from_pdf(pdf_bytes)
    return text_to_problem_json(text)


def text_to_problem_json(text: str) -> dict:
    """Plain text → Groq → problem JSON."""
    system = PROBLEM_JSON_PROMPT
    user = f"Nội dung đề bài:\n{text[:4000]}"
    try:
        raw = _groq_text(system, user)
        raw = raw.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        return json.loads(match.group()) if match else {"title": "?", "description": text[:500], "examples": []}
    except Exception as e:
        return {"title": "Parse error", "description": str(e), "examples": []}


# ─── Testcase generator (from ocr_sinhtc.py) ──────────────────────────────────

TESTCASE_GEN_PROMPT = """
Bạn là chuyên gia tạo test case cho bài lập trình thi đấu.
Nhiệm vụ: Dựa vào đề bài, tạo Python script sinh testcases tự động.

QUY TẮC:
1. Sinh đủ 4 loại: happy_path, boundary (min/max), corner_case, stress_test.
2. Dùng `sys.stdin` và `sys.stdout` + `with open(...)` để redirect I/O (KHÔNG dùng os.dup/os.dup2).
3. Tạo thư mục 'testcases_output' với 10 file: 01.in, 01.out, ..., 10.in, 10.out.
4. CHỈ trả về Python code thuần, KHÔNG markdown.
"""

def generate_testcase_script(problem_json: dict) -> str:
    """
    From ocr_sinhtc.py: AI sinh Python script tạo testcases.
    """
    problem_text = json.dumps(problem_json, ensure_ascii=False, indent=2)

    if GEMINI_API_KEY:
        try:
            prompt = TESTCASE_GEN_PROMPT + f"\n\nĐề bài:\n{problem_text}"
            # Text-only Gemini call
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3},
            }
            r = requests.post(url, json=payload, timeout=60)
            r.raise_for_status()
            code = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            return code.replace("```python", "").replace("```", "").strip()
        except Exception:
            pass

    # Fallback: Groq
    try:
        code = _groq_text(TESTCASE_GEN_PROMPT, f"Đề bài:\n{problem_text}")
        return code.replace("```python", "").replace("```", "").strip()
    except Exception as e:
        return f"# Error generating testcase script: {e}"


# ─── Testcase JSON list (simpler, direct) ─────────────────────────────────────

def generate_testcases_from_problem(problem_json: dict) -> list:
    """Return list of {input, expected_output, type} — used by AI router."""
    system = """Tạo test cases cho bài lập trình. Trả về JSON array:
[{"input": "...", "expected_output": "...", "type": "happy_path|boundary|corner_case|stress_test"}]
Tạo đủ 4 loại, tổng 8-12 test cases. JSON hợp lệ, không markdown."""
    user = json.dumps(problem_json, ensure_ascii=False)
    try:
        raw = _groq_text(system, user)
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        return json.loads(match.group()) if match else []
    except Exception:
        return []
