export interface Face {
  face_box: [number, number, number, number];
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
}

export interface Emotion {
  dominant_emotion: string;
  emotions: Record<string, number>;
}

export interface Behavior {
  dominant_behavior: string;
}

export interface RecognitionResult {
  faces: Face[];
}
