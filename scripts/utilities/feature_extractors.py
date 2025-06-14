"""This script contains standalone strategies to extract features from images,
to be used in pattern matching algorithms.

NOTE: ORB doesn't work with small images (e.g., single cards)!
"""

import os

import cv2
import numpy as np

os.environ["LOKY_MAX_CPU_COUNT"] = "1"  # Replace '4' with the number of cores you want to use


def extract_orb_features(image: np.ndarray, max_features=10):
    """Run the ORB detection algorithm. Fails on small images."""

    # Initialize ORB detector
    orb = cv2.ORB_create(nfeatures=max_features)

    # Detect keypoints and compute descriptors
    keypoints, descriptors = orb.detectAndCompute(image, None)

    # If no descriptors are found, return a zero array
    if descriptors is None:
        print("No descriptors found.")
        return np.zeros((max_features, 32), dtype=np.uint8).flatten()

    # Pad the descriptors array to ensure a consistent size
    if len(descriptors) < max_features:
        descriptors = np.vstack([descriptors, np.zeros((max_features - len(descriptors), 32), dtype=np.uint8)])

    # Return the descriptors as a flattened array
    return descriptors.flatten()


def plot_orb_keypoints(image: np.ndarray):
    """Compute and plot ORB feature keypoints"""
    # Initiate ORB detector
    orb = cv2.ORB_create()

    # find the keypoints with ORB
    kp = orb.detect(image, None)

    # compute the descriptors with ORB
    kp, descriptor = orb.compute(image, kp)

    # Return the image with keypoints
    return cv2.drawKeypoints(image, kp, None, color=(0, 255, 0), flags=0)


# Function to extract color histogram features
def extract_color_histograms_features(
    images: list[np.ndarray] | np.ndarray, bins: tuple[int] = (8, 8, 8)
) -> np.ndarray:
    """Compute color histograms for a batch of images. Works even with small images, and should work with SVM models.

    Args:
        images (np.ndarray): A list of images with shape (width, height, channels), or an array with 'batch' as the first dimension.
        bins (tuple): Number of bins for each channel in the histogram.

    Returns:
        np.ndarray: A 2D array where each row is the flattened histogram of an image.
    """

    if isinstance(images, np.ndarray) and images.ndim == 3:
        # It's a single image, let's make a batch off of it
        images = images[np.newaxis, ...]

    histograms = []

    for image in images:
        # Convert the image to HSV color space
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Compute the histogram and normalize it
        hist = cv2.calcHist([hsv_image], [0, 1, 2], None, bins, [0, 180, 0, 256, 0, 256])
        cv2.normalize(hist, hist)

        # Flatten the histogram and add it to the list
        histograms.append(hist.flatten())

    # Convert the list of histograms to a NumPy array
    return np.array(histograms)


def extract_difference_of_histograms_features(images: np.ndarray) -> np.ndarray:
    """Given two images, compute each one's color histograms and return the norm of the difference as single feature.

    Args:
        images (np.ndarray): Array of batch images, ideally of shape (batch, 2, width, height, channels).

    Returns:
        np.ndarray:     Array of shape (batch, features=1).
    """

    # Preprocessing
    if isinstance(images, (tuple, list)):
        # We need to convert it to np.ndarray
        images = np.array(images)
    if images.ndim == 4:
        # Assume it's an array, add the batch dimension
        images = images[np.newaxis, ...]

    features = []

    for batch_image in images:
        # For each image in the batch, compute the color histogram difference between the two images,
        # and append it to the list of features
        histograms = extract_color_histograms_features(batch_image)
        features.append(np.linalg.norm(histograms[0] - histograms[1]))

    # Add the final feature dimension, to make it shape (batch, 1)
    return np.array(features)[..., np.newaxis]


def extract_color_features(images: np.ndarray | list[np.ndarray], type="median") -> np.ndarray:
    """Computes the feature color of each channel. Works well with K-NN classification models.

    Args:
        images (np.ndarray | list[np.ndarray]): Either:
            - a 4D array of shape (N, H, W, 3), or
            - a list of 4D arrays of shape (N_i, H_i, W_i, 3) each.
        type (str): "mean" or "median".

    Returns:
        np.ndarray: An array of shape (total_N, 3), with one RGB feature vector per image.
    """

    if type == "median":
        feature_func = np.median
    elif type == "mean":
        feature_func = np.mean
    else:
        raise ValueError(f"Feature type '{type}' not understood. Pick between 'median' and 'mean'.")

    def process_batch(batch: np.ndarray) -> np.ndarray:
        if batch.ndim == 3:
            batch = batch[np.newaxis, ...]  # Promote to batch of 1

        if batch.ndim != 4 or batch.shape[-1] != 3:
            raise ValueError("Each image batch must have shape (N, H, W, 3)")

        feat_b = feature_func(batch[..., 0], axis=(1, 2))
        feat_g = feature_func(batch[..., 1], axis=(1, 2))
        feat_r = feature_func(batch[..., 2], axis=(1, 2))
        return np.stack((feat_r, feat_g, feat_b), axis=-1)

    if isinstance(images, list):
        features = [process_batch(batch) for batch in images]
        return np.concatenate(features, axis=0)
    else:
        return process_batch(images)


def extract_single_channel_features(images: np.ndarray, type="median") -> np.ndarray:
    """Extract the specific metric for a single channel of the image, to handle gray images properly"""

    if images.ndim == 2:
        # Add the batch dimension
        images = images[np.newaxis, ...]

    if type == "median":
        feature_func = np.median
    elif type == "mean":
        feature_func = np.mean
    else:
        raise ValueError(f"Feature type '{type}' not understood. Pick between 'median' and 'mean'.")

    feature = feature_func(images, axis=(1, 2))

    return feature[..., np.newaxis]  # Add the feature dimension
