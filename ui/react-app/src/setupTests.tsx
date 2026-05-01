import '@testing-library/jest-dom';

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  observe() { return null; }
  unobserve() {}
  disconnect() {}
};

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
class WebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  constructor(url) {
    this.url = url;
    this.readyState = WebSocket.CONNECTING;
    setTimeout(() => { this.readyState = WebSocket.OPEN; }, 0);
  }
  send(data) {}
  close() {}
  addEventListener(event, handler) {
    this[event] = handler;
  }
  removeEventListener(event) {}
  dispatchEvent(event) {}
}

global.WebSocket = WebSocket;

// Suppress console.error in tests (optional)
// console.error = jest.fn();
