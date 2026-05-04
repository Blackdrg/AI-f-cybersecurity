export interface Log {
  timestamp: string;
  action: string;
  person_id?: string;
  details: Record<string, any>;
  user_id?: string;
}

