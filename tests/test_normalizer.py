"""Tests for normalizer module."""

from src.preprocessing.normalizer import load_slang_dictionary, normalize_text, clean_asr_output


def test_load_slang_dictionary():
    import os
    path = "data/slang_dictionary/swahili_slang_typos.csv"
    if os.path.exists(path):
        mapping = load_slang_dictionary(path)
        assert isinstance(mapping, dict)


def test_normalize_text():
    mapping = {"niko": "nina"}
    result = normalize_text("niko", mapping)
    assert result == "nina"


def test_clean_asr_output():
    result = clean_asr_output("  hello   world  ")
    assert result == "hello world"