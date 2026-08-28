/**
 * API client for admin endpoints
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8100';

export interface AdminLoginRequest {
  username: string;
  password: string;
}

export interface AdminLoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface ClusterCreate {
  name: string;
  description?: string;
  contact_email?: string;
  location?: string;
}

export interface ClusterUpdate {
  description?: string;
  contact_email?: string;
  location?: string;
  active?: boolean;
}

export interface Cluster {
  id: string;
  name: string;
  description?: string;
  contact_email?: string;
  location?: string;
  api_key?: string;        // full key, present only in the response that issued it
  api_key_prefix: string;
  api_key_created: string;
  active: boolean;
  created_at: string;
  updated_at: string;
  last_submission?: string;
  total_jobs_submitted: number;

  // Deploy key fields
  deploy_key_created?: string;
  deploy_key_expires_at?: string;
  deploy_key_used?: boolean;
  deploy_key_used_at?: string;
  deploy_key_used_from_ip?: string;
}

export interface ClusterListResponse {
  clusters: Cluster[];
  total: number;
}

export interface APIKeyRotateResponse {
  cluster_id: string;
  new_api_key: string;
  message: string;
}

export interface DeployKeyResponse {
  status: string;
  deploy_key: string;
  message: string;
}

class AdminClient {
  /** Headers for admin API calls made outside this client (Bearer token or SAML cookie). */
  authHeaders(): HeadersInit {
    return this.getAuthHeaders();
  }

  private getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('admin_token');
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    // Add Bearer token if admin_token exists (username/password login)
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    // If no token, rely on cookie-based SAML authentication

    return headers;
  }

  async login(username: string, password: string): Promise<AdminLoginResponse> {
    const response = await fetch(`${API_BASE_URL}/api/admin/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    const data = await response.json();

    // Store token and expiration
    localStorage.setItem('admin_token', data.access_token);
    localStorage.setItem('admin_token_expires',
      (Date.now() + data.expires_in * 1000).toString()
    );

    return data;
  }

  logout(): void {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_token_expires');
  }

  isAuthenticated(): boolean {
    const token = localStorage.getItem('admin_token');
    const expires = localStorage.getItem('admin_token_expires');

    if (!token || !expires) {
      return false;
    }

    // Check if token is expired
    if (Date.now() > parseInt(expires)) {
      this.logout();
      return false;
    }

    return true;
  }

  async getClusters(): Promise<ClusterListResponse> {
    const response = await fetch(`${API_BASE_URL}/api/admin/clusters`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch clusters');
    }

    return response.json();
  }

  async getCluster(id: string): Promise<Cluster> {
    const response = await fetch(`${API_BASE_URL}/api/admin/clusters/${id}`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch cluster');
    }

    return response.json();
  }

  async createCluster(data: ClusterCreate): Promise<Cluster> {
    const response = await fetch(`${API_BASE_URL}/api/admin/clusters`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create cluster');
    }

    return response.json();
  }

  async updateCluster(id: string, data: ClusterUpdate): Promise<Cluster> {
    const response = await fetch(`${API_BASE_URL}/api/admin/clusters/${id}`, {
      method: 'PATCH',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error('Failed to update cluster');
    }

    return response.json();
  }

  async deleteCluster(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/admin/clusters/${id}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to delete cluster');
    }
  }

  async rotateAPIKey(clusterId: string): Promise<APIKeyRotateResponse> {
    const response = await fetch(`${API_BASE_URL}/api/admin/clusters/rotate-key`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ cluster_id: clusterId }),
    });

    if (!response.ok) {
      throw new Error('Failed to rotate API key');
    }

    return response.json();
  }

  async generateDeployKey(clusterId: string): Promise<DeployKeyResponse> {
    const response = await fetch(`${API_BASE_URL}/api/admin/clusters/${clusterId}/deploy-key`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to generate deploy key');
    }

    return response.json();
  }

  async reloadData(): Promise<{ success: boolean; message: string; date_ranges: Record<string, { min_date: string; max_date: string }> }> {
    const response = await fetch(`${API_BASE_URL}/api/data/reload`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to reload data');
    }

    return response.json();
  }
}

export const adminClient = new AdminClient();
