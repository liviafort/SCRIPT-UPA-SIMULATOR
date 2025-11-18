import axios, { AxiosInstance } from 'axios';
import { AuthConfig, AuthResponse } from './types';

export class APIClient {
  private client: AxiosInstance;
  private baseUrl: string;
  private authConfig?: AuthConfig;
  private token?: string;
  private tokenExpiration?: number;

  constructor(baseUrl: string, authConfig?: AuthConfig) {
    this.baseUrl = baseUrl;
    this.authConfig = authConfig;
    this.client = axios.create({
      baseURL: baseUrl,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    this.client.interceptors.request.use(async (config) => {
      if (this.authConfig && config.url !== this.authConfig.endpoints.login) {
        await this.ensureAuthenticated();
        if (this.token) {
          config.headers.Authorization = `Bearer ${this.token}`;
        }
      }
      return config;
    });
  }

  private async ensureAuthenticated(): Promise<void> {
    if (!this.authConfig) return;

    const now = Date.now();

    if (!this.token || !this.tokenExpiration) {
      await this.login();
      return;
    }

    if (this.tokenExpiration - now < 300000) {
      try {
        await this.refreshToken();
      } catch (error) {
        console.warn('[AUTH] Refresh token falhou, fazendo login novamente');
        await this.login();
      }
    }
  }

  private async login(): Promise<void> {
    if (!this.authConfig) return;

    try {
      const loginUrl = `${this.authConfig.base_url}${this.authConfig.endpoints.login}`;
      const response = await axios.post<{ data: AuthResponse }>(loginUrl, {
        username: this.authConfig.username,
        password: this.authConfig.password
      });

      if (response.data?.data?.token) {
        this.token = response.data.data.token;
        const expiresInMs = (response.data.data.expiresIn || 86400) * 1000;
        this.tokenExpiration = Date.now() + expiresInMs;

        const expiresInHours = Math.floor(expiresInMs / 3600000);
        console.log(`[AUTH] Login realizado com sucesso (expira em ${expiresInHours}h)`);
      }
    } catch (error) {
      console.error('[AUTH ERROR] Falha ao fazer login:', error instanceof Error ? error.message : error);
      throw error;
    }
  }

  private async refreshToken(): Promise<void> {
    if (!this.authConfig || !this.token) return;

    try {
      const refreshUrl = `${this.authConfig.base_url}${this.authConfig.endpoints.refresh}`;
      const response = await axios.post<{ data: AuthResponse }>(
        refreshUrl,
        {},
        {
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        }
      );

      if (response.data?.data?.token) {
        this.token = response.data.data.token;
        const expiresInMs = (response.data.data.expiresIn || 86400) * 1000;
        this.tokenExpiration = Date.now() + expiresInMs;

        const expiresInHours = Math.floor(expiresInMs / 3600000);
        console.log(`[AUTH] Token renovado com sucesso (expira em ${expiresInHours}h)`);
      }
    } catch (error) {
      console.error('[AUTH ERROR] Falha ao renovar token:', error instanceof Error ? error.message : error);
      throw error;
    }
  }

  private async retryWithBackoff<T>(
    operation: () => Promise<T>,
    maxRetries: number = 3,
    baseDelay: number = 100
  ): Promise<T | null> {
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error: any) {
        const isLastAttempt = attempt === maxRetries;
        const isDNSError = error?.code === 'EAI_AGAIN' || error?.code === 'ENOTFOUND';
        const isNetworkError = error?.code === 'ECONNRESET' || error?.code === 'ETIMEDOUT';

        if (isLastAttempt || (!isDNSError && !isNetworkError)) {
          throw error;
        }

        const delay = baseDelay * Math.pow(2, attempt) + Math.random() * 100;
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
    return null;
  }

  async get<T = any>(endpoint: string): Promise<T | null> {
    try {
      const result = await this.retryWithBackoff(async () => {
        const response = await this.client.get<T>(endpoint);
        return response.data;
      });
      return result;
    } catch (error) {
      console.error(`[API ERROR] GET ${this.baseUrl}${endpoint}:`, error instanceof Error ? error.message : error);
      return null;
    }
  }

  async post<T = any>(endpoint: string, data: any): Promise<T | null> {
    try {
      const result = await this.retryWithBackoff(async () => {
        const response = await this.client.post<T>(endpoint, data);
        return response.data;
      });
      return result;
    } catch (error) {
      console.error(`[API ERROR] POST ${this.baseUrl}${endpoint}:`, error instanceof Error ? error.message : error);
      return null;
    }
  }
}
