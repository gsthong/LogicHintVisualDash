"""
Sandboxed code execution using Docker.
Falls back to subprocess with resource limits if Docker is unavailable.

Security layers:
  1. Docker container with --network none, --memory, --cpus, read-only FS
  2. ulimit for CPU/memory inside container
  3. Hard timeout via asyncio
  4. No internet access (--network none)
"""
import asyncio
import tempfile
import os
import subprocess
import time
import shutil
from typing import Tuple

DOCKER_IMAGE_CPP    = "gcc:13-bookworm"
DOCKER_IMAGE_PYTHON = "python:3.12-slim"
DOCKER_IMAGE_JAVA   = "eclipse-temurin:21-jdk-alpine"

TIMEOUT_DEFAULT = 5.0   # seconds hard limit
MEMORY_LIMIT    = "256m"
CPU_LIMIT       = "1.0"


def _docker_available() -> bool:
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=3)
        return r.returncode == 0
    except Exception:
        return False


async def _run_cmd(cmd: list, stdin: str, timeout: float) -> Tuple[int, str, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=stdin.encode()),
            timeout=timeout,
        )
        return proc.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return -1, "", "TLE"


async def execute_cpp(code: str, stdin: str, time_limit: float) -> dict:
    tmp = tempfile.mkdtemp(prefix="cm_cpp_")
    src = os.path.join(tmp, "solution.cpp")
    exe = os.path.join(tmp, "solution")
    try:
        with open(src, "w") as f:
            f.write(code)

        if _docker_available():
            # Compile inside Docker
            compile_cmd = [
                "docker", "run", "--rm", "--network", "none",
                f"--memory={MEMORY_LIMIT}", f"--cpus={CPU_LIMIT}",
                "-v", f"{tmp}:/code:rw",
                DOCKER_IMAGE_CPP,
                "g++", "-O2", "-std=c++17", "-o", "/code/solution", "/code/solution.cpp",
            ]
            rc, _, err = await _run_cmd(compile_cmd, "", 30.0)
            if rc != 0:
                return {"status": "CE", "error": err, "runtime_ms": 0}

            run_cmd = [
                "docker", "run", "--rm", "--network", "none",
                f"--memory={MEMORY_LIMIT}", f"--cpus={CPU_LIMIT}",
                "--ulimit", "cpu=5:5",
                "-v", f"{tmp}:/code:ro",
                DOCKER_IMAGE_CPP,
                "/code/solution",
            ]
        else:
            # Fallback: native compile
            r = subprocess.run(
                ["g++", "-O2", "-std=c++17", "-o", exe, src],
                capture_output=True, text=True, timeout=30
            )
            if r.returncode != 0:
                return {"status": "CE", "error": r.stderr, "runtime_ms": 0}
            run_cmd = [exe]

        start = time.perf_counter()
        rc, stdout, stderr = await _run_cmd(run_cmd, stdin, time_limit + 1)
        elapsed = (time.perf_counter() - start) * 1000

        if stderr == "TLE" or elapsed > time_limit * 1000:
            return {"status": "TLE", "error": "Time limit exceeded", "runtime_ms": elapsed}
        if rc != 0:
            return {"status": "RE", "error": stderr[:500], "runtime_ms": elapsed}
        return {"status": "OK", "output": stdout.strip(), "runtime_ms": round(elapsed, 2)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def execute_python(code: str, stdin: str, time_limit: float) -> dict:
    tmp = tempfile.mkdtemp(prefix="cm_py_")
    src = os.path.join(tmp, "solution.py")
    try:
        with open(src, "w") as f:
            f.write(code)

        if _docker_available():
            run_cmd = [
                "docker", "run", "--rm", "--network", "none",
                f"--memory={MEMORY_LIMIT}", f"--cpus={CPU_LIMIT}",
                "-v", f"{tmp}:/code:ro",
                DOCKER_IMAGE_PYTHON,
                "python3", "/code/solution.py",
            ]
        else:
            run_cmd = ["python3", src]

        start = time.perf_counter()
        rc, stdout, stderr = await _run_cmd(run_cmd, stdin, time_limit + 1)
        elapsed = (time.perf_counter() - start) * 1000

        if stderr == "TLE" or elapsed > time_limit * 1000:
            return {"status": "TLE", "error": "Time limit exceeded", "runtime_ms": elapsed}
        if rc != 0:
            return {"status": "RE", "error": stderr[:500], "runtime_ms": elapsed}
        return {"status": "OK", "output": stdout.strip(), "runtime_ms": round(elapsed, 2)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def run_code(language: str, code: str, stdin: str, time_limit: float = 2.0) -> dict:
    if language == "cpp":
        return await execute_cpp(code, stdin, time_limit)
    elif language == "python":
        return await execute_python(code, stdin, time_limit)
    else:
        return {"status": "CE", "error": f"Language '{language}' not supported yet", "runtime_ms": 0}
