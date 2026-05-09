import axios from 'axios';
import * as api from '../services/api';

// Use var to avoid TDZ because jest.mock factory runs before imports/declarations due to hoisting
var mockAPIInstance: any;

jest.mock('axios', () => {
  // Create mock instance - will be assigned to outer variable
  mockAPIInstance = {
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() }
    },
    post: jest.fn(),
    get: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  };
  const mockAxios = jest.fn(() => mockAPIInstance);
  (mockAxios as any).create = jest.fn(() => mockAPIInstance);
  return mockAxios;
});

beforeEach(() => {
  jest.clearAllMocks();
  if (mockAPIInstance) {
    mockAPIInstance.post.mockClear();
    mockAPIInstance.get.mockClear();
    mockAPIInstance.put.mockClear();
    mockAPIInstance.delete.mockClear();
  }
});

describe('API Service Authentication', () => {
  test('login calls POST /api/auth/login with credentials', async () => {
    const mockResponse = { success: true, data: { user: { user_id: '123' } } };
    mockAPIInstance.post.mockResolvedValue({ data: mockResponse });

    await (api as any).login('test@example.com', 'password');

    expect(mockAPIInstance.post).toHaveBeenCalledWith(
      '/api/auth/login?email=test%40example.com&password=password'
    );
  });

  test('recognize sends FormData with image file', async () => {
    const mockFile = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
    const mockResponse = { success: true, data: { matches: [] } };
    mockAPIInstance.post.mockResolvedValue({ data: mockResponse });

    await (api as any).recognize(mockFile);

    expect(mockAPIInstance.post).toHaveBeenCalledWith('/api/recognize', expect.any(FormData));
  });

  test('enroll sends FormData with multiple images and metadata', async () => {
    const files = [new File(['a'], 'a.jpg'), new File(['b'], 'b.jpg')];
    const mockResponse = { success: true, data: { person_id: 'p1' } };
    mockAPIInstance.post.mockResolvedValue({ data: mockResponse });

    await (api as any).enroll(files, 'John Doe', true);

    expect(mockAPIInstance.post).toHaveBeenCalledWith('/api/enroll', expect.any(FormData));
  });

  test('logout calls POST /api/auth/logout', async () => {
    mockAPIInstance.post.mockResolvedValue({ data: {} });

   await (api as any).logout();

    expect(mockAPIInstance.post).toHaveBeenCalledWith('/api/auth/logout', {}, { withCredentials: true });
  });
});

describe('API Service Analytics & Health', () => {
  test('getAnalytics calls GET with timeframe', async () => {
    const mockResponse = { success: true, data: { stats: {} } };
    mockAPIInstance.get.mockResolvedValue({ data: mockResponse });

    await (api as any).getAnalytics('7d');

    expect(mockAPIInstance.get).toHaveBeenCalledWith('/api/analytics?timeframe=7d');
  });

  test('getIdentities builds query string', async () => {
    mockAPIInstance.get.mockResolvedValue({ data: { identities: [] } });

    await (api as any).getIdentities({ limit: 10, offset: 20 });

    expect(mockAPIInstance.get).toHaveBeenCalledWith('/api/identities?limit=10&offset=20');
  });

  test('checkHealth GET /api/health', async () => {
    mockAPIInstance.get.mockResolvedValue({ data: { status: 'healthy' } });

    const result = await (api as any).checkHealth();

    expect(mockAPIInstance.get).toHaveBeenCalledWith('/api/health');
    expect(result).toEqual({ status: 'healthy' });
  });

  test('checkDependencies GET /api/health/dependencies', async () => {
    mockAPIInstance.get.mockResolvedValue({ data: { overall: 'healthy' } });

    const result = await (api as any).checkDependencies();

    expect(mockAPIInstance.get).toHaveBeenCalledWith('/api/health/dependencies');
    expect(result.overall).toBe('healthy');
  });
});

describe('API Service Audit & Error Handling', () => {
  test('getAuditLogs builds query with params', async () => {
    mockAPIInstance.get.mockResolvedValue({ data: { logs: [] } });

    await (api as any).getAuditLogs({ action: 'recognize', limit: 50 });

    expect(mockAPIInstance.get).toHaveBeenCalledWith('/api/logs?action=recognize&limit=50');
  });

  // Note: Error transformation is handled by interceptors defined in api.ts module.
  // Those interceptors are installed on the real API instance at module load time.
  // Since we provide a mock instance without the real interceptor logic, detailed
  // error transformation tests are out of scope for this unit test layer.
});
