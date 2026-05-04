export interface RecognitionResult {
  faces: Face[];
  timestamp?: string;
  camera_id?: string;
  risk_score?: number;
}

