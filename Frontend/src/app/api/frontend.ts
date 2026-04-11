import { apiClient } from './client';
import { TestCatalogItem, WaitingCandidate } from '../types';

export interface FrontendBootstrapResponse {
  visits: any[];
  labs: any[];
  specialists: any[];
}

export interface FrontendDeltaResponse {
  since?: Date | null;
  now: Date;
  visits: any[];
  labs: any[];
  specialists: any[];
  metrics: any;
}

const stripPrefixedId = (value?: string | null) => {
  if (!value) return null;
  return value.replace(/^[a-z]/i, '');
};

export const frontendApi = {
  bootstrap: async () => {
    const response = await apiClient.get<FrontendBootstrapResponse>('/frontend/bootstrap');
    return response.data;
  },
  delta: async (since?: Date | null) => {
    const response = await apiClient.get<FrontendDeltaResponse>('/frontend/delta', {
      params: since ? { since: since.toISOString() } : undefined,
    });
    return response.data;
  },
  adminDashboard: async () => {
    const response = await apiClient.get('/frontend/admin-dashboard');
    return response.data;
  },
  getTestCatalog: async () => {
    const response = await apiClient.get<{ items: TestCatalogItem[] }>('/frontend/test-catalog');
    return response.data.items;
  },
  createPatient: async (payload: {
    patient_name: string;
    patient_age: number;
    patient_gender: string;
    priority_type: string;
    phone: string;
    test_names: string[];
  }) => {
    const response = await apiClient.post('/frontend/patients', payload);
    return response.data;
  },
  updatePatient: async (visitId: string, payload: {
    patient_name: string;
    patient_age: number;
    patient_gender: string;
    priority_type: string;
    phone: string;
    test_names: string[];
  }) => {
    const response = await apiClient.patch(`/frontend/patients/${visitId}`, payload);
    return response.data;
  },
  createSpecialist: async (payload: {
    name: string;
    gender: string;
    shift_start: string;
    shift_end: string;
  }) => {
    const response = await apiClient.post('/specialists', {
      name: payload.name,
      gender: payload.gender,
      shift_start: `${payload.shift_start}:00`,
      shift_end: `${payload.shift_end}:00`,
      is_active: true,
    });
    return response.data;
  },
  updateSpecialist: async (specialistId: string, payload: {
    name: string;
    gender: string;
    shift_start: string;
    shift_end: string;
  }) => {
    const response = await apiClient.patch(`/specialists/${stripPrefixedId(specialistId)}`, {
      name: payload.name,
      gender: payload.gender,
      shift_start: `${payload.shift_start}:00`,
      shift_end: `${payload.shift_end}:00`,
      is_active: true,
    });
    return response.data;
  },
  deleteSpecialist: async (specialistId: string) => {
    const response = await apiClient.delete(`/specialists/${stripPrefixedId(specialistId)}`);
    return response.data;
  },
  createLab: async (payload: {
    name: string;
    category: string;
    floor: string;
    specialist_id?: string | null;
    is_active: boolean;
  }) => {
    const response = await apiClient.post('/labs', {
      name: payload.name,
      category: payload.category,
      floor: payload.floor,
      room_number: payload.name.replace(/\s+/g, '-').slice(0, 32) || 'AUTO',
      opening_time: '07:00:00',
      closing_time: '19:00:00',
      cleanup_duration_minutes: 0,
      is_active: payload.is_active,
      specialist_id: stripPrefixedId(payload.specialist_id) ? Number(stripPrefixedId(payload.specialist_id)) : null,
    });
    return response.data;
  },
  updateLab: async (
    labId: string,
    payload: {
      name: string;
      category: string;
      floor: string;
      specialist_id?: string | null;
      is_active: boolean;
    }
  ) => {
    const response = await apiClient.patch(`/labs/${stripPrefixedId(labId)}`, {
      name: payload.name,
      category: payload.category,
      floor: payload.floor,
      is_active: payload.is_active,
      specialist_id: stripPrefixedId(payload.specialist_id) ? Number(stripPrefixedId(payload.specialist_id)) : null,
    });
    return response.data;
  },
  deleteLab: async (labId: string) => {
    const response = await apiClient.delete(`/labs/${stripPrefixedId(labId)}`);
    return response.data;
  },
  getWaitingCandidates: async (labId: string) => {
    const response = await apiClient.get<{ lab_id: string; items: WaitingCandidate[] }>(`/labs/${stripPrefixedId(labId)}/waiting-candidates`);
    return response.data;
  },
  getQueueSnapshot: async (labId: string) => {
    const response = await apiClient.get(`/queues/${stripPrefixedId(labId)}`);
    return response.data;
  },
  acceptCurrent: async (labId: string) => {
    const response = await apiClient.post(`/queues/${stripPrefixedId(labId)}/accept-current`);
    return response.data;
  },
  moveCurrentToPending: async (labId: string) => {
    const response = await apiClient.post(`/queues/${stripPrefixedId(labId)}/move-current-to-pending`);
    return response.data;
  },
  acceptFromPending: async (labId: string, visit_test_id?: number) => {
    const response = await apiClient.post(
      `/queues/${stripPrefixedId(labId)}/accept-from-pending`,
      typeof visit_test_id === 'number' ? { visit_test_id } : {}
    );
    return response.data;
  },
  completeCurrent: async (labId: string) => {
    const response = await apiClient.post(`/queues/${stripPrefixedId(labId)}/complete-current`);
    return response.data;
  },
};
