"""Feature extraction for intent classification."""

from sklearn.feature_extraction.text import TfidfVectorizer


def extract_features(texts, vectorizer=None, fit=True):
    """Convert text into TF-IDF feature vectors."""
    if vectorizer is None:
        vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
    if fit:
        features = vectorizer.fit_transform(texts)
    else:
        features = vectorizer.transform(texts)
    return features, vectorizer