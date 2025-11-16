import axios, { AxiosInstance } from 'axios';

/**
 * Cliente HTTP simplificado para comunicação com a API
 */
export class APIClient {
  private client: AxiosInstance;
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
    this.client = axios.create({
      baseURL: baseUrl,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json'
      }
    });
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
