import csv
import re
import string
from pathlib import Path

# Base monetary & financial Sheng terms
BASE_FINANCIAL_MAP = {
    "chapaa soo tano": "500",
    "soo tano": "500",
    "soo mbili": "200",
    "soo moja": "100",
    "elfu mbili": "2000",
    "elfu moja": "1000",
    "fifty bob": "50",
    "bob mbao": "20",
    "chapaa": "money",
    "ganji": "money",
    "punch": "100",
    "ngiri": "1000",
    "mbao": "20",
    "soo": "100",
    "chali yangu": "friend",
    "brathe": "brother",
    "mathe": "mother",
    "shosh": "grandmother",
    "mzee": "father",
    "sis": "sister",
    "kredit": "airtime",
    "salio": "balance",
    "mb": "bundles",
    "nitumie": "tuma",
    "tumia": "tuma",
}


def load_combined_slang_map(csv_path: Path = None) -> dict:
    """Loads CSV slang lookup table using built-in csv module and merges with base terms."""
    slang_map = BASE_FINANCIAL_MAP.copy()

    if csv_path is None:
        csv_path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "slang_dictionary"
            / "swahili_slang_typos.csv"
        )

    if csv_path.exists():
        try:
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    slang = row.get("slang")
                    corrected = row.get("corrected")
                    if slang:
                        key = str(slang).strip().lower()
                        val = str(corrected).strip().lower() if corrected else ""
                        if key:
                            slang_map[key] = val
        except Exception as e:
            print(f"Warning: Could not load slang CSV from {csv_path}: {e}")

    return slang_map


ACTIVE_SLANG_MAP = load_combined_slang_map()


def export_slang_map_to_csv(csv_path: Path = None):
    """Writes all active slang dictionary terms directly into the CSV file."""
    if csv_path is None:
        csv_path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "slang_dictionary"
            / "swahili_slang_typos.csv"
        )

    csv_path.parent.mkdir(parents=True, exist_ok=True)

    # Write merged terms back to CSV
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["slang", "corrected"])
        writer.writeheader()
        for slang, corrected in sorted(ACTIVE_SLANG_MAP.items()):
            writer.writerow({"slang": slang, "corrected": corrected})

    print(f"Successfully updated CSV with {len(ACTIVE_SLANG_MAP)} terms at: {csv_path}")


def clean_swahili_text(text: str) -> str:
    """Normalizes Swahili, Sheng, and English text using the active slang dictionary."""
    if not isinstance(text, str) or not text.strip():
        return ""

    text = text.lower()
    sorted_keys = sorted(ACTIVE_SLANG_MAP.keys(), key=len, reverse=True)

    for slang in sorted_keys:
        replacement = ACTIVE_SLANG_MAP[slang]
        text = re.sub(r"\b" + re.escape(slang) + r"\b", replacement, text)

    text = text.translate(str.maketrans("", "", string.punctuation))
    return re.sub(r"\s+", " ", text).strip()


if __name__ == "__main__":
    export_slang_map_to_csv()