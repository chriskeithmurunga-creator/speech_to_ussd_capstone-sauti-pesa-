# Speech-to-USSD

A speech-to-USSD pipeline that converts Swahili voice commands into USSD menu navigation.  
Built for mobile money services (M-Pesa) in East Africa.

## Pipeline

Audio → ASR (Whisper) → Normalize → Intent Classification → Slot Extraction → USSD Response

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
python main.py --audio sample.wav
```