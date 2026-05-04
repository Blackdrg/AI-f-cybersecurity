export type Severity = "error" | "warning" | "info" | "success";

export interface SnackbarState {
  open: boolean;
  message: string;
  severity: Severity;
}

export interface RecognitionError {
  type: string;
  severity: Severity;
  message: string;
  details?: Record<string, any>;
}

export interface ErrorState {
  hasError: boolean;
  error: Error | null;
}

