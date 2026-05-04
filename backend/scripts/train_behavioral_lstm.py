#!/usr/bin/env python3
"""
Train the Behavioral LSTM Model.

This script generates synthetic emotion sequence data correlated with
behavioral labels (fatigue, aggression, engagement) and trains the
LSTMBehaviorNet model.

Training data generation:
- Emotion sequences (30 timesteps x 10 features) are generated with
  temporal patterns correlated to behavioral labels.
- Labels are derived from emotion statistics (e.g., high tired+sad -> fatigue).

The trained model weights are saved to:
  - backend/models/behavioral_lstm.pt (PyTorch)
  - backend/models/onnx_bundle/behavioral_predictor.onnx (ONNX)
"""

import os
import sys
import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from pathlib import Path
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.behavioral_predictor import LSTMBehaviorNet

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Synthetic Data Generation
# ─────────────────────────────────────────────

class SyntheticBehaviorDataset(Dataset):
    """Generate synthetic emotion sequences with behavior labels."""

    EMOTION_INDEX = {
        'happy': 0, 'sad': 1, 'angry': 2, 'surprise': 3,
        'fear': 4, 'disgust': 5, 'neutral': 6, 'tired': 7,
        'confidence': 8, 'temporal_weight': 9
    }

    def __init__(self, num_samples: int = 10000, seq_len: int = 30, feature_dim: int = 10):
        self.num_samples = num_samples
        self.seq_len = seq_len
        self.feature_dim = feature_dim

    def __len__(self):
        return self.num_samples

    def _generate_emotion_profile(self, profile_type: str, timesteps: int) -> np.ndarray:
        """Generate an emotion time-series for a given behavioral profile."""
        seq = np.zeros((timesteps, self.feature_dim), dtype=np.float32)

        t = np.linspace(0, 4 * np.pi, timesteps)

        if profile_type == 'fatigued':
            # High tired/sad, low happy/surprise, decaying confidence
            seq[:, self.EMOTION_INDEX['tired']] = 0.6 + 0.3 * np.sin(t + 1) + np.random.normal(0, 0.1, timesteps)
            seq[:, self.EMOTION_INDEX['sad']] = 0.5 + 0.3 * np.cos(t) + np.random.normal(0, 0.1, timesteps)
            seq[:, self.EMOTION_INDEX['happy']] = 0.2 + 0.1 * np.sin(t)
            seq[:, self.EMOTION_INDEX['surprise']] = 0.1 + 0.05 * np.random.rand(timesteps)
            seq[:, self.EMOTION_INDEX['confidence']] = np.clip(0.8 - 0.02 * np.arange(timesteps) + np.random.normal(0, 0.05, timesteps), 0, 1)
            seq[:, self.EMOTION_INDEX['neutral']] = 0.3 + 0.2 * np.random.rand(timesteps)

        elif profile_type == 'aggressive':
            # High angry/disgust, moderate happy, low fear/sad
            seq[:, self.EMOTION_INDEX['angry']] = 0.7 + 0.2 * np.abs(np.sin(t)) + np.random.normal(0, 0.1, timesteps)
            seq[:, self.EMOTION_INDEX['disgust']] = 0.5 + 0.2 * np.cos(t * 0.5) + np.random.normal(0, 0.1, timesteps)
            seq[:, self.EMOTION_INDEX['happy']] = 0.3 + 0.1 * np.random.rand(timesteps)
            seq[:, self.EMOTION_INDEX['fear']] = 0.1 + 0.05 * np.random.rand(timesteps)
            seq[:, self.EMOTION_INDEX['sad']] = 0.1 + 0.05 * np.random.rand(timesteps)
            seq[:, self.EMOTION_INDEX['confidence']] = 0.7 + 0.2 * np.random.rand(timesteps)

        elif profile_type == 'engaged':
            # High happy/surprise, high confidence, low tired/sad
            seq[:, self.EMOTION_INDEX['happy']] = 0.7 + 0.2 * np.sin(t * 0.5) + np.random.normal(0, 0.1, timesteps)
            seq[:, self.EMOTION_INDEX['surprise']] = 0.5 + 0.3 * np.cos(t * 0.7) + np.random.normal(0, 0.1, timesteps)
            seq[:, self.EMOTION_INDEX['confidence']] = 0.8 + 0.15 * np.sin(t * 0.3) + np.random.normal(0, 0.05, timesteps)
            seq[:, self.EMOTION_INDEX['tired']] = 0.1 + 0.05 * np.random.rand(timesteps)
            seq[:, self.EMOTION_INDEX['sad']] = 0.1 + 0.05 * np.random.rand(timesteps)
            seq[:, self.EMOTION_INDEX['neutral']] = 0.2 + 0.1 * np.random.rand(timesteps)

        else:  # neutral / mixed
            # Balanced emotions, moderate confidence
            for emo in ['happy', 'sad', 'angry', 'surprise', 'fear', 'disgust', 'neutral']:
                seq[:, self.EMOTION_INDEX[emo]] = 0.3 + 0.2 * np.random.rand(timesteps)
            seq[:, self.EMOTION_INDEX['confidence']] = 0.5 + 0.2 * np.random.rand(timesteps)
            seq[:, self.EMOTION_INDEX['tired']] = 0.3 + 0.1 * np.random.rand(timesteps)

        # temporal_weight increases over sequence (temporal accumulation)
        seq[:, self.EMOTION_INDEX['temporal_weight']] = np.linspace(0.2, 1.0, timesteps)

        # Clip all values to [0, 1]
        seq = np.clip(seq, 0, 1)
        return seq

    def __getitem__(self, idx):
        # Randomly pick a profile type (balanced)
        profile_type = np.random.choice(['fatigued', 'aggressive', 'engaged', 'neutral'])

        # Generate emotion sequence
        sequence = self._generate_emotion_profile(profile_type, self.seq_len)

        # Compute behavior labels from aggregated statistics
        if profile_type == 'fatigued':
            fatigue = np.mean(sequence[:, self.EMOTION_INDEX['tired']]) + np.mean(sequence[:, self.EMOTION_INDEX['sad']])
            aggression = np.mean(sequence[:, self.EMOTION_INDEX['angry']]) + np.mean(sequence[:, self.EMOTION_INDEX['disgust']])
            engagement = np.mean(sequence[:, self.EMOTION_INDEX['happy']]) + np.mean(sequence[:, self.EMOTION_INDEX['surprise']])
        elif profile_type == 'aggressive':
            fatigue = np.mean(sequence[:, self.EMOTION_INDEX['tired']]) + np.mean(sequence[:, self.EMOTION_INDEX['sad']])
            aggression = np.mean(sequence[:, self.EMOTION_INDEX['angry']]) + np.mean(sequence[:, self.EMOTION_INDEX['disgust']])
            engagement = np.mean(sequence[:, self.EMOTION_INDEX['happy']]) + np.mean(sequence[:, self.EMOTION_INDEX['surprise']])
        elif profile_type == 'engaged':
            fatigue = np.mean(sequence[:, self.EMOTION_INDEX['tired']]) + np.mean(sequence[:, self.EMOTION_INDEX['sad']])
            aggression = np.mean(sequence[:, self.EMOTION_INDEX['angry']]) + np.mean(sequence[:, self.EMOTION_INDEX['disgust']])
            engagement = np.mean(sequence[:, self.EMOTION_INDEX['happy']]) + np.mean(sequence[:, self.EMOTION_INDEX['surprise']])
        else:  # neutral
            fatigue = 0.33 + np.random.normal(0, 0.1)
            aggression = 0.33 + np.random.normal(0, 0.1)
            engagement = 0.33 + np.random.normal(0, 0.1)

        # Normalize so they roughly sum to 1 (like the softmax output)
        total = fatigue + aggression + engagement
        if total > 0:
            fatigue /= total
            aggression /= total
            engagement /= total
        else:
            fatigue, aggression, engagement = 0.33, 0.33, 0.34

        label = np.array([fatigue, aggression, engagement], dtype=np.float32)

        return torch.from_numpy(sequence), torch.from_numpy(label)


def train_model(
    epochs: int = 20,
    batch_size: int = 64,
    lr: float = 1e-3,
    model_save_path: str = "backend/models/behavioral_lstm.pt",
    onnx_export_path: str = "backend/models/onnx_bundle/behavioral_predictor.onnx"
):
    """Train the LSTM and export to PyTorch + ONNX."""

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Training on device: {device}")

    # Dataset & loader
    dataset = SyntheticBehaviorDataset(num_samples=20000)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)

    # Model
    model = LSTMBehaviorNet(input_size=10, hidden_size=128, num_layers=2, output_size=256).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    # Training loop
    model.train()
    for epoch in range(epochs):
        running_loss = 0.0
        correct = 0
        total = 0

        for batch_idx, (sequences, labels) in enumerate(loader):
            sequences = sequences.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = model(sequences)  # [B, 256]
            outputs_3 = outputs[:, :3]  # Use first 3 dims for loss
            loss = criterion(outputs_3, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()

            # Accuracy on first 3 logits
            pred = outputs_3.argmax(dim=1)
            true = labels.argmax(dim=1)
            correct += (pred == true).sum().item()
            total += labels.size(0)

            if batch_idx % 100 == 0:
                logger.info(f"Epoch {epoch+1}/{epochs} | Batch {batch_idx} | Loss: {loss.item():.4f}")

        accuracy = correct / total if total > 0 else 0
        avg_loss = running_loss / len(loader)
        logger.info(f"Epoch {epoch+1}/{epochs} completed - Loss: {avg_loss:.4f} | Accuracy: {accuracy:.3%}")

    # Save PyTorch weights
    save_path = Path(model_save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), save_path)
    logger.info(f"Model saved to {save_path}")

    # Export to ONNX
    model.eval()
    dummy_input = torch.randn(1, 30, 10).to(device)

    onnx_path = Path(onnx_export_path)
    onnx_path.parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['emotion_sequence'],
        output_names=['behavior_vector'],
        dynamic_axes={
            'emotion_sequence': {1: 'seq_len'},
            'behavior_vector': {0: 'batch'}
        }
    )
    logger.info(f"ONNX model exported to {onnx_path}")

    # Verify ONNX file is non-trivial
    onnx_size = onnx_path.stat().st_size
    logger.info(f"ONNX file size: {onnx_size} bytes")
    if onnx_size < 1000:
        logger.warning("ONNX file is suspiciously small — check export.")

    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train behavioral LSTM model")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    args = parser.parse_args()

    logger.info("Starting behavioral LSTM training...")
    train_model(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)
    logger.info("Training complete. Model artifacts generated.")
