import os
import requests
from PyPDF2 import PdfReader

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.environ.get("OLLAMA_MODEL", "mistral")


def call_ollama(prompt: str) -> str:
    """Call a local Ollama model (for example mistral or llama3)."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
            },
            timeout=300,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except Exception as e:
        return f"[AI error] Could not reach local model: {e}"


def extract_text_from_pdf(path: str, max_pages: int = 8) -> str:
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages):
        if i >= max_pages:
            break
        pages.append(page.extract_text() or "")
    text = "\n\n".join(pages)
    if len(reader.pages) > max_pages:
        text += "\n\n[Note: PDF truncated to first few pages for faster processing.]"
    return text


def generate_text_from_prompt(prompt: str) -> str:
    return call_ollama(prompt)


def generate_from_pdf(path: str, instruction: str) -> str:
    text = extract_text_from_pdf(path)
    prompt = f"""You will receive study material extracted from a PDF.

Instruction: {instruction}

PDF content:
{text}

Now follow the instruction carefully and produce a helpful answer for a student.
"""
    return generate_text_from_prompt(prompt)
