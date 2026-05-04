export interface Metrics {
  recognition_count: number;
  enroll_count: number;
  avg_latency_ms: number;
  total_embeddings: number;
  spoof_attempts: number;
  bias_metrics?: {
    demographic_parity_difference: number;
    equalized_odds_difference: number;
  };
}

