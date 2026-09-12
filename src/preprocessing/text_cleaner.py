import csv
import re
import string
from pathlib import Path


# Common Whisper transcription mistakes
WHISPER_CORRECTIONS = {
    "nanteka": "nataka",
    "silinki": "shilingi",
    "eftano": "elfu tano",
    "kojon": "kwa john",
}


# Base monetary & financial Sheng terms
BASE_FINANCIAL_MAP = {
    "chapaa soo tano": "500",
    "soo tano": "500",
    "soo mbili": "200",
    "soo moja": "100",
    "elfu moja": "1000",
    "elfu mbili": "2000",
    "elfu tatu": "3000",
    "elfu nne": "4000",
    "elfu tano": "5000",
    "elfu sita": "6000",
    "elfu saba": "7000",
    "elfu nane": "8000",
    "elfu tisa": "9000",
    "elfu kumi": "10000",
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
    """Load CSV slang lookup table and merge it with base terms."""

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
                        val = (
                            str(corrected).strip().lower()
                            if corrected
                            else ""
                        )

                        if key:
                            slang_map[key] = val

        except Exception as e:
            print(
                f"Warning: Could not load slang CSV from "
                f"{csv_path}: {e}"
            )

    return slang_map


ACTIVE_SLANG_MAP = load_combined_slang_map()


def export_slang_map_to_csv(csv_path: Path = None):
    """Write all active slang dictionary terms to the CSV file."""

    if csv_path is None:
        csv_path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "slang_dictionary"
            / "swahili_slang_typos.csv"
        )

    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(
        csv_path,
        mode="w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=["slang", "corrected"],
        )

        writer.writeheader()

        for slang, corrected in sorted(
            ACTIVE_SLANG_MAP.items()
        ):
            writer.writerow(
                {
                    "slang": slang,
                    "corrected": corrected,
                }
            )

    print(
        f"Successfully updated CSV with "
        f"{len(ACTIVE_SLANG_MAP)} terms at: {csv_path}"
    )


def clean_swahili_text(text: str) -> str:
    """
    Normalize Swahili, Sheng, English, and common
    Whisper transcription mistakes.
    """

    if not isinstance(text, str) or not text.strip():
        return ""

    # Convert to lowercase
    text = text.lower()

    # Correct common Whisper transcription mistakes
    sorted_corrections = sorted(
        WHISPER_CORRECTIONS.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for wrong, correct in sorted_corrections:
        text = re.sub(
            r"\b" + re.escape(wrong) + r"\b",
            correct,
            text,
        )

    # Apply slang dictionary
    sorted_keys = sorted(
        ACTIVE_SLANG_MAP.keys(),
        key=len,
        reverse=True,
    )

    for slang in sorted_keys:
        replacement = ACTIVE_SLANG_MAP[slang]

        text = re.sub(
            r"\b" + re.escape(slang) + r"\b",
            replacement,
            text,
        )

    # Remove punctuation
    text = text.translate(
        str.maketrans("", "", string.punctuation)
    )

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


if __name__ == "__main__":
    export_slang_map_to_csv()

