import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("eaw_access_token");
    const orgId = localStorage.getItem("eaw_org_id");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    if (orgId) {
      config.headers["X-Organization-Id"] = orgId;
    }
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = localStorage.getItem("eaw_refresh_token");
      if (refresh) {
        try {
          const { data } = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
            refresh_token: refresh,
          });
          const payload = data.data;
          localStorage.setItem("eaw_access_token", payload.access_token);
          localStorage.setItem("eaw_refresh_token", payload.refresh_token);
          original.headers.Authorization = `Bearer ${payload.access_token}`;
          return api(original);
        } catch {
          localStorage.removeItem("eaw_access_token");
          localStorage.removeItem("eaw_refresh_token");
        }
      }
    }
    return Promise.reject(error);
  }
);

export type ApiEnvelope<T> = {
  data: T;
  meta: { request_id?: string; total?: number };
};
