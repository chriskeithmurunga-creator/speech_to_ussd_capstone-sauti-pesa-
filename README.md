


# Speech-to-USSD

A speech-to-USSD pipeline that converts Swahili voice commands into USSD menu navigation.  
Built for mobile money services (M-Pesa) in East Africa.


## Pipeline

Audio → ASR (Whisper) → Normalize → Intent Classification → Slot Extraction → USSD Response



<img width="1536" height="1024" alt="WhatsApp Image 2026-08-24 at 17 43 02" src="https://github.com/user-attachments/assets/ea8c0ac2-b7cf-4507-86e4-238862e1c6ab" />


## Team — Sauti Pesa
Built as a group capstone for the Moringa School Data Science program (Cohort DSF-FT16).

- **Steve Mose** — Integration & Backend (Team Lead)
- **Damaris Mbaluka** ([@MACRINA-yea](https://github.com/MACRINA-yea)) — Business Understanding
- **Vivian Ochieng** ([@Vivian-Xy](https://github.com/Vivian-Xy)) — Data & Voice Processing
- **Joy Seneyian** ([@seneyianjoy-bit](https://github.com/seneyianjoy-bit)) — Data Preprocessing
- **Keith Chris Murunga** ([@chriskeithmurunga-creator](https://github.com/chriskeithmurunga-creator)) — ASR & Intent Classification
- **Lyne Chesergon** ([@chesergon](https://github.com/chesergon)) — USSD Mapping

### My contribution (Keith)
I built the NLP/intent classification component: engineered features from the normalized transcripts, trained and compared four models (Logistic Regression, Decision Tree, Random Forest, MLP), evaluated them by F1 score and confusion matrix, and selected the best-performing model. Full workflow in `notebooks/` and `models/intent_classifier/`.



## Project Structure

```
speech-to-ussd/
├── data/               # Raw audio, transcripts, processed CSVs, slang dictionary
├── models/             # Trained intent classifiers and embeddings
├── src/                # Source code
│   ├── audio/          # Recording
│   ├── asr/            # Whisper transcription
│   ├── preprocessing/  # Text normalization
│   ├── intent/         # Feature extraction, training, prediction
│   ├── slots/          # Entity extraction
│   └── ussd/           # Menu templates and response generation
├── app/                # CLI interface
├── tests/              # Test suite
└── main.py             # Entry point
```

## Usage

```bash
pip install -r requirements.txt

# Run on an audio file
python main.py --audio sample.wav
```

### Voice recording (microphone)

```bash
# Record a voice command and run the full pipeline
python main.py --record

# Record for longer (e.g. 8 seconds)
python main.py --record --duration 8
```

### Run from text (skip ASR)

```bash
python main.py --text "send 5000 to john"
```

### Voice traceability

Every run is saved to `data/traces/<run_id>/` with the audio clip, the Whisper
**transcript**, the normalized text, intent, extracted slots, and the final
USSD output. To inspect them:

```bash
python main.py --traces          # list runs
python main.py --trace <run_id>  # view one run as JSON

# Open the browser UI: list runs, play your voice clip, see the transcript
python main.py --serve
# then open http://127.0.0.1:8000
```

### Fine-tuning Whisper on Swahili voice data

First preprocess the raw audio (Vivian's `audio_preprocessor.py`) so
`data/processed/cleaned_speech_transcripts.csv` exists, then:

```bash
# Quick sanity check (validates data + inputs only)
python -m src.asr.finetune_whisper --dry-run

# Real fine-tune (CPU-friendly: whisper-tiny, 3 epochs)
python -m src.asr.finetune_whisper --epochs 3
```

The checkpoint is saved to `models/whisper_finetuned/` and is loaded
automatically by the pipeline. If it is absent, the pipeline falls back to
the base `openai/whisper-tiny` model.
