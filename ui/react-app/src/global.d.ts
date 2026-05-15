export {};

declare global {
  interface Window {
    trackError?: (error: Record<string, unknown>) => void;
    Stripe?: unknown;
  }
}

// Module declarations for packages without type definitions
declare module 'react-chatbot-kit';
declare module 'react-stripe-js';
declare module 'troika-three-text';
