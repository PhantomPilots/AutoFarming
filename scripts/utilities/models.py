import os

import dill as pickle
import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from utilities.card_data import CardTypes
from utilities.feature_extractors import (
    extract_color_features,
    extract_color_histograms_features,
    extract_difference_of_histograms_features,
)


class IModel:
    """Interface class for any models needed. Is there anything they all share, to group here?"""

    # Class variable for the model
    model: KNeighborsClassifier | LogisticRegression = None

    @classmethod
    def _load_model(cls, model_filename: str):
        """Load the model and assign it to the class variable."""
        if cls.model is None:
            with open(os.path.join("models", model_filename), "rb") as model_file:
                cls.model = pickle.load(model_file)


class CardTypePredictor(IModel):
    """Predictor for card types"""

    @staticmethod
    def predict_card_type(card_type_image: np.ndarray, feature_type: str = "median") -> CardTypes:
        """Extract the features from the card and predict its type"""

        # Ensure the model is properly loaded
        CardTypePredictor._load_model("card_type_predictor.knn")

        features = extract_color_features(card_type_image[np.newaxis, ...], type=feature_type)
        predicted_label = CardTypePredictor.model.predict(features).item()
        return CardTypes(predicted_label)


class CardMergePredictor(IModel):

    @staticmethod
    def predict_card_merge(card_1: np.ndarray, card_2: np.ndarray) -> bool:
        """Extract the features and use the model to predict whether two cards are going to merge"""

        # Ensure the model is properly loaded
        CardMergePredictor._load_model("card_merges_predictor.lr")

        features = extract_difference_of_histograms_features((card_1, card_2))
        return int(CardMergePredictor.model.predict(features).item())


class AmplifyCardPredictor(IModel):
    """Model that identifies if a card should be played in phase 3"""

    pca_model: PCA | None = None

    @staticmethod
    def _load_pca_model(model_filename: str):
        if AmplifyCardPredictor.pca_model is None:
            with open(os.path.join("models", model_filename), "rb") as model_file:
                print("Loading model!")
                AmplifyCardPredictor.pca_model = pickle.load(model_file)

    @staticmethod
    def is_amplify_card(card_1: np.ndarray | None) -> bool:
        """Predict if a card ia amplify or Thor's"""

        if card_1 is None:
            return 0

        # Ensure the model is properly loaded
        AmplifyCardPredictor._load_model("amplify_cards_predictor.knn")
        # Load the PCA model
        AmplifyCardPredictor._load_pca_model("pca_amplify_model.pca")

        # TODO: Apply PCA to reduce dimensionality! And use SVM with RBF kernel, or even K-NN?
        features = extract_color_histograms_features(card_1, bins=(4, 4, 4))

        # Fit the PCA -- NOTE: THIS IS WRONG, scaling/dim. reduction models should be saved during training and loaded here
        features_reduced = AmplifyCardPredictor.pca_model.transform(features)

        return int(AmplifyCardPredictor.model.predict(features_reduced).item())
