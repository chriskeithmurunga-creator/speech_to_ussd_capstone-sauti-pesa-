import os
from pathlib import Path
import librosa
import pandas as pd
import soundfile as sf
from tqdm import tqdm

TARGET_SAMPLE_RATE = 16000  # 16 kHz Mono


def resample_audio_file(
    input_path: Path, output_path: Path, target_sr: int = TARGET_SAMPLE_RATE
) -> bool:
    """Loads audio, enforces mono channel, resamples to 16kHz, and exports as 16-bit PCM WAV."""
    try:
        audio, sr = librosa.load(input_path, sr=target_sr, mono=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, audio, target_sr, subtype="PCM_16")
        return True
    except Exception as e:
        print(f"\n[Error] Failed processing {input_path.name}: {e}")
        return False


def locate_audio_file(audio_dir: Path, file_id: str, rel_path: str) -> Path:
    """Checks data/raw/audio for exact matches across common audio formats."""
    # Check exact relative path or filename inside audio_dir
    for ref in [rel_path, file_id]:
        if not ref:
            continue
        clean_name = Path(ref).name
        candidate = audio_dir / clean_name
        if candidate.exists() and candidate.is_file():
            return candidate

        # Fallback search across standard extensions
        stem = Path(clean_name).stem
        for ext in [".wav", ".mp3", ".flac", ".ogg", ".m4a"]:
            candidate = audio_dir / f"{stem}{ext}"
            if candidate.exists() and candidate.is_file():
                return candidate

    return None


def batch_resample_dataset(
    audio_dir: Path, proc_audio_dir: Path, transcripts_csv: Path
) -> pd.DataFrame:
    if not transcripts_csv.exists():
        raise FileNotFoundError(
            f"Transcripts index not found at {transcripts_csv}"
        )

    df = pd.read_csv(transcripts_csv)
    proc_audio_dir.mkdir(parents=True, exist_ok=True)

    resampled_paths = []
    success_flags = []

    print(f"Target Directory : {audio_dir}")
    print(
        f"Processing {len(df)} audio files -> Target: {TARGET_SAMPLE_RATE}Hz Mono WAV..."
    )

    missing_count = 0
    for idx, row in tqdm(df.iterrows(), total=len(df)):
        file_id = str(row.get("file_id", "")) if pd.notna(row.get("file_id")) else ""
        rel_path = (
            str(row.get("audio_path", ""))
            if pd.notna(row.get("audio_path"))
            else ""
        )

        input_path = locate_audio_file(audio_dir, file_id, rel_path)

        if input_path is None:
            missing_count += 1
            if missing_count == 1:
                print(
                    f"\n[Warning] Sample missing file check -> ID: '{file_id}', Path: '{rel_path}'"
                )
            success_flags.append(False)
            resampled_paths.append("")
            continue

        output_path = proc_audio_dir / f"{input_path.stem}_16k.wav"
        success = resample_audio_file(
            input_path, output_path, TARGET_SAMPLE_RATE
        )

        success_flags.append(success)
        resampled_paths.append(str(output_path) if success else "")

    df["resampled_audio_path"] = resampled_paths
    df["is_resampled_16k"] = success_flags

    updated_csv_path = proc_audio_dir.parent / "cleaned_speech_transcripts.csv"
    df.to_csv(updated_csv_path, index=False)

    print(
        f"\nAudio Preprocessing Summary:"
        f"\n* Resampled successfully : {sum(success_flags)} / {len(df)} files"
        f"\n* Unresolved/Missing     : {missing_count} files"
        f"\n* Output Folder          : {proc_audio_dir}"
        f"\n* Metadata Index Updated : {updated_csv_path}"
    )

    return df


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    AUDIO_DIR = PROJECT_ROOT / "data" / "raw" / "audio"
    PROC_AUDIO_DIR = PROJECT_ROOT / "data" / "processed" / "audio_16k"

    # Search for transcripts CSV in data/raw or data/metadata
    TRANSCRIPTS_CSV = PROJECT_ROOT / "data" / "raw" / "transcripts.csv"
    if not TRANSCRIPTS_CSV.exists():
        TRANSCRIPTS_CSV = PROJECT_ROOT / "data" / "metadata" / "transcripts.csv"

    batch_resample_dataset(AUDIO_DIR, PROC_AUDIO_DIR, TRANSCRIPTS_CSV)