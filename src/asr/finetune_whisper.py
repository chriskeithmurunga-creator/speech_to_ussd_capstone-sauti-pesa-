"""Fine-tune Whisper on the Swahili speech dataset.

Input:  data/processed/cleaned_speech_transcripts.csv  (produced by
        src/preprocessing/audio_preprocessor.py — Vivian's pipeline)
Output: models/whisper_finetuned/  (HF checkpoint used by src/asr/whisper.py)

Example:
    python -m src.asr.finetune_whisper --dry-run        # quick sanity check
    python -m src.asr.finetune_whisper --epochs 5       # real fine-tune
"""

import argparse
import os
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = PROJECT_ROOT / "data" / "processed" / "cleaned_speech_transcripts.csv"
OUTPUT_DIR = PROJECT_ROOT / "models" / "whisper_finetuned"
BASE_MODEL = "openai/whisper-tiny"  # tiny is CPU-friendly; use -base for better quality


def load_dataset(csv_path: Path, sample: int | None = None) -> pd.DataFrame:
    """Load the cleaned speech transcripts CSV and filter valid audio rows."""
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Missing {csv_path}. Run src/preprocessing/audio_preprocessor.py first."
        )
    df = pd.read_csv(csv_path)
    df = df[df["is_resampled_16k"] == True].copy()  # noqa: E712 (bool column)
    df = df[df["transcript"].notna() & (df["transcript"].astype(str).str.strip() != "")]
    df = df[df["resampled_audio_path"].notna() & (df["resampled_audio_path"].astype(str) != "")]
    if sample:
        df = df.sample(n=sample, random_state=42)
    return df.reset_index(drop=True)


def prepare_ds_for_finetune(df: pd.DataFrame):
    """Convert the dataframe into HF Dataset objects for Whisper fine-tuning."""
    from datasets import Dataset, Audio

    ds = Dataset.from_pandas(df[["resampled_audio_path", "transcript"]])
    ds = ds.rename_column("resampled_audio_path", "audio")
    ds = ds.rename_column("transcript", "sentence")
    ds = ds.cast_column("audio", Audio(sampling_rate=16000))
    return ds


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Whisper on Swahili speech")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Cleaned transcripts CSV")
    parser.add_argument("--base-model", default=BASE_MODEL, help="HF base Whisper model id")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Where to save the checkpoint")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=8, help="Train batch size")
    parser.add_argument("--lr", type=float, default=1e-5, help="Learning rate")
    parser.add_argument("--sample", type=int, default=None, help="Limit to N rows (debugging)")
    parser.add_argument("--dry-run", action="store_true", help="Validate data + inputs only, no training")
    args = parser.parse_args()

    print(f"Loading dataset from {args.csv}")
    df = load_dataset(args.csv, args.sample)
    print(f"* {len(df)} usable (audio+transcript) clips")

    if args.dry_run:
        print("DRY RUN: preparing HF Dataset...")
        ds = prepare_ds_for_finetune(df)
        print(f"* Dataset ready with {len(ds)} rows")
        print("DRY RUN OK: fine-tune inputs assemble correctly. Run without --dry-run to train.")
        return

    print("Loading base model...")
    from transformers import (
        WhisperForConditionalGeneration,
        WhisperProcessor,
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
    )

    processor = WhisperProcessor.from_pretrained(
        args.base_model, language="sw", task="transcribe"
    )
    model = WhisperForConditionalGeneration.from_pretrained(args.base_model)

    model.config.forced_decoder_ids = None
    model.config.suppress_tokens = []
    model.config.use_cache = False

    ds = prepare_ds_for_finetune(df)

    def prepare(batch):
        audio = [a["array"] for a in batch["audio"]]
        out = processor(audio=audio, sampling_rate=16000, return_tensors="pt")
        batch["input_features"] = out.input_features
        batch["labels"] = processor(
            text=batch["sentence"], return_tensors="pt"
        ).input_ids
        return batch

    ds = ds.map(prepare, remove_columns=ds.column_names, batched=True, batch_size=args.batch_size)
    split = ds.train_test_split(test_size=0.1, seed=42)
    train_ds, eval_ds = split["train"], split["test"]

    args.output_dir.mkdir(parents=True, exist_ok=True)

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(args.output_dir),
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=2,
        learning_rate=args.lr,
        warmup_steps=500,
        num_train_epochs=args.epochs,
        evaluation_strategy="steps",
        eval_steps=100,
        logging_steps=25,
        save_steps=100,
        save_total_limit=2,
        predict_with_generate=True,
        fp16=False,  # CPU-friendly; set True on GPU
        report_to=[],
        push_to_hub=False,
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        tokenizer=processor.feature_extractor,
    )

    trainer.train()
    trainer.save_model(str(args.output_dir))
    processor.save_pretrained(str(args.output_dir))
    print(f"Fine-tuned checkpoint saved to {args.output_dir}")


if __name__ == "__main__":
    main()