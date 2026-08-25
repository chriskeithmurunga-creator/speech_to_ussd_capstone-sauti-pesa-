"""Intent prediction using trained classifiers."""

import joblib
import os


def load_model(model_name, model_dir="models/intent_classifier"):
    """Load a trained classifier."""
    path = os.path.join(model_dir, f"{model_name}.pkl")
    return joblib.load(path)


def predict_intent(text, model, vectorizer):
    """Predict intent for a given text."""
    features = vectorizer.transform([text])
    pred = model.predict(features)[0]
    proba = model.predict_proba(features).max() if hasattr(model, "predict_proba") else None
    return pred, proba