/**
 * Authentication Types
 * Sprint 38 Feature 38.1b: JWT Authentication Frontend
 */

export interface User {
  username: string;
  email: string;
  created_at?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export interface TokenData {
  token: string;
  expiresAt: number;
}
