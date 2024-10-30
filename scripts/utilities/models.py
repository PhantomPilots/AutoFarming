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

os.environ["LOKY_MAX_CPU_COUNT"] = "1"  # Replace '4' with the number of cores you want to use


class IModel:
    """Interface class for any models needed. Is there anything they all share, to group here?"""

    # Class variable for the model
    model: KNeighborsClassifier | LogisticRegression = None
    # Model for transforming features before the the classifier
    feature_transform_model: PCA | None = None

    @classmethod
    def _load_feature_transform_model(cls, model_filename: str):
        if cls.feature_transform_model is None:
            with open(os.path.join("models", model_filename), "rb") as model_file:
                print("Loading model!")
                cls.feature_transform_model = pickle.load(model_file)

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

    @staticmethod
    def is_amplify_card(card_1: np.ndarray | None) -> bool:
        """Predict if a card ia amplify or Thor's"""

        if card_1 is None:
            return 0

        # Ensure the models are properly loaded
        AmplifyCardPredictor._load_feature_transform_model("pca_amplify_model.pca")
        AmplifyCardPredictor._load_model("amplify_cards_predictor.knn")

        # TODO: Apply PCA to reduce dimensionality! And use SVM with RBF kernel, or even K-NN?
        features = extract_color_histograms_features(card_1, bins=(8, 8, 8))

        # Transform features with the PCA
        features_reduced = AmplifyCardPredictor.feature_transform_model.transform(features)

        return int(AmplifyCardPredictor.model.predict(features_reduced).item())


class HAMCardPredictor(IModel):
    """Class that predicts whether a card is hard-hitting"""

    @staticmethod
    def is_HAM_card(card: np.ndarray | None) -> bool:
        """Predict if a card is hard-hitting"""

        if card is None:
            return 0

        # Ensure all models are properly loaded
        HAMCardPredictor._load_feature_transform_model("pca_HAM_cards_model.pca")
        HAMCardPredictor._load_model("HAM_cards_predictor.knn")

        # Extract the features
        features = extract_color_histograms_features(card, bins=(8, 8, 8))

        # Transform features with the PCA
        features_reduced = HAMCardPredictor.feature_transform_model.transform(features)

        # Finally, predict HAM card
        return int(HAMCardPredictor.model.predict(features_reduced).item())


class ThorCardPredictor(IModel):
    """Class that identifies Thor cards"""

    @staticmethod
    def is_Thor_card(card: np.ndarray | None) -> bool:
        """Predict if a card is hard-hitting"""

        if card is None:
            return 0

        # Ensure all models are properly loaded
        ThorCardPredictor._load_feature_transform_model("pca_Thor_cards_model.pca")
        ThorCardPredictor._load_model("Thor_cards_predictor.svm")

        # Extract the features
        features = extract_color_histograms_features(card, bins=(8, 8, 8))

        # Transform features with the PCA
        features_reduced = ThorCardPredictor.feature_transform_model.transform(features)

        # Finally, predict HAM card
        return int(ThorCardPredictor.model.predict(features_reduced).item())


class GroundCardPredictor(IModel):
    """Class that identifies if a card is ground or not"""

    @staticmethod
    def is_ground_card(card: np.ndarray) -> bool:
        """Predict ground card"""

        # Ensure models are properly loaded
        GroundCardPredictor._load_feature_transform_model("pca_ground_cards_model.pca")
        GroundCardPredictor._load_model("ground_cards_predictor.svm")

        # Extract the features
        features = extract_color_histograms_features(card, bins=(8, 8, 8))
        # Transform the features
        features_reduced = GroundCardPredictor.feature_transform_model.transform(features)

        # Predict if the card is ground
        return int(GroundCardPredictor.model.predict(features_reduced).item())
