import { create } from 'zustand';

interface AuthState {
  token: string | null;
  role: 'Admin' | 'Receptionist' | null;
  setAuth: (token: string, role: 'Admin' | 'Receptionist') => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  role: localStorage.getItem('role') as 'Admin' | 'Receptionist' | null,
  setAuth: (token, role) => {
    localStorage.setItem('token', token);
    localStorage.setItem('role', role);
    set({ token, role });
  },
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    set({ token: null, role: null });
    // Should ideally use window.location or similar to redirect to login
  },
}));
