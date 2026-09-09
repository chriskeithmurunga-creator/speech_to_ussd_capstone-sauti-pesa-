"""
Two-stage Whisper fine-tuning.

Stage 1:
    Fine-tune openai/whisper-large on a general Swahili speech dataset.

Stage 2:
    Continue fine-tuning the Stage-1 checkpoint on natural WhatsApp
    recordings.

Examples
--------

Stage 1:

    python -m src.asr.finetune_whisper \
        --stage 1 \
        --csv data/processed/cleaned_speech_transcripts.csv \
        --output-dir models/whisper_swahili \
        --epochs 3 \
        --batch-size 1

Stage 2:

    python -m src.asr.finetune_whisper \
        --stage 2 \
        --csv data/processed/naturalvoice/metadata.csv \
        --base-model models/whisper_swahili \
        --output-dir models/whisper_finetuned \
        --epochs 2 \
        --batch-size 1
"""

import argparse
from pathlib import Path

import pandas as pd
import torch
from datasets import Audio, Dataset
from transformers import (
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    WhisperForConditionalGeneration,
    WhisperProcessor,
)


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# small is CPU-friendly; use large only with a strong GPU
DEFAULT_BASE_MODEL = "openai/whisper-small"

DEFAULT_STAGE1_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "cleaned_speech_transcripts.csv"
)

DEFAULT_STAGE2_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "naturalvoice"
    / "metadata.csv"
)

DEFAULT_STAGE1_OUTPUT = (
    PROJECT_ROOT / "models" / "whisper_swahili"
)

DEFAULT_STAGE2_OUTPUT = (
    PROJECT_ROOT / "models" / "whisper_finetuned"
)


# ============================================================
# DATA LOADING
# ============================================================

def load_dataframe(
    csv_path: Path,
    stage: int,
    sample: int | None = None,
) -> pd.DataFrame:
    """
    Load and validate the dataset CSV.

    Stage 1 expects:
        resampled_audio_path
        transcript

    Stage 2 expects:
        audio
        transcript
    """

    if not csv_path.exists():
        raise FileNotFoundError(
            f"\nDataset not found:\n{csv_path}\n"
        )

    print(f"Loading dataset: {csv_path}")

    df = pd.read_csv(csv_path)

    print(f"Columns found: {list(df.columns)}")
    print(f"Rows found: {len(df)}")

    # --------------------------------------------------------
    # Stage 1
    # --------------------------------------------------------

    if stage == 1:

        required = [
            "resampled_audio_path",
            "transcript",
        ]

        missing = [
            column
            for column in required
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Stage 1 dataset is missing columns: {missing}"
            )

        df = df[
            df["transcript"].notna()
            & (
                df["transcript"]
                .astype(str)
                .str.strip()
                != ""
            )
        ].copy()

        df = df[
            df["resampled_audio_path"].notna()
            & (
                df["resampled_audio_path"]
                .astype(str)
                .str.strip()
                != ""
            )
        ].copy()

        df = df.rename(
            columns={
                "resampled_audio_path": "audio"
            }
        )

    # --------------------------------------------------------
    # Stage 2
    # --------------------------------------------------------

    elif stage == 2:

        required = [
            "audio",
            "transcript",
        ]

        missing = [
            column
            for column in required
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Stage 2 dataset is missing columns: {missing}"
            )

        df = df[
            df["transcript"].notna()
            & (
                df["transcript"]
                .astype(str)
                .str.strip()
                != ""
            )
        ].copy()

        df = df[
            df["audio"].notna()
            & (
                df["audio"]
                .astype(str)
                .str.strip()
                != ""
            )
        ].copy()

    else:
        raise ValueError("stage must be 1 or 2")

    # --------------------------------------------------------
    # Resolve audio paths
    # --------------------------------------------------------

    def resolve_audio_path(audio_path):
        path = Path(str(audio_path))

        if path.is_absolute():
            return str(path)

        # First try relative to project root.
        project_path = PROJECT_ROOT / path

        if project_path.exists():
            return str(project_path)

        # Then try relative to CSV directory.
        csv_path_candidate = csv_path.parent / path

        if csv_path_candidate.exists():
            return str(csv_path_candidate)

        # Return project-relative path even if it does not
        # currently exist. Validation happens below.
        return str(project_path)

    df["audio"] = df["audio"].apply(resolve_audio_path)

    # --------------------------------------------------------
    # Remove missing audio files
    # --------------------------------------------------------

    before = len(df)

    df = df[
        df["audio"].apply(
            lambda path: Path(path).exists()
        )
    ].copy()

    removed = before - len(df)

    if removed:
        print(
            f"Removed {removed} rows with missing audio files."
        )

    # --------------------------------------------------------
    # Optional sampling
    # --------------------------------------------------------

    if sample is not None:

        if sample <= 0:
            raise ValueError(
                "--sample must be greater than 0"
            )

        if sample < len(df):
            df = df.sample(
                n=sample,
                random_state=42,
            )

    df = df.reset_index(drop=True)

    print(f"Valid rows: {len(df)}")

    if len(df) == 0:
        raise ValueError(
            "No valid audio/transcript pairs were found."
        )

    return df


# ============================================================
# DATASET PREPARATION
# ============================================================

def prepare_dataset(
    df: pd.DataFrame,
    processor: WhisperProcessor,
) -> Dataset:
    """
    Convert the pandas dataframe into a Hugging Face Dataset
    and extract Whisper input features and labels.
    """

    dataset = Dataset.from_pandas(
        df[["audio", "transcript"]],
        preserve_index=False,
    )

    dataset = dataset.cast_column(
        "audio",
        Audio(sampling_rate=16000),
    )

    def prepare_example(example):

        audio = example["audio"]

        input_features = processor.feature_extractor(
            audio["array"],
            sampling_rate=audio["sampling_rate"],
        ).input_features[0]

        labels = processor.tokenizer(
            example["transcript"]
        ).input_ids

        return {
            "input_features": input_features,
            "labels": labels,
        }

    dataset = dataset.map(
        prepare_example,
        remove_columns=dataset.column_names,
    )

    return dataset


# ============================================================
# DATA COLLATOR
# ============================================================

class DataCollatorSpeechSeq2Seq:
    """
    Pads Whisper input features and labels to the same length.
    """

    def __init__(self, processor):
        self.processor = processor
        self.processor.feature_extractor

    def __call__(self, features):

        input_features = [
            {
                "input_features": feature["input_features"]
            }
            for feature in features
        ]

        batch = self.processor.feature_extractor.pad(
            input_features,
            return_tensors="pt",
        )

        label_features = [
            {
                "input_ids": feature["labels"]
            }
            for feature in features
        ]

        labels_batch = self.processor.tokenizer.pad(
            label_features,
            return_tensors="pt",
        )

        labels = labels_batch["input_ids"]

        # Replace padding tokens with -100 so that they
        # are ignored by the loss function.
        labels = labels.masked_fill(
            labels_batch.attention_mask.ne(1),
            -100,
        )

        # Remove BOS token if it is already present.
        if (
            labels.shape[1] > 0
            and torch.all(
                labels[:, 0]
                == self.processor.tokenizer.bos_token_id
            )
        ):
            labels = labels[:, 1:]

        batch["labels"] = labels

        return batch


# ============================================================
# TRAINING
# ============================================================

def train_whisper(
    dataset: Dataset,
    base_model: str,
    output_dir: Path,
    processor: WhisperProcessor,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    gradient_accumulation_steps: int,
    save_steps: int,
    logging_steps: int,
):
    """
    Fine-tune Whisper on the supplied dataset.
    """

    print()
    print("=" * 60)
    print("Loading Whisper model")
    print("=" * 60)
    print(f"Base model: {base_model}")

    model = WhisperForConditionalGeneration.from_pretrained(
        base_model
    )

    # --------------------------------------------------------
    # Swahili ASR configuration
    # --------------------------------------------------------

    model.generation_config.language = "swahili"
    model.generation_config.task = "transcribe"

    model.config.forced_decoder_ids = None

    # --------------------------------------------------------
    # Data collator
    # --------------------------------------------------------

    data_collator = DataCollatorSpeechSeq2Seq(
        processor
    )

    # --------------------------------------------------------
    # Training arguments
    # --------------------------------------------------------

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    use_fp16 = (
        torch.cuda.is_available()
        and torch.cuda.get_device_capability(0)[0] >= 7
    )

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(output_dir),

        num_train_epochs=epochs,

        per_device_train_batch_size=batch_size,

        gradient_accumulation_steps=(
            gradient_accumulation_steps
        ),

        learning_rate=learning_rate,

        warmup_steps=500,

        logging_steps=logging_steps,

        save_steps=save_steps,

        save_total_limit=2,

        fp16=use_fp16,

        gradient_checkpointing=True,

        predict_with_generate=False,

        remove_unused_columns=False,

        report_to="none",

        dataloader_num_workers=2,

        load_best_model_at_end=False,
    )

    # --------------------------------------------------------
    # Trainer
    # --------------------------------------------------------

    trainer = Seq2SeqTrainer(
        args=training_args,
        model=model,
        train_dataset=dataset,
        data_collator=data_collator,
        processing_class=processor,
    )

    print()
    print("=" * 60)
    print("Starting training")
    print("=" * 60)

    trainer.train()

    # --------------------------------------------------------
    # Save final model
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("Saving model")
    print("=" * 60)

    trainer.save_model(str(output_dir))

    processor.save_pretrained(
        str(output_dir)
    )

    print(f"Model saved to: {output_dir}")


# ============================================================
# ARGUMENT PARSER
# ============================================================

def parse_args():
    """
    Parse command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description="Two-stage Whisper fine-tuning"
    )

    parser.add_argument(
        "--stage",
        type=int,
        choices=[1, 2],
        required=True,
        help="Fine-tuning stage: 1 or 2",
    )

    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Path to dataset CSV",
    )

    parser.add_argument(
        "--base-model",
        type=str,
        default=None,
        help=(
            "Base Whisper model or Stage-1 checkpoint. "
            "Required for Stage 2 unless default is used."
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory where the fine-tuned model is saved.",
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs.",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Training batch size per GPU.",
    )

    parser.add_argument(
        "--learning-rate",
        type=float,
        default=1e-5,
        help="Learning rate.",
    )

    parser.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        default=1,
        help="Gradient accumulation steps.",
    )

    parser.add_argument(
        "--save-steps",
        type=int,
        default=500,
        help="Save checkpoint every N steps.",
    )

    parser.add_argument(
        "--logging-steps",
        type=int,
        default=10,
        help="Log training information every N steps.",
    )

    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help=(
            "Optional number of examples to use. "
            "Useful for testing the pipeline."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Validate dataset + model paths and print the prepared "
            "dataset size without running training."
        ),
    )

    return parser.parse_args()


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    """
    Main program entry point.
    """

    args = parse_args()

    # --------------------------------------------------------
    # Select stage-specific defaults
    # --------------------------------------------------------

    if args.stage == 1:

        csv_path = (
            args.csv
            if args.csv is not None
            else DEFAULT_STAGE1_CSV
        )

        base_model = (
            args.base_model
            if args.base_model is not None
            else DEFAULT_BASE_MODEL
        )

        output_dir = (
            args.output_dir
            if args.output_dir is not None
            else DEFAULT_STAGE1_OUTPUT
        )

    else:

        csv_path = (
            args.csv
            if args.csv is not None
            else DEFAULT_STAGE2_CSV
        )

        base_model = (
            args.base_model
            if args.base_model is not None
            else str(DEFAULT_STAGE1_OUTPUT)
        )

        output_dir = (
            args.output_dir
            if args.output_dir is not None
            else DEFAULT_STAGE2_OUTPUT
        )

    # --------------------------------------------------------
    # Print configuration
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("WHISPER FINE-TUNING")
    print("=" * 60)

    print(f"Stage:          {args.stage}")
    print(f"Dataset:        {csv_path}")
    print(f"Base model:     {base_model}")
    print(f"Output:         {output_dir}")
    print(f"Epochs:         {args.epochs}")
    print(f"Batch size:     {args.batch_size}")
    print(f"Learning rate:  {args.learning_rate}")
    print("=" * 60)

    # --------------------------------------------------------
    # Validate Stage 2 base model
    # --------------------------------------------------------

    if args.stage == 2:

        base_model_path = Path(base_model)

        if (
            not base_model_path.exists()
            and "/" not in base_model
        ):
            raise FileNotFoundError(
                "\nStage 2 requires the Stage 1 checkpoint.\n"
                f"Expected checkpoint: {base_model_path}\n"
                "\nRun Stage 1 first or provide --base-model."
            )

    # --------------------------------------------------------
    # Load dataframe
    # --------------------------------------------------------

    df = load_dataframe(
        csv_path=csv_path,
        stage=args.stage,
        sample=args.sample,
    )

    # --------------------------------------------------------
    # Load processor
    # --------------------------------------------------------

    print()
    print("Loading Whisper processor...")

    processor = WhisperProcessor.from_pretrained(
        base_model,
        language="swahili",
        task="transcribe",
    )

    # --------------------------------------------------------
    # Prepare dataset
    # --------------------------------------------------------

    print()
    print("Preparing audio dataset...")

    dataset = prepare_dataset(
        df=df,
        processor=processor,
    )

    print(f"Prepared examples: {len(dataset)}")

    # --------------------------------------------------------
    # Dry run: stop before training
    # --------------------------------------------------------

    if args.dry_run:
        print()
        print("=" * 60)
        print("DRY RUN — validation passed")
        print("=" * 60)
        print(f"Dataset rows : {len(df)}")
        print(f"Examples     : {len(dataset)}")
        print(f"Base model   : {base_model}")
        print(f"Output dir   : {output_dir}")
        print("No training was run. Remove --dry-run to train.")
        return

    # --------------------------------------------------------
    # Train
    # --------------------------------------------------------

    train_whisper(
        dataset=dataset,
        base_model=base_model,
        output_dir=output_dir,
        processor=processor,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        gradient_accumulation_steps=(
            args.gradient_accumulation_steps
        ),
        save_steps=args.save_steps,
        logging_steps=args.logging_steps,
    )

    print()
    print("=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Model: {output_dir}")


# ============================================================
# PYTHON ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
