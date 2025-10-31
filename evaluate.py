import os
import argparse
import numpy as np
from sklearn.metrics import roc_curve, auc
import matplotlib.pyplot as plt
from tqdm import tqdm
from backend.app.models.face_detector import FaceDetector
from backend.app.models.face_embedder import FaceEmbedder
import cv2


def load_dataset(dataset_path):
    """
    Load face embeddings and labels from a dataset directory.

    Args:
        dataset_path (str): Path to the dataset directory with structure dataset_path/person_id/images

    Returns:
        tuple: (embeddings, labels) where embeddings is a numpy array and labels is a list
    """
    embeddings = []
    labels = []
    detector = FaceDetector()
    embedder = FaceEmbedder()

    if not os.path.exists(dataset_path):
        raise ValueError(f"Dataset path {dataset_path} does not exist")

    person_dirs = [d for d in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, d))]
    if not person_dirs:
        raise ValueError(f"No person directories found in {dataset_path}")

    print(f"Loading dataset from {dataset_path}...")
    for person_dir in tqdm(person_dirs, desc="Processing persons"):
        person_path = os.path.join(dataset_path, person_dir)
        img_files = [f for f in os.listdir(person_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if not img_files:
            print(f"Warning: No image files found in {person_path}")
            continue

        for img_file in tqdm(img_files, desc=f"Processing images for {person_dir}", leave=False):
            img_path = os.path.join(person_path, img_file)
            img = cv2.imread(img_path)
            if img is None:
                print(f"Warning: Could not read image {img_path}")
                continue

            faces = detector.detect_faces(img)
            if not faces:
                print(f"Warning: No faces detected in {img_path}")
                continue

            aligned = detector.align_face(img, faces[0]['landmarks'])
            emb = embedder.get_embedding(aligned)
            embeddings.append(emb)
            labels.append(person_dir)

    if not embeddings:
        raise ValueError("No valid embeddings generated from dataset")

    return np.array(embeddings), labels


def compute_similarity_matrix(embeddings):
    """
    Compute cosine similarity matrix for embeddings.

    Args:
        embeddings (np.ndarray): Array of face embeddings

    Returns:
        np.ndarray: Similarity matrix
    """
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized = embeddings / norms
    return np.dot(normalized, normalized.T)


def evaluate_tar_far(embeddings, labels, thresholds):
    """
    Evaluate TAR and FAR for given thresholds.

    Args:
        embeddings (np.ndarray): Face embeddings
        labels (list): Corresponding labels
        thresholds (np.ndarray): Threshold values to evaluate

    Returns:
        list: List of (TAR, FAR) tuples for each threshold
    """
    similarities = compute_similarity_matrix(embeddings)
    n = len(labels)
    tar_far = []

    # Create label matrix for same person check
    label_matrix = np.array([[labels[i] == labels[j] for j in range(n)] for i in range(n)])
    np.fill_diagonal(label_matrix, False)  # Exclude self-comparisons

    # Collect genuine and impostor similarities
    genuine_mask = label_matrix
    impostor_mask = ~label_matrix

    genuine_similarities = similarities[genuine_mask]
    impostor_similarities = similarities[impostor_mask]

    if len(genuine_similarities) == 0 or len(impostor_similarities) == 0:
        raise ValueError("Insufficient data for evaluation: need both genuine and impostor pairs")

    print("Evaluating TAR/FAR...")
    for threshold in tqdm(thresholds, desc="Evaluating thresholds"):
        # TAR: True Accept Rate (genuine accepted)
        tar = np.mean(genuine_similarities >= threshold)
        # FAR: False Accept Rate (impostor accepted)
        far = np.mean(impostor_similarities >= threshold)
        tar_far.append((tar, far))

    return tar_far


def plot_and_save_roc(tar_far, thresholds, output_path="tar_far_plot.png"):
    """
    Plot and save TAR vs FAR curve.

    Args:
        tar_far (list): List of (TAR, FAR) tuples
        thresholds (np.ndarray): Threshold values
        output_path (str): Path to save the plot
    """
    tar, far = zip(*tar_far)

    plt.figure(figsize=(8, 6))
    plt.plot(far, tar, label='TAR vs FAR')
    plt.xlabel('False Accept Rate (FAR)')
    plt.ylabel('True Accept Rate (TAR)')
    plt.title('TAR vs FAR Curve')
    plt.grid(True)
    plt.legend()

    # Compute AUC
    auc_value = auc(far, tar)
    plt.text(0.6, 0.2, f'AUC: {auc_value:.4f}', transform=plt.gca().transAxes,
             bbox=dict(boxstyle="round,pad=0.3", facecolor="white"))

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to {output_path}")
    plt.show()


def find_threshold_for_far(tar_far, thresholds, target_far=0.001):
    """
    Find the threshold that achieves a target FAR.

    Args:
        tar_far (list): List of (TAR, FAR) tuples
        thresholds (np.ndarray): Threshold values
        target_far (float): Target FAR value

    Returns:
        tuple: (threshold, tar) or None if not found
    """
    for t, (tar_val, far_val) in zip(thresholds, tar_far):
        if far_val <= target_far:
            return t, tar_val
    return None


def compute_eer(tar_far, thresholds):
    """
    Compute Equal Error Rate (EER).

    Args:
        tar_far (list): List of (TAR, FAR) tuples
        thresholds (np.ndarray): Threshold values

    Returns:
        tuple: (eer, threshold_at_eer)
    """
    tar, far = zip(*tar_far)
    eer_index = np.argmin(np.abs(np.array(tar) - (1 - np.array(far))))
    eer = (tar[eer_index] + (1 - far[eer_index])) / 2
    return eer, thresholds[eer_index]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate face recognition system")
    parser.add_argument("dataset_path", help="Path to the validation dataset")
    parser.add_argument("--output_plot", default="tar_far_plot.png", help="Output path for the plot")
    args = parser.parse_args()

    try:
        embeddings, labels = load_dataset(args.dataset_path)
        print(f"Loaded {len(embeddings)} embeddings for {len(set(labels))} persons")

        thresholds = np.linspace(0, 1, 100)
        tar_far = evaluate_tar_far(embeddings, labels, thresholds)

        # Plot and save
        plot_and_save_roc(tar_far, thresholds, args.output_plot)

        # Find threshold for FAR=0.001%
        threshold_result = find_threshold_for_far(tar_far, thresholds, 0.001)
        if threshold_result:
            thresh, tar_val = threshold_result
            print(f"Threshold for FAR=0.001%: {thresh:.4f}, TAR: {tar_val:.4f}")
        else:
            print("No threshold found for FAR=0.001%")

        # Compute EER
        eer, eer_thresh = compute_eer(tar_far, thresholds)
        print(f"Equal Error Rate (EER): {eer:.4f} at threshold {eer_thresh:.4f}")

    except Exception as e:
        print(f"Error: {e}")
        exit(1)
