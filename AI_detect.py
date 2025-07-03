# ai_text_detector.py

"""
A script to analyze documents for AI authorship likelihood using OpenAI.
Supports PDF, DOCX, Markdown, and TXT files.
"""
import os
import sys
import math
import argparse
import json

# (Optional) from dotenv import load_dotenv
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        pass

# Ensure 'requests' is available
try:
    import requests
except ImportError:
    print("Error: 'requests' library not installed. Install with 'pip install requests'.", file=sys.stderr)
    sys.exit(1)

from docx import Document
import PyPDF2


def extract_text(path: str) -> str:
    """
    Extract text from PDF, DOCX, MD, or TXT files.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        text_chunks = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text_chunks.append(page_text)
        return "\n".join(text_chunks)

    elif ext == ".docx":
        doc = Document(path)
        return "\n".join([p.text for p in doc.paragraphs])

    elif ext in (".md", ".markdown", ".txt"):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    else:
        raise ValueError(f"Unsupported file type: {ext}")


def detect_ai(text: str, api_key: str) -> dict:
    """
    Send text to OpenAI detection model and return verdict and confidence.
    """
    url = "https://api.openai.com/v1/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "model-detect-v2",
        "prompt": text.strip() + "\n</s><|disc_score|>",
        "max_tokens": 1,
        "temperature": 0,
        "logprobs": 5,
        "stop": ["\n"],
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()
    top_logprob = data["choices"][0]["logprobs"]["top_logprobs"][0].get("</s>", 0)
    prob = math.exp(top_logprob)
    confidence = 100 * (1 - prob)
    verdict = "likely AI-generated" if confidence > 50 else "unlikely AI-generated"
    return {"verdict": verdict, "confidence": round(confidence, 2)}


def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is missing.", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Analyze documents for likelihood of AI authorship."
    )
    parser.add_argument(
        "files",
        nargs='+',
        help="Paths to one or more PDF, DOCX, MD, or TXT files."
    )
    args = parser.parse_args()

    results = []
    for path in args.files:
        if not os.path.isfile(path):
            print(f"Warning: File not found: {path}", file=sys.stderr)
            continue
        try:
            text = extract_text(path)
            result = detect_ai(text, api_key)
            results.append({"file": os.path.basename(path), **result})
        except Exception as e:
            print(f"Error processing {path}: {e}", file=sys.stderr)

    print(json.dumps({"analysis": results}, indent=2))


if __name__ == "__main__":
    main()
