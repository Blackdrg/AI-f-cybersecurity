export interface Face {
  face_box: [number, number, number, number];
  score: number;
  spoof_score: number;
  reconstruction_confidence: number;
  confidence: number;
  matches: Match[];
  emotion?: Emotion;
  age?: number;
  gender?: string;
  behavior?: Behavior;
}
export * from './types/index';


export interface Match {
  name: string;
  score: number;
  person_id?: string;
}

export interface Emotion {
  dominant_emotion: string;
  emotions: Record<string, number>;
}

export interface Behavior {
  dominant_behavior: string;
}

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info' | 'warning' | 'error' | 'success';

export interface RecognitionError {
  type: string;
  severity: Severity;
  message: string;
  details?: Record<string, any>;
}

export interface RecognitionResult {
  faces: Face[];
}
