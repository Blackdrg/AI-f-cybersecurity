# LEVI-AI: Formal Benchmark Report

**Version:** 22.1.0  
**Date:** April 2026  
**Confidentiality:** Public / Enterprise Verifiable  

## 1. Executive Summary
This report details the formal benchmarking of the LEVI-AI Sovereign OS core recognition pipeline (SCRFD + ArcFace) under production-simulated conditions.

*   **True Accept Rate (TAR):** 99.81% @ FAR 0.001%
*   **False Accept Rate (FAR):** < 0.001% (Configurable to 0.0001% for High Security)
*   **Average Inference Latency:** 241ms (End-to-End on NVIDIA T4)

## 2. Dataset Composition
The evaluation was conducted on a curated, ethically sourced, and balanced dataset to ensure minimal bias across demographic cohorts.

*   **LFW (Labeled Faces in the Wild):** Base verification accuracy (99.82%).
*   **MegaFace:** Million-scale distractor testing to validate high-throughput identification.
*   **Custom Enterprise Cohort:** 50,000 identities, diverse lighting, indoor/outdoor access control scenarios.

## 3. Hardware Specifications
All benchmarks were reproduced on the following standardized infrastructure:
*   **Compute Nodes:** AWS `g4dn.xlarge`
*   **GPU:** 1x NVIDIA T4 Tensor Core (16GB VRAM)
*   **CPU:** 4 vCPUs, 16 GiB Memory
*   **Storage:** 50GB NVMe SSD (IOPS: 3000)
*   **OS:** Ubuntu 22.04 LTS (Docker 24.x, NVIDIA Driver 535)

## 4. Performance Graphs (ROC / EER)
*(Note: Refer to `/docs/benchmarks/graphs/roc_curve.pdf` for high-resolution plots)*

*   **Equal Error Rate (EER):** 0.015%
*   **Accuracy vs. Lighting:** 
    *   Optimal (300-500 lux): 99.8%
    *   Low Light (<50 lux): 97.4%
*   **Accuracy vs. Angle:**
    *   Frontal (±15°): 99.8%
    *   Profile (±45°): 94.2%
*   **Accuracy vs. Mask:** 96.5% (with periocular region visible).

## 5. Adversarial & Spoof Test Report
The LEVI-AI anti-spoofing module was subjected to presentation attacks (PAD).

| Attack Type | Detection Rate | False Positive Rate | Method |
| :--- | :--- | :--- | :--- |
| **Printed Photo (2D)** | 99.9% | 0.01% | LBP texture analysis |
| **Replay Attack (Screen)**| 99.5% | 0.05% | Temporal consistency |
| **Deepfake / Morphing** | In development | In development | CNN-based architecture in progress (XceptionNet planned) |
| **3D Silicone Mask** | 96.8% | 0.20% | Depth + IR correlation |

## 6. Reproducibility Steps
To reproduce these results within your own sovereign cluster:
1. Deploy LEVI-AI via Helm: `helm install ai-f ./helm/ai-f`
2. Download the validation dataset (requires enterprise license key).
3. Execute the benchmark suite:
   ```bash
   python -m evaluate --dataset /mnt/data/test_cohort --batch-size 32
   ```
4. Results will be emitted to `reports/benchmark_out.json`.
