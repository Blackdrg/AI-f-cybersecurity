import time
import logging
from backend.app.models.face_detector import FaceDetector
from backend.app.models.face_embedder import FaceEmbedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ColdStartBenchmark")

def measure_cold_start():
    logger.info("Starting Cold Start Benchmark...")
    
    # Measure Detector Load Time
    start_time = time.time()
    detector = FaceDetector()
    detector_time = time.time() - start_time
    logger.info(f"FaceDetector Cold Start (Model + GPU Allocation): {detector_time:.3f} seconds")
    
    # Measure Embedder Load Time
    start_time = time.time()
    embedder = FaceEmbedder()
    embedder_time = time.time() - start_time
    logger.info(f"FaceEmbedder Cold Start (Model + GPU Allocation): {embedder_time:.3f} seconds")
    
    total_time = detector_time + embedder_time
    logger.info(f"Total AI Model Cold Start Latency: {total_time:.3f} seconds")
    
    if total_time > 5.0:
        logger.warning("Cold start latency is above the 5.0s threshold. Consider pre-warming models or optimizing weights.")
    else:
        logger.info("Cold start latency is within acceptable limits for Enterprise HA.")

if __name__ == "__main__":
    measure_cold_start()
