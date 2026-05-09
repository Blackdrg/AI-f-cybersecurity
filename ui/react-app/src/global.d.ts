export {};

declare global {
  interface Window {
    trackError?: (error: any) => void;
    Stripe?: any;
  }
}
