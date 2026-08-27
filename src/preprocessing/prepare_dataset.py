import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from text_cleaner import clean_swahili_text


def load_and_audit_data(project_root: Path):
    """Loads resampled speech transcripts and synthetic intent dataset, performing quality checks."""
    speech_csv = project_root / "data" / "processed" / "cleaned_speech_transcripts.csv"
    synthetic_csv = project_root / "data" / "metadata" / "synthetic_intent_dataset.csv"

    # 1. Load Speech Data
    if not speech_csv.exists():
        raise FileNotFoundError(f"Run audio_preprocessor.py first. Missing: {speech_csv}")
    
    df_speech = pd.read_csv(speech_csv)
    # Filter only successfully resampled audio files
    df_speech_valid = df_speech[df_speech["is_resampled_16k"] == True].copy()
    
    # Clean text transcripts using text_cleaner logic
    df_speech_valid["clean_transcript"] = df_speech_valid["transcript"].apply(clean_swahili_text)
    df_speech_valid["is_synthetic"] = False

    # Standardize columns
    speech_data = df_speech_valid[[
        "file_id", "transcript", "clean_transcript", "resampled_audio_path", "is_synthetic"
    ]].rename(columns={"resampled_audio_path": "audio_path"})

    # 2. Load Synthetic NLU Data
    if not synthetic_csv.exists():
        raise FileNotFoundError(f"Run augment_text.py first. Missing: {synthetic_csv}")
        
    df_syn = pd.read_csv(synthetic_csv)
    df_syn["clean_transcript"] = df_syn["transcript"].apply(clean_swahili_text)
    df_syn["audio_path"] = ""  # Text-only entries

    print("=== DATA UNDERSTANDING & AUDIT ===")
    print(f"* Total Resampled Speech Audio Clips : {len(speech_data)}")
    print(f"* Total Synthetic NLU Text Samples  : {len(df_syn)}")
    print(f"* Intent Class Distribution:\n{df_syn['intent'].value_counts().to_string()}\n")

    return speech_data, df_syn


def create_stratified_splits(df_syn: pd.DataFrame, output_dir: Path, random_seed: int = 42):
    """Splits synthetic NLU data into train (80%), val (10%), and test (10%) splits with stratified intents."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # First split: 80% train, 20% temp (val + test)
    train_df, temp_df = train_test_split(
        df_syn, test_size=0.20, random_state=random_seed, stratify=df_syn["intent"]
    )

    # Second split: Split remaining 20% into equal 10% val and 10% test
    val_df, test_df = train_test_split(
        temp_df, test_size=0.50, random_state=random_seed, stratify=temp_df["intent"]
    )

    # Save splits
    train_df.to_csv(output_dir / "intent_train.csv", index=False)
    val_df.to_csv(output_dir / "intent_val.csv", index=False)
    test_df.to_csv(output_dir / "intent_test.csv", index=False)

    print("=== DATA ENGINEERING SPLITS CREATED ===")
    print(f"* Train set : {len(train_df)} rows -> {output_dir / 'intent_train.csv'}")
    print(f"* Val set   : {len(val_df)} rows   -> {output_dir / 'intent_val.csv'}")
    print(f"* Test set  : {len(test_df)} rows  -> {output_dir / 'intent_test.csv'}")


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

    speech_df, syn_df = load_and_audit_data(PROJECT_ROOT)
    create_stratified_splits(syn_df, PROCESSED_DIR)