import abc
import argparse
import os

import cv2
import dill as pickle
import numpy as np
from utilities.card_data import CardTypes
from utilities.feature_extractors import (
    extract_color_features,
    extract_color_histograms_features,
    extract_difference_of_histograms_features,
    extract_orb_features,
    extract_single_channel_features,
    plot_orb_keypoints,
)
from utilities.utilities import (
    capture_hand_image,
    capture_window,
    crop_image,
    determine_relative_coordinates,
    display_image,
    get_card_interior_image,
    get_card_type_image,
    get_hand_cards,
    get_hand_cards_3_cards,
)


class DataCollector(abc.ABC):
    def collect_data(self, num_units=4):

        dataset_list = []
        labels_list = []
        labels = None  # To allow bookkeeping of labels

        while True:

            condition = input("Press ENTER to capture hand screenshot ('c' to quit data collection) ")
            if condition == "c":
                print("Quitting data collection")
                break

            hand, labels = self.collect_hand_data(previous_labels=labels, num_units=num_units)

            dataset_list.append(hand)
            labels_list.append(labels)

        # We use `concatenate` here instead of `stack` because the batch dimension already exists in each `hand`
        dataset = np.concatenate(dataset_list, axis=0)
        all_labels = np.concatenate(labels_list, axis=0)

        return dataset, all_labels

    @abc.abstractmethod
    def collect_hand_data(self, previous_labels: np.ndarray | None = None, num_units=4) -> list[np.ndarray]:
        """Logic to extract the cards and labels from the hand.
        `previous_labels` used if bookkeeping is desired, to facilitate data collection
        (meaning, always click the rightmost cards).
        Needs to be mplemented by a subclass.
        """


class CardTypeCollector(DataCollector):
    def collect_hand_data(self, previous_labels: np.ndarray | None = None, num_units=4) -> list[np.ndarray]:
        """From the current screenshot, extract and return all the card types"""

        cards = get_hand_cards(num_units=num_units)

        data = []
        labels = []

        for i, card in enumerate(cards):
            # Extract card type image
            card_type_image = get_card_type_image(card.card_image, num_units=num_units)

            display_image(card_type_image)

            if i > 3 and previous_labels is not None and False:
                # Use the first 4 instances of the previous labels as the last 4 of this iteration
                card_label = previous_labels[i - 4]
                print(f"Auto-appending label {CardTypes(card_label)}")

            else:
                # cv2.imshow("card type", card_type_image)
                # cv2.waitKey(0)
                card_label = int(
                    input("Card type (att=0, att_debuff=3, ult=-1, disabled=9, ground=10, buff=5, stance=1, recov=2): ")
                )
                # cv2.destroyAllWindows()

            # Append the new card to the dataset, and the label to the labels list
            data.append(card_type_image)
            labels.append(CardTypes(card_label))

        data = np.stack(data, axis=0)
        labels = np.stack(labels, axis=0)

        return data, labels


class MergeCardsCollector(DataCollector):
    """Collects data to identify when two cards are going to merge when clicked on a third one"""

    def collect_hand_data(self, previous_labels: np.ndarray | None = None, num_units=4) -> list[np.ndarray]:
        """Collect data to identify if clicking on a card will result in a merge"""

        cards = get_hand_cards(num_units)

        data = []
        labels = []

        for i, card in enumerate(cards[1:-1], start=1):

            # Extract the left and right cards
            card_image_left = get_card_interior_image(cards[i + 1].card_image, num_units=num_units)
            card_image_right = get_card_interior_image(cards[i - 1].card_image, num_units=num_units)

            # Convert to grayscale
            # card_image_left = cv2.cvtColor(card_image_left, cv2.COLOR_BGR2GRAY)
            # card_image_right = cv2.cvtColor(card_image_right, cv2.COLOR_BGR2GRAY)

            # Testing potential features
            feature = extract_difference_of_histograms_features((card_image_left, card_image_right))
            print("Norm of histogram difference: ", feature)

            cv2.imshow("left image", card_image_left)
            cv2.imshow("right image", card_image_right)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

            # Get the card data from which the features will be extracted.
            # Need to concatenate the cards together along a new axis
            card_data = np.stack((card_image_left, card_image_right), axis=0)

            # Get the label
            fusion_label = input("Will the two cards merge? 1/y, 0/n: ")
            fusion_label = 1 if "y" in fusion_label else 0 if "n" in fusion_label else int(fusion_label)

            # Append the new card to the dataset, and the label to the labels list
            data.append(card_data)
            labels.append(fusion_label)

        data = np.stack(data, axis=0)
        labels = np.stack(labels, axis=0)

        return data, labels


class AmplifyCardsCollector(DataCollector):
    """Collects data to train a model that identifies the cards required for phase 3"""

    def collect_hand_data(self, previous_labels: np.ndarray | None = None, num_units=4) -> list[np.ndarray]:

        cards = get_hand_cards(num_units)

        data = []
        labels = []

        for i, card in enumerate(cards):

            if i > 3 and previous_labels is not None and False:
                # Use the first 4 instances of the previous labels as the last 4 of this iteration
                card_label = previous_labels[i - 4]
                print(f"Auto-appending label: {'amplify' if card_label else 'NO amplify'}")
            else:
                card_label = input("Is this card 'amplify' or Thor? 1/y, 0/n: ")
                card_label = 1 if "y" in card_label else 0 if "n" in card_label else int(card_label)

            # Extract the inside of the card, effectively removing its border/rank information
            card_interior = get_card_interior_image(card.card_image, num_units=num_units)

            # Let's plot the image for debugging
            # display_image(card_interior)

            data.append(card_interior)
            labels.append(card_label)

        data = np.stack(data, axis=0)
        labels = np.stack(labels, axis=0)

        return data, labels


class HAMCardsCollector(DataCollector):
    """Collect that corresponding to high-hitting cards (excluding ultimates)"""

    def collect_hand_data(self, previous_labels: np.ndarray | None = None, num_units=4) -> list[np.ndarray]:
        cards = get_hand_cards(num_units)

        data = []
        labels = []

        for i, card in enumerate(cards):
            if i > 3 and previous_labels is not None and False:
                # Use the first 4 instances of the previous labels as the last 4 of this iteration
                card_label = previous_labels[i - 4]
                print(f"Auto-appending label: {'HAM' if card_label else 'Weak'}")
            else:
                card_label = input("Is this a high-hitting card (no ultimate)? 1/y, 0/n: ")
                card_label = 1 if "y" in card_label else 0 if "n" in card_label else int(card_label)

            # Extract the inside of the card, effectively removing its border/rank information
            card_interior = get_card_interior_image(card.card_image, num_units=num_units)

            # Let's plot the image for debugging
            # display_image(card_interior)

            data.append(card_interior)
            labels.append(card_label)

        data = np.stack(data, axis=0)
        labels = np.stack(labels, axis=0)

        return data, labels


class ThorCardCollector(DataCollector):
    """Identify Thor cards only"""

    def collect_hand_data(self, previous_labels: np.ndarray | None = None, num_units=4) -> list[np.ndarray]:
        cards = get_hand_cards(num_units)

        data = []
        labels = []

        for i, card in enumerate(cards):
            if i > 3 and previous_labels is not None:
                # Use the first 4 instances of the previous labels as the last 4 of this iteration
                card_label = previous_labels[i - 4]
                print(f"Auto-appending label: {'THOR' if card_label else 'not thor'}")
            else:
                card_label = input("Is this a Thor card? 1/y, 0/n: ")
                card_label = 1 if "y" in card_label else 0 if "n" in card_label else int(card_label)

            # Extract the inside of the card, effectively removing its border/rank information
            card_interior = get_card_interior_image(card.card_image, num_units=num_units)

            # Let's plot the image for debugging
            # display_image(card_interior)

            data.append(card_interior)
            labels.append(card_label)

        data = np.stack(data, axis=0)
        labels = np.stack(labels, axis=0)

        return data, labels


class GroundDataCollector(DataCollector):
    """Identify if a card is ground or not. Use the whole interior of the card as data"""

    def collect_hand_data(self, previous_labels: np.ndarray | None = None, num_units=4) -> list[np.ndarray]:
        cards = get_hand_cards(num_units)

        data = []
        labels = []

        for card in cards:
            # Extract the inside of the card, effectively removing its border/rank information
            card_interior = get_card_interior_image(card.card_image, num_units=num_units)

            # # Let's plot the image for debugging
            # display_image(card_interior)

            card_label = input("Is this a GROUND card? 1/y, 0/n: ")
            card_label = 1 if "y" in card_label else 0 if "n" in card_label else int(card_label)

            data.append(card_interior)
            labels.append(card_label)

        data = np.stack(data, axis=0)
        labels = np.stack(labels, axis=0)

        return data, labels


def save_data(dataset: np.ndarray, all_labels: np.ndarray, filename: str):
    """Creates a dictionary with the data and saves it under 'data/'"""

    data_dict = {"data": dataset, "labels": all_labels}

    i = 0
    filepath = os.path.join("data", f"{filename}_{i}")
    while os.path.exists(f"{filepath}.npy"):
        idx = int(filepath.split("_")[-1]) + 1
        filepath = filepath.replace(str(i), str(idx))
        i += 1

    # Append the numpy extension
    filepath += ".npy"
    # Save the dataset
    save = input(f"About to save dataset in {filepath}, continue? (Y/n) ")
    if not save or "y" in save.lower():
        with open(filepath, "wb") as pfile:
            pickle.dump(data_dict, pfile)
            print(f"New dataset saved in {filepath}")
    else:
        print("Not saving dataset!")


def collect_data(CollectorClass: DataCollector, filename: str, num_units=4):
    print(f"Collecting data for {CollectorClass.__name__}")

    data_collector: DataCollector = CollectorClass()
    dataset, all_labels = data_collector.collect_data(num_units=num_units)
    print("All labels:\n", all_labels)
    save_data(dataset, all_labels, filename=filename)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--num-units", type=int, default=4, help="How many units in the front")
    args = parser.parse_args()

    # collect_data(MergeCardsCollector, filename="card_merges_data")

    collect_data(CardTypeCollector, filename="card_types_data", num_units=args.num_units)

    # collect_data(AmplifyCardsCollector, filename="amplify_cards_data")

    # collect_data(HAMCardsCollector, filename="ham_cards_data")

    # collect_data(ThorCardCollector, filename="thor_cards_data")

    # collect_data(GroundDataCollector, filename="ground_data", num_units=args.num_units)


if __name__ == "__main__":

    main()
