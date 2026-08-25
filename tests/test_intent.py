"""Tests for intent module."""

from src.intent.features import extract_features
from src.intent.predict import predict_intent


def test_extract_features():
    texts = ["hello world", "send money"]
    features, vectorizer = extract_features(texts)
    assert features.shape[0] == 2


def test_predict_intent():
    # Placeholder: requires a trained model
    pass