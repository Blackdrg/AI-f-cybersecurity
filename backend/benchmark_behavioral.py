"""Benchmark BehavioralPredictor accuracy on validation dataset.

Usage:
    python -m backend.benchmark_behavioral --dataset-path /data/behavioral_test.jsonl

The dataset should be a JSONL file with each line:
{
  "emotion_sequence": [{"emotions": {...}}, ...],
  "expected_behavior": "aggressive|fatigue|engagement"
}
"""
import argparse
import json
import logging
import numpy as np
from pathlib import Path
from app.models.behavioral_predictor import BehavioralPredictor

logger = logging.getLogger(__name__)

def load_dataset(path: str):
    data = []
    with open(path, 'r') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def main():
    parser = argparse.ArgumentParser(description="Benchmark BehavioralPredictor")
    parser.add_argument("--dataset-path", type=str, required=True, help="Path to test dataset JSONL")
    parser.add_argument("--seq-length", type=int, default=30, help="Sequence length for predictor")
    args = parser.parse_args()

    predictor = BehavioralPredictor(sequence_length=args.seq_length)
    dataset = load_dataset(args.dataset_path)
    total = len(dataset)
    if total == 0:
        logger.error("No data loaded")
        return

    correct = 0
    confusion = {"aggressive": {"tp":0, "fp":0, "fn":0}, "fatigue": {"tp":0, "fp":0, "fn":0}, "engagement": {"tp":0, "fp":0, "fn":0}}
    for item in dataset:
        emotion_sequence = item.get("emotion_sequence", [])
        expected = item.get("expected_behavior")
        # predictor expects list of emotion dicts
        result = predictor.predict_with_temporal(emotion_sequence)
        predicted = result.get("dominant_behavior")
        if predicted == expected:
            correct += 1
        # Update confusion per class
        for cls in ["aggressive", "fatigue", "engagement"]:
            if predicted == cls and expected == cls:
                confusion[cls]["tp"] += 1
            elif predicted == cls and expected != cls:
                confusion[cls]["fp"] += 1
            elif predicted != cls and expected == cls:
                confusion[cls]["fn"] += 1

    accuracy = correct / total
    logger.info(f"Accuracy: {accuracy:.3%} ({correct}/{total})")
    for cls, counts in confusion.items():
        prec = counts["tp"] / (counts["tp"] + counts["fp"]) if (counts["tp"] + counts["fp"]) > 0 else 0
        rec = counts["tp"] / (counts["tp"] + counts["fn"]) if (counts["tp"] + counts["fn"]) > 0 else 0
        f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0
        logger.info(f"{cls}: P={prec:.3%} R={rec:.3%} F1={f1:.3%}")

    # Dump results to JSON for CI
    results = {
        "accuracy": accuracy,
        "confusion": confusion,
        "total": total,
        "correct": correct
    }
    out_path = Path(args.dataset_path).with_suffix(".benchmark.json")
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results written to {out_path}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
