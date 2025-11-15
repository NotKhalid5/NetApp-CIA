import os
import re
import mimetypes
from datetime import datetime
import concurrent.futures
import chardet
from langdetect import detect_langs
from langcodes import Language
from magika import Magika  # AI-powered file classification


# ----------------------------
#   PII Detection Patterns
# ----------------------------
PII_PATTERNS = {
    "ssn_us": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(
        r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b"
    ),
    "ip_v4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(
        r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b"
    ),
    "dob": re.compile(r"\b(?:\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b"),
    "routing_account": re.compile(r"\b(?:Acct|Account|Account Number|Routing|ABA)\b", re.I),
    "password_label": re.compile(r"\b(password|passwd|pwd|contraseña|clave)\b", re.I),
    "spanish_cc_label": re.compile(r"\b(tarjeta|numero de tarjeta|número de tarjeta)\b", re.I),
    "spanish_ssn_label": re.compile(r"\b(NSS|dni|cedula|rut)\b", re.I),
    "student_id": re.compile(r"\b(?:S\d{5,9}|ID[:\s]?\d{5,9})\b", re.I),
}


# ----------------------------
#   Helper Functions
# ----------------------------
def detect_language(text: str) -> str:
    """Detect dominant language for text preview."""
    try:
        langs = detect_langs(text)
        if not langs:
            return "Unknown"
        top = langs[0]
        code = top.lang
        name = Language.get(code).display_name()
        return f"{name} ({code})"
    except Exception:
        return "Unknown"


def safe_read(file_path: str, max_bytes: int = 20000):
    """Safely read partial file data to avoid large memory use."""
    try:
        with open(file_path, "rb") as f:
            raw = f.read(max_bytes)
        enc = chardet.detect(raw).get("encoding") or "utf-8"
        text = raw.decode(enc, errors="ignore")
        return text, enc
    except Exception:
        return "[Unreadable or binary data]", "Unknown"


def find_pii(preview_text: str) -> list:
    """Search text for PII-like patterns."""
    found = []
    for key, pattern in PII_PATTERNS.items():
        if pattern.search(preview_text):
            found.append(key)
    return found


# ----------------------------
#   File Analyzer
# ----------------------------
def analyze_single_file(file_path: str) -> dict:
    """Analyze one file with Magika AI + PII scanning."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Initialize Magika within this process
        magika = Magika()
        ai_result = magika.identify_path(file_path)
        output = ai_result.output

        mime = getattr(output, "mime_type", None) or mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        category = getattr(output, "category", None) or "Unknown"
        confidence = getattr(output, "confidence", 0.99) * 100
    except Exception as e:
        return {
            "file_name": os.path.basename(file_path),
            "mime_type": "error",
            "ai_category": "Processing Failed",
            "confidence": "0%",
            "encoding": "N/A",
            "language": "Unknown",
            "flagged": False,
            "flag_reasons": [f"Magika error: {str(e)}"],
            "preview": "[Error analyzing file]",
            "uploaded": timestamp,
        }

    ext = os.path.splitext(file_path)[1].lower()

    flagged = False
    flag_reasons = []
    encoding = "N/A"
    language = "N/A"
    preview = "[Skipped: non-text or non-pdf file]"

    # Only analyze readable files (TXT or PDF)
    if mime in ["application/pdf", "text/plain"] or ext in [".pdf", ".txt"]:
        preview, encoding = safe_read(file_path)
        language = detect_language(preview)
        pii_matches = find_pii(preview)

        # Extra contextual patterns
        personal_info_patterns = {
            "person_name": r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",
            "address": r"\b\d{1,5}\s[A-Za-z0-9\s]+(Street|St|Ave|Avenue|Blvd|Road|Rd|Lane|Ln)\b",
            "bank_account": r"\b\d{9,18}\b",
        }

        for label, pattern in personal_info_patterns.items():
            if re.search(pattern, preview):
                pii_matches.append(label)

        if pii_matches:
            flagged = True
            flag_reasons = list(set(pii_matches))

    return {
        "file_name": os.path.basename(file_path),
        "mime_type": mime,
        "ai_category": category,
        "file_type": ext.lstrip(".") or "unknown",
        "encoding": encoding,
        "language": language,
        "file_size": f"{os.path.getsize(file_path)} bytes",
        "confidence": f"{confidence:.2f}%",
        "uploaded": timestamp,
        "preview": preview[:5000].strip(),
        "flagged": flagged,
        "flag_reasons": flag_reasons,
    }


# ----------------------------
#   Scalable Batch Processor
# ----------------------------
def classify_files_batch(file_paths: list) -> list:
    """Process multiple files concurrently using ProcessPoolExecutor for CPU-bound operations."""
    results = []

    with concurrent.futures.ProcessPoolExecutor() as executor:
        future_to_path = {executor.submit(analyze_single_file, path): path for path in file_paths}

        for future in concurrent.futures.as_completed(future_to_path):
            path = future_to_path[future]
            try:
                results.append(future.result())
            except Exception as e:
                results.append({
                    "file_name": os.path.basename(path),
                    "mime_type": "error",
                    "ai_category": "Processing Failed",
                    "confidence": "0%",
                    "encoding": "N/A",
                    "language": "Unknown",
                    "flagged": False,
                    "flag_reasons": [f"Worker error: {str(e)}"],
                    "preview": "[Error analyzing file]",
                    "uploaded": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })

    return results
