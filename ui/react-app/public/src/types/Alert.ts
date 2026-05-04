export interface Alert {
  id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  message: string;
  timestamp: string;
  category?: string;
  confidence?: number;
  affected_systems?: string[];
  metrics?: Record<string, number>;
}

