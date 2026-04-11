import axios from 'axios';
import { useAuthStore } from '../store/useAuthStore';
import { resolveApiBaseUrl } from './resolveApiUrl';

export const apiClient = axios.create({
  baseURL: resolveApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    // Utility to transform ISO strings to Date objects globally
    const transformDates = (data: any): any => {
      if (data === null || data === undefined) return data;
      if (typeof data === 'string') {
        // basic ISO string regex matcher
        const isISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d*)?(?:[-+]\d{2}:\d{2}|Z)?$/.test(data);
        if (isISO) return new Date(data);
        return data;
      }
      if (Array.isArray(data)) {
        return data.map(transformDates);
      }
      if (typeof data === 'object') {
        const transformed: any = {};
        for (const [key, value] of Object.entries(data)) {
          transformed[key] = transformDates(value);
        }
        return transformed;
      }
      return data;
    };

    response.data = transformDates(response.data);
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
  }
);
