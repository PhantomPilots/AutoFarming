import os

import dill as pickle
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from utilities.card_data import CardTypes
from utilities.feature_extractors import (
    extract_color_features,
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
