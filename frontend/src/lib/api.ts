/**
 * API Client with JWT Authentication
 * Sprint 38 Feature 38.1b: JWT Authentication Frontend
 */

import type { LoginRequest, LoginResponse, User, TokenData } from '../types/auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const TOKEN_STORAGE_KEY = 'aegis_auth_token';
const DEFAULT_TIMEOUT_MS = 15000; // 15 seconds timeout

/**
 * Create an AbortController with timeout
 */
function createTimeoutController(timeoutMs: number = DEFAULT_TIMEOUT_MS): AbortController {
  const controller = new AbortController();
  setTimeout(() => controller.abort(), timeoutMs);
  return controller;
}

/**
 * API Client class with JWT token management
 */
export class ApiClient {
  private static instance: ApiClient;
  private tokenData: TokenData | null = null;
  private onUnauthorized?: () => void;

  private constructor() {
    this.loadToken();
  }

  static getInstance(): ApiClient {
    if (!ApiClient.instance) {
      ApiClient.instance = new ApiClient();
    }
    return ApiClient.instance;
  }

  /**
   * Set callback to be called on 401 Unauthorized responses
   */
  setUnauthorizedCallback(callback: () => void) {
    this.onUnauthorized = callback;
  }

  /**
   * Load token from localStorage
   */
  private loadToken() {
    const stored = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (stored) {
      try {
        this.tokenData = JSON.parse(stored);
        // Check if token is expired
        if (this.tokenData && this.isTokenExpired()) {
          this.clearToken();
        }
      } catch (e) {
        console.error('Failed to parse stored token:', e);
        this.clearToken();
      }
    }
  }

  /**
   * Save token to localStorage
   */
  private saveToken(tokenData: TokenData) {
    this.tokenData = tokenData;
    localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokenData));
  }

  /**
   * Clear token from memory and localStorage
   */
  private clearToken() {
    this.tokenData = null;
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }

  /**
   * Check if current token is expired
   */
  isTokenExpired(): boolean {
    if (!this.tokenData) return true;
    return Date.now() >= this.tokenData.expiresAt;
  }

  /**
   * Get authorization headers with JWT token
   */
  getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (this.tokenData && !this.isTokenExpired()) {
      headers['Authorization'] = `Bearer ${this.tokenData.token}`;
    }

    return headers;
  }

  /**
   * Handle API response and check for 401
   */
  private async handleResponse<T>(response: Response): Promise<T> {
    if (response.status === 401) {
      this.clearToken();
      if (this.onUnauthorized) {
        this.onUnauthorized();
      }
      throw new Error('Unauthorized');
    }

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`HTTP ${response.status}: ${error}`);
    }

    return response.json();
  }

  /**
   * Generic GET request
   */
  async get<T>(endpoint: string): Promise<T> {
    const controller = createTimeoutController();
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'GET',
        headers: this.getHeaders(),
        signal: controller.signal,
      });
      return this.handleResponse<T>(response);
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Request timeout: Server at ${API_BASE_URL} did not respond within 15 seconds. Please check if the backend is accessible.`);
      }
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(`Network error: Cannot connect to ${API_BASE_URL}. Please check if the backend is running and accessible.`);
      }
      throw error;
    }
  }

  /**
   * Generic POST request
   */
  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    const controller = createTimeoutController();
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: data ? JSON.stringify(data) : undefined,
        signal: controller.signal,
      });
      return this.handleResponse<T>(response);
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Request timeout: Server at ${API_BASE_URL} did not respond within 15 seconds. Please check if the backend is accessible.`);
      }
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(`Network error: Cannot connect to ${API_BASE_URL}. Please check if the backend is running and accessible.`);
      }
      throw error;
    }
  }

  /**
   * Generic PATCH request
   */
  async patch<T>(endpoint: string, data?: unknown): Promise<T> {
    const controller = createTimeoutController();
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'PATCH',
        headers: this.getHeaders(),
        body: data ? JSON.stringify(data) : undefined,
        signal: controller.signal,
      });
      return this.handleResponse<T>(response);
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Request timeout: Server at ${API_BASE_URL} did not respond within 15 seconds. Please check if the backend is accessible.`);
      }
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(`Network error: Cannot connect to ${API_BASE_URL}. Please check if the backend is running and accessible.`);
      }
      throw error;
    }
  }

  /**
   * Generic DELETE request
   */
  async delete<T>(endpoint: string): Promise<T> {
    const controller = createTimeoutController();
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'DELETE',
        headers: this.getHeaders(),
        signal: controller.signal,
      });
      return this.handleResponse<T>(response);
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Request timeout: Server at ${API_BASE_URL} did not respond within 15 seconds. Please check if the backend is accessible.`);
      }
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(`Network error: Cannot connect to ${API_BASE_URL}. Please check if the backend is running and accessible.`);
      }
      throw error;
    }
  }

  /**
   * Login and store JWT token
   */
  async login(credentials: LoginRequest): Promise<User> {
    const controller = createTimeoutController();
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Login failed: ${error}`);
      }

      const data: LoginResponse = await response.json();

      // Calculate expiration timestamp
      const expiresAt = Date.now() + data.expires_in * 1000;

      // Store token
      this.saveToken({
        token: data.access_token,
        expiresAt,
      });

      return data.user;
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Login timeout: Server at ${API_BASE_URL} did not respond within 15 seconds. Please ensure port 8000 is forwarded in VS Code.`);
      }
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(`Network error: Cannot connect to ${API_BASE_URL}. Please forward port 8000 in VS Code or check if the backend is running.`);
      }
      throw error;
    }
  }

  /**
   * Logout and clear token
   */
  async logout(): Promise<void> {
    try {
      // Call backend logout endpoint if token exists
      if (this.tokenData && !this.isTokenExpired()) {
        await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
          method: 'POST',
          headers: this.getHeaders(),
        });
      }
    } catch (e) {
      console.error('Logout API call failed:', e);
    } finally {
      // Always clear local token
      this.clearToken();
    }
  }

  /**
   * Get current user info
   */
  async getCurrentUser(): Promise<User> {
    return this.get<User>('/api/v1/auth/me');
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return this.tokenData !== null && !this.isTokenExpired();
  }
}

// Export singleton instance
export const apiClient = ApiClient.getInstance();
