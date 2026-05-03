import { render, screen, waitFor } from '@testing-library/react';
import { APIResponse, User } from '../services/api';
import * as api from '../services/api';
import axios from 'axios';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('API Service', () => {
  const mockUser: User = {
    user_id: '123',
    email: 'test@example.com',
    name: 'Test User',
    role: 'user',
    subscription_tier: 'pro',
    created_at: '2024-01-01',
  };

  const mockResponse: APIResponse<User> = {
    success: true,
    data: mockUser,
    error: null,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('login returns user data', async () => {
    mockedAxios.post.mockResolvedValue({ data: mockResponse });

    const result = await api.login('test@example.com', 'password');

    expect(result).toEqual(mockResponse);
    expect(mockedAxios.post).toHaveBeenCalledWith(
      expect.stringContaining('/api/auth/login'),
      expect.anything()
    );
  });

  test('login stores token in sessionStorage for legacy', async () => {
    const mockToken = 'mock-jwt-token';
    mockedAxios.post.mockResolvedValue({ 
      data: { ...mockResponse, access_token: mockToken },
      headers: { 'http-only-cookie': 'false' }
    });

    await api.login('test@example.com', 'password');

    expect(sessionStorage.getItem('token')).toBe(mockToken);
    expect(sessionStorage.getItem('user')).toBe(JSON.stringify(mockUser));
  });

  test('login uses httpOnly cookie in production', async () => {
    mockedAxios.post.mockResolvedValue({ 
      data: mockResponse,
      headers: { 'http-only-cookie': 'true' }
    });

    const consoleSpy = jest.spyOn(console, 'info').mockImplementation();
    await api.login('test@example.com', 'password');
    expect(consoleSpy).toHaveBeenCalledWith('Using httpOnly cookie for auth (production mode)');
    consoleSpy.mockRestore();
  });

  test('recognize uploads file correctly', async () => {
    const mockFile = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
    mockedAxios.post.mockResolvedValue({ data: mockResponse });

    await api.recognize(mockFile);

    expect(mockedAxios.post).toHaveBeenCalledWith('/api/recognize', expect.any(FormData));
  });

  test('error handling in interceptor', async () => {
    const errorMessage = 'Unauthorized';
    mockedAxios.post.mockRejectedValue({
      response: { data: { error: errorMessage } }
    });

    await expect(api.login('bad', 'bad')).rejects.toThrow(errorMessage);
  });

  test('getAnalytics calls correct endpoint', async () => {
    mockedAxios.get.mockResolvedValue({ data: mockResponse });

    await api.getAnalytics('7d');

    expect(mockedAxios.get).toHaveBeenCalledWith('/api/analytics?timeframe=7d');
  });
});
