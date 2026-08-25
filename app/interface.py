"""Command-line interface for the speech-to-USSD system."""

from src.pipeline import run_pipeline


def cli():
    """Simple CLI for testing the pipeline."""
    import argparse
    parser = argparse.ArgumentParser(description="Speech-to-USSD Pipeline")
    parser.add_argument("--audio", required=True, help="Path to audio file")
    parser.add_argument("--slang-dict", default="data/slang_dictionary/swahili_slang_typos.csv",
                        help="Path to slang dictionary CSV")
    parser.add_argument("--model", default="logistic_regression", help="Model name")
    args = parser.parse_args()

    result = run_pipeline(args.audio, args.slang_dict, args.model)
    print(result["ussd_menu"])