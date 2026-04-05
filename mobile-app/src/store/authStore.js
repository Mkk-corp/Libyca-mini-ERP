import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { auth as authApi } from '../api/client';

const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      loading: false,
      error: null,

      login: async (email, password) => {
        set({ loading: true, error: null });
        try {
          const data = await authApi.login(email, password);
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
          set({ user: data.user, isAuthenticated: true, loading: false });
          return true;
        } catch (err) {
          const msg =
            err.response?.data?.detail ||
            err.response?.data?.message ||
            'فشل تسجيل الدخول';
          set({ error: msg, loading: false });
          return false;
        }
      },

      logout: async () => {
        await authApi.logout();
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        set({ user: null, isAuthenticated: false, error: null });
      },

      fetchMe: async () => {
        const token = localStorage.getItem('access_token');
        if (!token) { set({ isAuthenticated: false }); return; }
        try {
          const user = await authApi.me();
          set({ user, isAuthenticated: true });
        } catch {
          set({ isAuthenticated: false, user: null });
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'libyca-auth',
      // Only persist the flag — tokens stay in localStorage separately
      partialize: (s) => ({ isAuthenticated: s.isAuthenticated, user: s.user }),
    }
  )
);

export default useAuthStore;
