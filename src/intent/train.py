"""Training intent classifiers."""

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score
import os


def train_all(X_train, y_train, X_val, y_val, model_dir="models/intent_classifier"):
    """Train multiple classifiers and save them."""
    models = {
        "logistic_regression": LogisticRegression(max_iter=1000),
        "decision_tree": DecisionTreeClassifier(),
        "random_forest": RandomForestClassifier(),
        "mlp": MLPClassifier(max_iter=1000),
    }

    os.makedirs(model_dir, exist_ok=True)

    for name, model in models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_val)
        acc = accuracy_score(y_val, preds)
        print(f"{name} validation accuracy: {acc:.4f}")
        joblib.dump(model, os.path.join(model_dir, f"{name}.pkl"))

    return models