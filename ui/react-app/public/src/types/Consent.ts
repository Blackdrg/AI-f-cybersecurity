export interface Consent {
  user_id: string;
  biometric_type: 'face' | 'voice' | 'gait';
  granted: boolean;
  timestamp: string;
  expires_at?: string;
  metadata?: Record<string, any>;
}

