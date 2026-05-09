export interface Face {
  person_id?: string;
  name?: string;
  confidence?: number;
  bounding_box?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  emotion?: string;
  age?: number;
  gender?: string;
}

export interface RecognitionResult {
  faces: Face[];
  timestamp?: string;
  camera_id?: string;
  risk_score?: number;
}

