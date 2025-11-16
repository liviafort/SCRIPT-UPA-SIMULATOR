import axios, { AxiosInstance } from 'axios';
import { AuthConfig, AuthResponse } from './types';

/**
 * Cliente HTTP com suporte a autenticação JWT
 */
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

    // Interceptor para adicionar token automaticamente
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

  /**
   * Garante que o cliente está autenticado com token válido
   */
  private async ensureAuthenticated(): Promise<void> {
    if (!this.authConfig) return;

    // Se não tem token ou token está expirando em menos de 1 minuto, faz login
    const now = Date.now();
    if (!this.token || !this.tokenExpiration || this.tokenExpiration - now < 60000) {
      await this.login();
    }
  }

  /**
   * Realiza login e obtém token JWT
   */
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
        // Define expiração (ou usa 24h como padrão se não vier no response)
        const expiresInMs = (response.data.data.expiresIn || 86400) * 1000;
        this.tokenExpiration = Date.now() + expiresInMs;
        console.log('[AUTH] Login realizado com sucesso');
      }
    } catch (error) {
      console.error('[AUTH ERROR] Falha ao fazer login:', error instanceof Error ? error.message : error);
      throw error;
    }
  }

  async get<T = any>(endpoint: string): Promise<T | null> {
    try {
      const response = await this.client.get<T>(endpoint);
      return response.data;
    } catch (error) {
      console.error(`[API ERROR] GET ${this.baseUrl}${endpoint}:`, error instanceof Error ? error.message : error);
      return null;
    }
  }

  async post<T = any>(endpoint: string, data: any): Promise<T | null> {
    try {
      const response = await this.client.post<T>(endpoint, data);
      return response.data;
    } catch (error) {
      console.error(`[API ERROR] POST ${this.baseUrl}${endpoint}:`, error instanceof Error ? error.message : error);
      return null;
    }
  }
}
