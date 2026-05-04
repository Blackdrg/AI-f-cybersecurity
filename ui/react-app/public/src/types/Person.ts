export interface Person {
  person_id: string;
  name: string;
  embeddings: number[][];
  created_at: string;
  metadata?: Record<string, any>;
  org_id?: string;
}

