import axios from 'axios';
import type {
  FilterRequest,
  FilterResponse,
  MetadataResponse,
  HealthResponse,
  ClusterStats,
  AggregatedChartsResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8100';

const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Include cookies for SAML session
});

// Add response interceptor to handle authentication errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to SAML login on authentication error
      console.log('401 Unauthorized from apiClient - Redirecting to SAML login');
      const currentUrl = window.location.href;
      window.location.replace(`${API_BASE_URL}/saml/login?redirect_to=${encodeURIComponent(currentUrl)}`);
      return new Promise(() => {}); // Never resolve to prevent further execution
    }
    return Promise.reject(error);
  }
);

// Add global axios interceptor for SAML auth errors
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/saml/login')) {
      // Redirect to SAML login on authentication error
      console.log('401 Unauthorized from axios - Redirecting to SAML login', error.config?.url);
      const currentUrl = window.location.href;
      window.location.replace(`${API_BASE_URL}/saml/login?redirect_to=${encodeURIComponent(currentUrl)}`);
      return new Promise(() => {}); // Never resolve to prevent further execution
    }
    return Promise.reject(error);
  }
);

export interface UserInfo {
  username: string;
  email: string | null;
  is_admin: boolean;
  attributes: Record<string, unknown>;
}

export const authApi = {
  getCurrentUser: async (): Promise<UserInfo> => {
    const response = await axios.get<UserInfo>(`${API_BASE_URL}/saml/me`, {
      withCredentials: true,
    });
    return response.data;
  },
};

export const dashboardApi = {
  getHealth: async (): Promise<HealthResponse> => {
    const response = await apiClient.get<HealthResponse>('/dashboard/health');
    return response.data;
  },

  getMetadata: async (params?: { hostname?: string; start_date?: string; end_date?: string }): Promise<MetadataResponse> => {
    const response = await apiClient.get<MetadataResponse>('/dashboard/metadata', { params });
    return response.data;
  },

  filterData: async (request: FilterRequest): Promise<FilterResponse> => {
    const response = await apiClient.post<FilterResponse>('/dashboard/filter', request);
    return response.data;
  },

  getAggregatedCharts: async (request: FilterRequest): Promise<AggregatedChartsResponse> => {
    const response = await apiClient.post<AggregatedChartsResponse>('/dashboard/charts', request);
    return response.data;
  },

  getClusterStats: async (
    hostname: string,
    startDate?: string,
    endDate?: string
  ): Promise<ClusterStats> => {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const response = await apiClient.get<ClusterStats>(
      `/dashboard/stats/${hostname}?${params.toString()}`
    );
    return response.data;
  },
};

export const reportsApi = {
  previewReport: async (
    hostname: string,
    type: 'monthly' | 'quarterly' | 'annual',
    year: number,
    month?: number,
    quarter?: number
  ) => {
    const params = new URLSearchParams();
    params.append('hostname', hostname);
    params.append('type', type);
    params.append('year', year.toString());
    if (month !== undefined) {
      params.append('month', month.toString());
    }
    if (quarter !== undefined) {
      params.append('quarter', quarter.toString());
    }

    const response = await apiClient.get(`/reports/preview?${params.toString()}`);
    return response.data;
  },

  downloadReport: (
    hostname: string,
    type: 'monthly' | 'quarterly' | 'annual',
    year: number,
    month: number | undefined,
    quarter: number | undefined,
    format: 'json' | 'csv' | 'pdf'
  ) => {
    const params = new URLSearchParams();
    params.append('hostname', hostname);
    params.append('type', type);
    params.append('year', year.toString());
    params.append('format', format);
    if (month !== undefined) {
      params.append('month', month.toString());
    }
    if (quarter !== undefined) {
      params.append('quarter', quarter.toString());
    }

    window.open(`${API_BASE_URL}/api/reports/generate?${params.toString()}`, '_blank');
  },
};

export default apiClient;
