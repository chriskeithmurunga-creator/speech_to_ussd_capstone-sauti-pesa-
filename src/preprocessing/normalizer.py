"""Text normalization for Swahili slang, typos, and ASR output."""

import csv
import os


def load_slang_dictionary(csv_path):
    """Load slang-to-corrected mapping from CSV."""
    mapping = {}
    with open(csv_path, "r") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) >= 2 and row[0].strip():
                mapping[row[0].strip().lower()] = row[1].strip().lower()
    return mapping


def normalize_text(text, slang_dict):
    """Normalize transcribed text by replacing slang/typos."""
    words = text.lower().split()
    corrected = [slang_dict.get(w, w) for w in words]
    return " ".join(corrected)


def clean_asr_output(text):
    """Basic cleanup of ASR output (extra spaces, punctuation)."""
    import re
    text = re.sub(r"\s+", " ", text).strip()
    return text