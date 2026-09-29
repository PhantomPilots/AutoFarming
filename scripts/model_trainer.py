import os

import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import LeaveOneGroupOut, StratifiedGroupKFold, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from utilities.card_data import CardTypes
from utilities.feature_extractors import (
    extract_color_features,
    extract_color_histograms_features,
    extract_difference_of_histograms_features,
    extract_ground_card_features,
    extract_spatial_color_features,
)
from utilities.artifact_security import dataset_paths, labels_to_numpy_values, load_dataset_file
from utilities.utilities import display_image, load_dataset, save_model


def load_card_type_features() -> tuple[np.ndarray, np.ndarray]:
    """Load all available data inside the 'data/' directory"""

    dataset, all_labels = load_dataset("data/card_types*")

    card_features = extract_spatial_color_features(images=dataset)

    return card_features, all_labels


def load_card_merges_features() -> list[np.ndarray]:
    """Load all available data corresponding to card merges, and extract their features"""

    dataset, all_labels = load_dataset("data/card_merges*")

    # Extract all the features from `dataset`, now of shape (batch, 2, height, width, 3)
    features = extract_difference_of_histograms_features(dataset)

    return features, all_labels


def load_card_slots_features() -> list[np.ndarray]:
    """Load the dataset corresponding to identifying empty and filled card slots"""
    dataset, all_labels = load_dataset("data/card_slots_data*")

    # Extract the features
    features = extract_color_features(images=dataset, type="median")
    return features, all_labels


def load_entire_slot_space_features() -> list[np.ndarray]:
    dataset, all_labels = load_dataset("data/entire_slot_space_data*")

    # Extract the features -- TODO: For this case, we may need a new different set of features
    features = extract_color_features(images=dataset, type="median")
    return features, all_labels


def load_amplify_cards_features() -> list[np.ndarray]:
    """Load the amplify card dataset and extract its features"""
    dataset, all_labels = load_dataset("data/amplify*")

    # Extract the features
    features = extract_color_histograms_features(images=dataset, bins=(8, 8, 8))

    return features, all_labels


def load_HAM_cards_features() -> list[np.ndarray]:
    """Load all the high-hitting dataset"""
    dataset, all_labels = load_dataset("data/ham_cards*")

    # Extract the features
    features = extract_color_histograms_features(images=dataset, bins=(8, 8, 8))

    return features, all_labels


def load_thor_cards_features() -> list[np.ndarray]:
    """Load all the high-hitting dataset"""
    dataset, all_labels = load_dataset("data/thor_cards*")

    # Extract the features
    features = extract_color_histograms_features(images=dataset, bins=(8, 8, 8))

    return features, all_labels


def load_ground_cards_features() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load ground samples and preserve their capture-file groups for validation."""
    batches, labels, file_groups = [], [], []
    for file_index, filepath in enumerate(dataset_paths("data/ground_data*")):
        print(f"Loading {filepath}...")
        batch, batch_labels = load_dataset_file(filepath)
        batches.append(batch)
        labels.append(batch_labels)
        file_groups.extend([file_index] * len(batch_labels))

    return extract_ground_card_features(batches), np.concatenate(labels), np.asarray(file_groups)


def apply_pca_transform(features: np.ndarray, n_components: int) -> tuple[np.ndarray, PCA]:
    """Fit a PCA model and return the reduced features plus the fitted transform."""

    pca_model = PCA(n_components=n_components)
    features_reduced = pca_model.fit_transform(features)

    return features_reduced, pca_model


def load_unit_type_features() -> list[np.ndarray]:
    """We'll use the same features as the card types"""
    dataset, all_labels = load_dataset("data/unit_type*")

    card_features = extract_color_histograms_features(images=dataset, bins=(4, 4, 4))

    return card_features, all_labels


def explore_features(features, labels: list[CardTypes], label_type: CardTypes):
    """Explore the features for specific labels, for debugging..."""

    print(f"Features for all cards that are {label_type.name}:")

    labels_int = np.array([label.value for label in labels])
    print(features[labels_int == label_type.value])


def train_knn(X: np.ndarray, labels: np.ndarray[CardTypes], k: int = 3) -> KNeighborsClassifier:
    """Train a K-NN classifier on the card types"""

    # Train the model till we get a good enough one
    acc = 0
    num_trials = 0
    print("Training K-NN model...")
    while acc < 0.99 and num_trials < 20:
        # Split the data
        X_train, X_test, y_train, y_test = train_test_split(X, labels, test_size=0.2, stratify=labels)
        # Create the K-NN model
        knn = KNeighborsClassifier(n_neighbors=k)
        # Train the model
        knn.fit(X_train, y_train)
        # Test the model
        _, acc = test_model(knn, X_test, y_test)

        # Increment the number of trials...
        num_trials += 1

    print(f"Found a model after {num_trials} trial(s).")

    # After validating that we have enough data, fit all the data into the model
    knn.fit(X, labels)

    return knn


def train_svm_classifier(X: np.ndarray, labels: np.ndarray) -> SVC:
    """Train a Support Vector Machine classifier"""

    # Train the model till we get a good enough one
    acc = 0
    num_trials = 0
    print("Training SVM model...")
    while acc < 0.995 and num_trials < 20:
        # Split the data into training and testing sets
        X_train, X_test, y_train, y_test = train_test_split(X, labels, test_size=0.2, stratify=labels)

        # Create and train the SVM model with RBF kernel
        svm_model = SVC(kernel="rbf")
        svm_model.fit(X_train, y_train)

        # Test the model
        _, acc = test_model(svm_model, X_test, y_test)

        # Increment the number of trials
        num_trials += 1

    print(f"Found a good SVM model after {num_trials} trial(s).")
    return svm_model


def train_logistic_regressor(X: np.ndarray, labels: np.ndarray) -> LogisticRegression:
    """Train a model to identify card merges"""

    # Split the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, labels, test_size=0.2, stratify=labels)

    # Train the logistic regression model
    logistic_regressor = LogisticRegression(max_iter=1000)
    logistic_regressor.fit(X_train, y_train)

    # Test the model
    test_model(logistic_regressor, X_test, y_test)

    return logistic_regressor


def train_logistic_regressor_with_scaling(
    X: np.ndarray, labels: np.ndarray
) -> tuple[LogisticRegression, StandardScaler]:
    """Train a logistic regressor after standardizing the input features"""

    X_train, X_test, y_train, y_test = train_test_split(X, labels, test_size=0.2, stratify=labels)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    logistic_regressor = LogisticRegression(max_iter=1000)
    logistic_regressor.fit(X_train_scaled, y_train)

    test_model(logistic_regressor, X_test_scaled, y_test)

    scaler.fit(X)
    X_scaled = scaler.transform(X)
    logistic_regressor.fit(X_scaled, labels)
    print("Train accuracy on full refitted dataset:")
    test_model(logistic_regressor, X_scaled, labels)

    return logistic_regressor, scaler


def train_svc_classifier_raw(X: np.ndarray, labels: np.ndarray) -> SVC:
    """Train an SVC directly on the raw extracted features"""

    X_train, X_test, y_train, y_test = train_test_split(X, labels, test_size=0.2, stratify=labels)

    svc_model = SVC(kernel="rbf")
    svc_model.fit(X_train, y_train)

    test_model(svc_model, X_test, y_test)

    svc_model.fit(X, labels)
    print("Train accuracy on full refitted dataset:")
    test_model(svc_model, X, labels)

    return svc_model


def test_model(model: KNeighborsClassifier | LogisticRegression | SVC, X_test: np.ndarray, y_test: np.ndarray):
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

    return y_pred, accuracy


def test_card_types_model(knn_model: KNeighborsClassifier | LogisticRegression, X_test: np.ndarray, y_test: np.ndarray):
    """Test a trained K-NN model for distinguishing card types"""

    y_pred_int, _ = test_model(knn_model, X_test, y_test)

    # Convert integer predictions back to enum
    y_pred_enum = np.array([CardTypes(pred) for pred in y_pred_int])
    y_test_enum = np.array([CardTypes(pred) for pred in y_test])

    # Display predictions with enum labels
    predictions = zip(y_test_enum, y_pred_enum)
    print("\nActual vs Predicted misclassified labels:")
    for i, (actual, predicted) in enumerate(predictions):
        if actual.name != predicted.name:
            print(f"Actual: {actual.name}, Predicted: {predicted.name}, Features: {X_test[i]}")


def train_card_types_model():
    """Evaluate card type recognition, then train the saved model on all samples."""
    features, labels = load_card_type_features()
    labels_values = labels_to_numpy_values(labels)

    # Keep identical feature vectors in the same fold so duplicates cannot
    # appear in both training and validation data.
    _, groups = np.unique(features, axis=0, return_inverse=True)
    conflicting_groups = [group for group in np.unique(groups) if np.unique(labels_values[groups == group]).size > 1]
    if conflicting_groups:
        print(
            f"{len(conflicting_groups)} set(s) of identical features have different labels; "
            "100% training accuracy is impossible with these labels."
        )
    cross_validation = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    accuracies = []
    for train_indices, test_indices in cross_validation.split(features, labels_values, groups):
        trial_model = SVC(kernel="rbf", C=100)
        trial_model.fit(features[train_indices], labels_values[train_indices])
        accuracies.append(accuracy_score(labels_values[test_indices], trial_model.predict(features[test_indices])))

    print(f"Card type validation accuracy (5 folds): {np.mean(accuracies) * 100:.2f}%")
    print("Fold accuracies:", ", ".join(f"{accuracy * 100:.2f}%" for accuracy in accuracies))

    svm_model = SVC(kernel="rbf", C=100)
    svm_model.fit(features, labels_values)
    print(f"Card type training accuracy: {svm_model.score(features, labels_values) * 100:.2f}%")
    save_model(svm_model, filename="card_type_predictor.svm")


def train_card_merges_model():
    """Train a model that identifies when two cards are going to merge"""

    features, labels = load_card_merges_features()
    model = train_logistic_regressor(X=features, labels=labels)
    save_model(model, filename="card_merges_predictor.lr")


def train_empty_card_slots_model():
    """Train a model that distinguishes between empty and filled card slots"""

    features, labels = load_card_slots_features()
    model = train_knn(X=features, labels=labels)
    save_model(model, filename="card_slots_predictor.knn")


def train_amplify_cards_classifier():
    """Train a model that identifies what cards need to be used in phase 3 of Bird FLoor 4!"""

    features, labels = load_amplify_cards_features()
    features_reduced, pca_model = apply_pca_transform(features, n_components=20)
    model = train_knn(X=features_reduced, labels=labels)
    save_model(model, filename="amplify_cards_predictor.knn")
    save_model(pca_model, filename="pca_amplify_model.pca")


def train_HAM_cards_classifier():
    """Train a model that identifies hard-hitting cards (excluding ultimates)"""

    features, labels = load_HAM_cards_features()
    features_reduced, pca_model = apply_pca_transform(features, n_components=25)
    model = train_knn(X=features_reduced, labels=labels)
    save_model(model, filename="HAM_cards_predictor.knn")
    save_model(pca_model, filename="pca_HAM_cards_model.pca")


def train_thor_cards_classifier():
    """Train a model that identifies hard-hitting cards (excluding ultimates)"""

    features, labels = load_thor_cards_features()
    features_reduced, pca_model = apply_pca_transform(features, n_components=25)
    model = train_svm_classifier(X=features_reduced, labels=labels)
    save_model(model, filename="Thor_cards_predictor.svm")
    save_model(pca_model, filename="pca_Thor_cards_model.pca")


def train_ground_cards_classifier():
    """Validate ground recognition on unseen samples and capture files, then refit."""
    features, labels, file_groups = load_ground_cards_features()
    _, duplicate_groups = np.unique(features, axis=0, return_inverse=True)
    cross_validation = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    accuracies = []
    for train_indices, test_indices in cross_validation.split(features, labels, duplicate_groups):
        trial_model = SVC(kernel="rbf", C=10)
        trial_model.fit(features[train_indices], labels[train_indices])
        accuracies.append(trial_model.score(features[test_indices], labels[test_indices]))
    print(f"Ground validation accuracy (5 folds): {np.mean(accuracies) * 100:.2f}%")
    print("Fold accuracies:", ", ".join(f"{accuracy * 100:.2f}%" for accuracy in accuracies))

    correct, total = 0, 0
    for train_indices, test_indices in LeaveOneGroupOut().split(features, labels, file_groups):
        # Copies of held-out samples must also be excluded from other files.
        train_indices = train_indices[
            ~np.isin(duplicate_groups[train_indices], duplicate_groups[test_indices])
        ]
        trial_model = SVC(kernel="rbf", C=10)
        trial_model.fit(features[train_indices], labels[train_indices])
        predictions = trial_model.predict(features[test_indices])
        correct += np.count_nonzero(predictions == labels[test_indices])
        total += len(test_indices)
    print(f"Ground validation accuracy (held-out files): {correct / total * 100:.2f}%")

    model = SVC(kernel="rbf", C=10)
    model.fit(features, labels)
    print(f"Ground training accuracy: {model.score(features, labels) * 100:.2f}%")
    save_model(model, filename="ground_cards_predictor.svc")


def train_unit_type_classifier():
    """Train a model that identifies the unit type color of a unit"""
    features, labels = load_unit_type_features()
    model = train_svm_classifier(X=features, labels=labels)
    save_model(model, filename="unit_type_predictor.svm")


def main():

    ### For card types
    # train_card_types_model()

    ### For card merges
    # train_card_merges_model()

    ### For empty card slots
    # train_empty_card_slots_model()

    ### Train model for amplify cards
    # train_amplify_cards_classifier()

    ### Train model for identifying HAM cards
    # train_HAM_cards_classifier()

    ### Train model to identify Thor cards
    # train_thor_cards_classifier()

    # ### Train a model that identifies GROUND cards
    train_ground_cards_classifier()

    ### Train a model that the color type of a unit
    # train_unit_type_classifier()

    return


if __name__ == "__main__":
    main()
