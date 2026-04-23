import os
import argparse
import numpy as np
import json
import time
import sys
from datetime import datetime
from tqdm import tqdm
import cv2

# Add project root to path for internal imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.models.face_detector import FaceDetector
from backend.app.models.face_embedder import FaceEmbedder

class AccuracyReportGenerator:
    def __init__(self, dataset_path, output_dir="reports"):
        self.dataset_path = dataset_path
        self.output_dir = output_dir
        self.detector = FaceDetector()
        self.embedder = FaceEmbedder()
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def load_diverse_dataset(self):
        """Loads dataset with metadata support."""
        embeddings = []
        labels = []
        metadata = []
        
        person_dirs = [d for d in os.listdir(self.dataset_path) if os.path.isdir(os.path.join(self.dataset_path, d))]
        
        for person_id in tqdm(person_dirs, desc="Processing Diversity Dataset"):
            person_path = os.path.join(self.dataset_path, person_id)
            for img_file in os.listdir(person_path):
                if not img_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue
                    
                img_path = os.path.join(person_path, img_file)
                img = cv2.imread(img_path)
                if img is None: continue
                
                faces = self.detector.detect_faces(img)
                if not faces: continue
                
                # Extract metadata from filename or directory if present
                # e.g., "person1_lowlight_angle45.jpg"
                img_meta = {
                    "low_light": "lowlight" in img_file.lower(),
                    "side_angle": "angle" in img_file.lower(),
                    "cctv": "cctv" in img_file.lower()
                }
                
                aligned = self.detector.align_face(img, faces[0]['landmarks'])
                emb = self.embedder.get_embedding(aligned)
                
                embeddings.append(emb)
                labels.append(person_id)
                metadata.append(img_meta)
                
        return np.array(embeddings), labels, metadata

    def calculate_metrics(self, embeddings, labels, metadata, threshold=0.6):
        n = len(labels)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / (norms + 1e-8)
        sim_matrix = np.dot(normalized, normalized.T)
        
        tp, fp, tn, fn = 0, 0, 0, 0
        diversity_stats = {
            "low_light": {"tp": 0, "fn": 0},
            "side_angle": {"tp": 0, "fn": 0},
            "cctv": {"tp": 0, "fn": 0}
        }
        
        for i in range(n):
            for j in range(i + 1, n):
                is_same = (labels[i] == labels[j])
                sim = sim_matrix[i, j]
                match = (sim >= threshold)
                
                if is_same:
                    if match: 
                        tp += 1
                        # Update diversity stats if applicable
                        for key in diversity_stats:
                            if metadata[i][key] or metadata[j][key]:
                                diversity_stats[key]["tp"] += 1
                    else: 
                        fn += 1
                        for key in diversity_stats:
                            if metadata[i][key] or metadata[j][key]:
                                diversity_stats[key]["fn"] += 1
                else:
                    if match: fp += 1
                    else: tn += 1
                    
        total_genuine = tp + fn
        total_impostor = fp + tn
        
        tar = tp / total_genuine if total_genuine > 0 else 0
        far = fp / total_impostor if total_impostor > 0 else 0
        frr = fn / total_genuine if total_genuine > 0 else 0
        
        # Calculate diversity-specific TAR
        diversity_tar = {}
        for key, stats in diversity_stats.items():
            denom = stats["tp"] + stats["fn"]
            diversity_tar[key] = stats["tp"] / denom if denom > 0 else "N/A"

        return {
            "overall": {
                "tar": tar,
                "far": far,
                "frr": frr,
                "accuracy": (tp + tn) / (total_genuine + total_impostor)
            },
            "diversity_tar": diversity_tar,
            "counts": {
                "total_images": n,
                "total_pairs": n * (n - 1) // 2,
                "genuine_pairs": total_genuine,
                "impostor_pairs": total_impostor
            }
        }

    def run(self):
        start_time = time.time()
        print(f"--- Starting Enterprise Accuracy Report [{datetime.now()}] ---")
        
        try:
            embs, labs, metas = self.load_diverse_dataset()
            results = self.calculate_metrics(embs, labs, metas)
            
            results["metadata"] = {
                "timestamp": datetime.now().isoformat(),
                "duration_sec": time.time() - start_time,
                "dataset_path": self.dataset_path
            }
            
            output_file = os.path.join(self.output_dir, f"accuracy_report_{int(time.time())}.json")
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=4)
                
            print(f"\n✅ Report Generated: {output_file}")
            print(f"Overall Accuracy: {results['overall']['accuracy']:.2%}")
            print(f"TAR @ 0.6: {results['overall']['tar']:.4f}")
            print(f"FAR @ 0.6: {results['overall']['far']:.4f}")
            
        except Exception as e:
            print(f"❌ Error during evaluation: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Path to real-world diverse dataset")
    args = parser.parse_args()
    
    gen = AccuracyReportGenerator(args.dataset)
    gen.run()
