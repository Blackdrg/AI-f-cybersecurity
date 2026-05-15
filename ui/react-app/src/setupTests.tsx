import '@testing-library/jest-dom';
jest.mock('axios');

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  root = null;
  rootMargin = '';
  thresholds = [];
  observe() { return null; }
  unobserve() {}
  disconnect() {}
  takeRecords() { return []; }
} as any;

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock WebSocket (partial)
(global as any).WebSocket = class {
  constructor(url: string) { }
  send() { }
  close() {}
};

// Suppress console.error in tests (optional)
// console.error = jest.fn();


