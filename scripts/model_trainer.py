import glob
import os

import dill as pickle
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from utilities.card_data import CardTypes
from utilities.feature_extractors import (
    extract_color_features,
    extract_difference_of_histograms_features,
)


def load_dataset(glob_pattern: str) -> list[np.ndarray]:
    """Return all the data and labels together, based on the specified file pattern"""
    dataset = []
    all_labels = []

    for filepath in glob.iglob(glob_pattern):
        print(f"Loading {filepath}...")
        local_data = pickle.load(open(filepath, "rb"))
        data, labels = local_data["data"], local_data["labels"]
        dataset.append(data)
        all_labels.append(labels)

    dataset = np.concatenate(dataset, axis=0)
    all_labels = np.concatenate(all_labels, axis=0)

    return dataset, all_labels


def load_card_type_features() -> list[np.ndarray]:
    """Load all available data inside the 'data/' directory"""

    dataset, all_labels = load_dataset("data/*card_types*")

    # Load the features
    card_features = extract_color_features(images=dataset, type="median")

    return card_features, all_labels


def load_card_merges_features() -> list[np.ndarray]:
    """Load all available data corresponding to card merges, and extract their features"""

    dataset, all_labels = load_dataset("data/*merges*")

    # Extract all the features from `dataset`, now of shape (batch, 2, height, width, 3)
    features = extract_difference_of_histograms_features(dataset)

    return features, all_labels


def explore_features(features, labels: list[CardTypes], label_type: CardTypes):
    """Explore the features for specific labels, for debugging..."""

    print(f"Features for all cards that are {label_type.name}:")

    labels_int = np.array([label.value for label in labels])
    print(features[labels_int == label_type.value])


def train_knn(X: np.ndarray, labels: np.ndarray[CardTypes]) -> KNeighborsClassifier:
    """Train a K-NN classifier on the card types"""

    # Split the data
    labels_values = [label.value for label in labels]
    X_train, X_test, y_train, y_test = train_test_split(X, labels_values, test_size=0.2, stratify=labels_values)

    # Create the K-NN model
    k = 3  # Choose the number of neighbors
    knn = KNeighborsClassifier(n_neighbors=k)

    # Train the model
    knn.fit(X_train, y_train)

    # Test the model
    test_card_types_model(knn, X_test, y_test)

    return knn


def train_logistic_regressor(X: np.ndarray, labels: np.ndarray):
    """Train a model to identify card merges"""

    # Split the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, labels, test_size=0.2, stratify=labels)

    # Train the logistic regression model
    logistic_regressor = LogisticRegression(max_iter=1000)
    logistic_regressor.fit(X_train, y_train)

    # Test the model
    test(logistic_regressor, X_test, y_test)

    return logistic_regressor


def test(model: KNeighborsClassifier | LogisticRegression, X_test: np.ndarray, y_test: np.ndarray):
    """Test a generic pre-trained model.

    Args:
        X_test (np.ndarray): Array of already extracted test features.
        y_test (np.ndarray): Array of test labels.
    """

    # Compute predictions
    y_pred = model.predict(X_test)

    # Compute test accuracy
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Accuracy: {accuracy * 100:.2f}%")

    if accuracy < 1:
        print("Classification Report:")
        print(classification_report(y_test, y_pred))

    return y_pred


def test_card_types_model(knn_model: KNeighborsClassifier | LogisticRegression, X_test: np.ndarray, y_test: np.ndarray):
    """Test a trained K-NN model for distinguishing card types"""

    y_pred_int = test(knn_model, X_test, y_test)

    # Convert integer predictions back to enum
    y_pred_enum = np.array([CardTypes(pred) for pred in y_pred_int])
    y_test_enum = np.array([CardTypes(pred) for pred in y_test])

    # Display predictions with enum labels
    predictions = zip(y_test_enum, y_pred_enum)
    print("\nActual vs Predicted misclassified labels:")
    for i, (actual, predicted) in enumerate(predictions):
        if actual.name != predicted.name:
            print(f"Actual: {actual.name}, Predicted: {predicted.name}, Features: {X_test[i]}")


def save_model(model: KNeighborsClassifier | LogisticRegression, filename: str):
    """Save the model in file"""
    model_path = os.path.join("models", f"{filename}")
    with open(model_path, "wb") as pfile:
        pickle.dump(model, pfile)

    print(f"Model saved in '{model_path}'")


def train_card_types_model():
    """Train a K-NN model to distinguis between card types"""
    features, labels = load_card_type_features()
    knn_model = train_knn(X=features, labels=labels)

    # Explore some features
    # explore_features(features=features, labels=labels, label_type=CardTypes.STANCE)

    # Save the trained model
    save_model(knn_model, filename="card_type_predictor.knn")


def train_card_merges_model():
    """Train a model that identifies when two cards are going to merge"""

    features, labels = load_card_merges_features()
    model = train_logistic_regressor(X=features, labels=labels)
    save_model(model, filename="card_merges_predictor.lr")


def main():

    # For card types
    train_card_types_model()

    # For card merges
    # train_card_merges_model()

    return


if __name__ == "__main__":
    main()
