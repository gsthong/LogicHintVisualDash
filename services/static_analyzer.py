"""
Static Code Analyzer — extracted từ GNN notebook (train_logic_hint__thông_.ipynb).

Chạy KHÔNG cần PyTorch/torch_geometric — dùng heuristic thuần Python
(same logic as GNN post-processing layer: compute_tle_risk, hint_level_*, BugDetector).

Khi có model file (ai_ide_model.pt) thì dùng GNN thật.
Khi không có → fallback heuristic (vẫn rất tốt cho MVP).
"""
import re
import os
from typing import Optional

# ─── Heuristic analyzer (always available) ────────────────────────────────────

def analyze_cpp_static(code: str) -> dict:
    """Parse C++ code → structural features. Extracted from notebook cell 4."""
    tokens = re.findall(r'\w+|\{|\}', code)
    brace_depth = 0
    loop_depth = 0
    max_loop_depth = 0
    total_loops = 0
    total_calls = 0
    total_branches = 0
    recursion = 0
    func_match = re.search(r'\b(\w+)\s*\(', code)
    func_name = func_match.group(1) if func_match else None
    keywords = {"for", "while", "if", "switch", "return"}

    for i, tok in enumerate(tokens):
        if tok in ["for", "while"]:
            loop_depth += 1
            total_loops += 1
            max_loop_depth = max(max_loop_depth, loop_depth)
        elif tok == "{":
            brace_depth += 1
        elif tok == "}":
            brace_depth = max(0, brace_depth - 1)
            if loop_depth > 0:
                loop_depth -= 1
        elif tok in ["if", "switch"]:
            total_branches += 1
        elif re.match(r'^[A-Za-z_]\w*$', tok) and i + 1 < len(tokens) and tokens[i+1] == "(":
            total_calls += 1
            if func_name and tok == func_name:
                recursion = 1

    complexity_class = min(max_loop_depth, 3)
    return {
        "complexity_class": complexity_class,
        "max_loop_depth":   max_loop_depth,
        "total_loops":      total_loops,
        "total_branches":   total_branches,
        "total_calls":      total_calls,
        "recursion":        recursion,
        "token_count":      len(tokens),
    }


def compute_tle_risk(loop_depth: int, total_loops: int, token_count: int, recursion: int) -> float:
    risk = 0.0
    risk += loop_depth * 0.3
    risk += min(total_loops / 5, 1) * 0.2
    risk += min(token_count / 200, 1) * 0.2
    if recursion:
        risk += 0.3
    return round(min(risk, 1.0), 3)


def hint_level_1(loop_depth: int, recursion: int, branches: int) -> str:
    if recursion:
        return "Phát hiện đệ quy. Kiểm tra base case và tránh stack overflow."
    if loop_depth >= 2:
        return "Vòng lặp lồng nhau phát hiện. Xem xét độ phức tạp thời gian."
    if branches > 5:
        return "Nhiều nhánh điều kiện. Kiểm tra logic rẽ nhánh cẩn thận."
    return "Cấu trúc đơn giản. Kiểm tra edge cases (mảng rỗng, giá trị âm, trùng lặp)."


def hint_level_2(loop_depth: int, total_loops: int, token_count: int) -> str:
    if loop_depth == 3:
        return "Độ sâu vòng lặp = 3 → O(n³). Nguy cơ TLE cao. Tìm cách giảm xuống O(n²) hoặc O(n log n)."
    if loop_depth == 2:
        return "Độ sâu vòng lặp = 2 → O(n²). Nếu n lớn, cân nhắc dùng hash map hoặc two pointers."
    if token_count > 300:
        return "Code dài, logic phức tạp. Tách hàm nhỏ hơn và kiểm tra từng phần."
    return "Độ phức tạp có vẻ ổn. Tập trung vào tính đúng đắn của thuật toán."


def hint_level_3(loop_depth: int, recursion: int) -> str:
    if recursion and loop_depth >= 1:
        return "Đệ quy + vòng lặp → cân nhắc memoization hoặc quy hoạch động (DP) để tránh tính lại."
    if loop_depth >= 2:
        return "Thử: prefix sum, hash map, two pointers, hoặc sắp xếp trước để giảm độ phức tạp."
    return "Tập trung vào điều kiện biên và constraint đầu vào."


def generate_skill_profile(loop_depth: int, recursion: int, branches: int) -> dict:
    return {
        "loop_skill":      max(0, 3 - loop_depth),
        "recursion_skill": 0 if recursion else 1,
        "branch_skill":    max(0, 5 - branches),
    }


def recommend_problem(skill_profile: dict) -> str:
    if skill_profile["loop_skill"] == 0:
        return "Luyện tập bài tối ưu vòng lặp lồng nhau (Two Sum, Matrix problems)."
    if skill_profile["recursion_skill"] == 0:
        return "Luyện tập đệ quy và quy hoạch động (Fibonacci, Coin Change, Tree traversal)."
    if skill_profile["branch_skill"] == 0:
        return "Luyện tập xử lý điều kiện và edge case (Binary Search, Valid Parentheses)."
    return "Thử bài tổng hợp nhiều kỹ thuật (Graph, DP, Sliding Window)."


# ─── Bug Detector (from notebook cell 14) ─────────────────────────────────────

class BugDetector:
    def detect(self, code: str) -> list:
        results = []
        lines = code.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()

            # Off-by-one
            if re.search(r'for\s*\(.*<=.*;', stripped):
                results.append({
                    "line": i + 1,
                    "type": "off_by_one",
                    "message": "Vòng lặp dùng <= có thể gây lỗi off-by-one.",
                    "fix": "Kiểm tra lại: dùng < thay vì <= nếu duyệt n phần tử."
                })

            # Infinite loop
            if "while(true)" in stripped and "break" not in code:
                results.append({
                    "line": i + 1,
                    "type": "infinite_loop",
                    "message": "while(true) không có break → vòng lặp vô hạn.",
                    "fix": "Thêm điều kiện break hoặc đổi sang while(condition)."
                })

            # Uninitialized variable
            if re.search(r'\bint\s+\w+\s*;', stripped) and "=" not in stripped:
                results.append({
                    "line": i + 1,
                    "type": "uninitialized_var",
                    "message": "Biến khai báo không khởi tạo → giá trị rác.",
                    "fix": "Khởi tạo: int x = 0;"
                })

            # Array index without bounds check
            if re.search(r'\w+\[.*\]', stripped) and "size" not in code and ".length" not in code:
                if "n" in stripped and stripped.count("[") > 0:
                    results.append({
                        "line": i + 1,
                        "type": "potential_oob",
                        "message": "Truy cập mảng không kiểm tra bounds → có thể out-of-bounds.",
                        "fix": "Đảm bảo index trong phạm vi [0, n-1]."
                    })

        return results


# ─── Full analyzer (combines all) ─────────────────────────────────────────────

bug_detector = BugDetector()

def full_analyze(code: str, language: str = "cpp") -> dict:
    """
    One-stop function: gọi từ AI router.
    Returns complete analysis: TLE risk, hints, bugs, skill profile.
    """
    if language != "cpp":
        # Python heuristic (lighter)
        lines = code.split("\n")
        indent_depth = max(
            (len(l) - len(l.lstrip())) // 4
            for l in lines if l.strip()
        ) if lines else 0
        has_recursion = any(
            re.search(r'def\s+(\w+).*:', l) and
            re.search(r'\1\s*\(', code)
            for l in lines
        )
        return {
            "tle_risk": round(min(indent_depth * 0.25, 1.0), 3),
            "complexity_class": min(indent_depth, 3),
            "hints": {
                "level_1": f"Độ sâu indent = {indent_depth} → kiểm tra vòng lặp lồng nhau.",
                "level_2": "Cân nhắc dùng dict/set thay vì list lồng nhau.",
                "level_3": "Thử list comprehension hoặc generator để tối ưu memory.",
            },
            "bugs": bug_detector.detect(code),
            "skill_profile": {"loop_skill": max(0, 3-indent_depth), "recursion_skill": 1, "branch_skill": 2},
            "recommendation": "Luyện thêm bài về Python optimization.",
        }

    feat = analyze_cpp_static(code)
    tle = compute_tle_risk(feat["max_loop_depth"], feat["total_loops"], feat["token_count"], feat["recursion"])
    profile = generate_skill_profile(feat["max_loop_depth"], feat["recursion"], feat["total_branches"])

    # TLE risk label
    if tle >= 0.7:
        tle_label = "🔴 Cao"
    elif tle >= 0.4:
        tle_label = "🟡 Trung bình"
    else:
        tle_label = "🟢 Thấp"

    return {
        "tle_risk":        tle,
        "tle_label":       tle_label,
        "complexity_class": feat["complexity_class"],
        "max_loop_depth":  feat["max_loop_depth"],
        "recursion":       bool(feat["recursion"]),
        "hints": {
            "level_1": hint_level_1(feat["max_loop_depth"], feat["recursion"], feat["total_branches"]),
            "level_2": hint_level_2(feat["max_loop_depth"], feat["total_loops"], feat["token_count"]),
            "level_3": hint_level_3(feat["max_loop_depth"], feat["recursion"]),
        },
        "bugs":            bug_detector.detect(code),
        "skill_profile":   profile,
        "recommendation":  recommend_problem(profile),
        "stats": {
            "token_count":    feat["token_count"],
            "total_loops":    feat["total_loops"],
            "total_branches": feat["total_branches"],
            "total_calls":    feat["total_calls"],
        },
    }
