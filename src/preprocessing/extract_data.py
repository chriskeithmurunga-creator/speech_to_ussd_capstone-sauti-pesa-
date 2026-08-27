import csv
import os
import shutil
import tarfile
import wave
from pathlib import Path


def check_wav_properties(file_path: Path) -> dict:
    """Validates WAV file integrity and retrieves audio metadata using standard wave module."""
    try:
        with wave.open(str(file_path), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            frames = wf.getnframes()
            duration = frames / float(sample_rate) if sample_rate > 0 else 0.0

            is_valid = channels > 0 and sample_rate > 0 and frames > 0
            return {
                "is_valid": is_valid,
                "channels": channels,
                "sample_width": sample_width,
                "sample_rate": sample_rate,
                "duration_sec": round(duration, 3),
                "error": "",
            }
    except Exception as e:
        return {
            "is_valid": False,
            "channels": 0,
            "sample_width": 0,
            "sample_rate": 0,
            "duration_sec": 0.0,
            "error": str(e),
        }


def extract_archive(tar_path: Path, extract_dir: Path):
    """Extracts the tar.bz2 archive to a temporary extraction folder."""
    print(f"Extracting {tar_path} to {extract_dir}...")
    with tarfile.open(tar_path, "r:bz2") as tar:
        tar.extractall(path=extract_dir)
    print("Extraction complete.")


def collect_transcripts_from_prompt_file(prompt_file: Path) -> dict:
    """Parses standard ALFFA/Kaldi 'PROMPT_SPEECH' or 'prompts.txt' files."""
    transcripts = {}
    if not prompt_file.is_file():
        return transcripts

    with open(prompt_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                file_id, text = parts
                transcripts[file_id] = text
    return transcripts


def process_dataset(archive_path: str, output_audio_dir: str, csv_output_path: str):
    archive_path = Path(archive_path)
    output_audio_dir = Path(output_audio_dir)
    csv_output_path = Path(csv_output_path)

    temp_extract_dir = archive_path.parent / "temp_extracted"
    output_audio_dir.mkdir(parents=True, exist_ok=True)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Extract tar.bz2 archive
    extract_archive(archive_path, temp_extract_dir)

    audio_file_map = {}
    transcripts_map = {}

    # 2. Traverse extracted folder to index audio files and parse transcripts
    print("Indexing audio files and collecting transcripts...")
    for root, _, files in os.walk(temp_extract_dir):
        root_path = Path(root)
        for file in files:
            file_path = root_path / file

            if file.lower().endswith((".wav", ".flac", ".mp3", ".sph")):
                stem = file_path.stem
                dest_path = output_audio_dir / file
                file_path.rename(dest_path)
                audio_file_map[stem] = dest_path.name

            elif file.lower() in ["prompt_speech", "prompts.txt", "text", "transcripts.txt"]:
                parsed = collect_transcripts_from_prompt_file(file_path)
                transcripts_map.update(parsed)

            elif file.lower().endswith(".txt"):
                stem = file_path.stem
                with open(file_path, "r", encoding="utf-8") as tf:
                    transcripts_map[stem] = tf.read().strip()

    # 3. Validate audio files and create paired CSV dataset
    print(f"Validating audio files and writing dataset to {csv_output_path}...")
    valid_count = 0

    with open(csv_output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow([
            "file_id", "audio_path", "transcript", 
            "is_valid", "channels", "sample_rate", 
            "duration_sec", "error"
        ])

        for stem, audio_filename in sorted(audio_file_map.items()):
            audio_full_path = output_audio_dir / audio_filename
            transcript = transcripts_map.get(stem, "")
            audio_rel_path = str(Path("data/raw/audio") / audio_filename)

            val_meta = check_wav_properties(audio_full_path)

            writer.writerow([
                stem, audio_rel_path, transcript,
                val_meta["is_valid"], val_meta["channels"],
                val_meta["sample_rate"], val_meta["duration_sec"],
                val_meta["error"]
            ])

            if val_meta["is_valid"]:
                valid_count += 1

    print(f"Done! Successfully processed and validated {valid_count}/{len(audio_file_map)} audio files.")

    if temp_extract_dir.exists():
        shutil.rmtree(temp_extract_dir)


if __name__ == "__main__":
    ARCHIVE_FILE = "data/raw/data_broadcastnews_sw.tar.bz2"
    AUDIO_DEST_DIR = "data/raw/audio"
    CSV_DEST_FILE = "data/raw/transcripts.csv"

    process_dataset(ARCHIVE_FILE, AUDIO_DEST_DIR, CSV_DEST_FILE)