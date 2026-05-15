/**
 * UI Store — Zustand
 *
 * Manages sidebar state, active page, modals, and snackbar notifications.
 * Previously scattered across multiple useState calls in Dashboard.tsx.
 */
import { create } from 'zustand';

// ─── Types ──────────────────────────────────────────────────────

export type SnackbarSeverity = 'success' | 'error' | 'warning' | 'info';

export interface SnackbarState {
  open: boolean;
  message: string;
  severity: SnackbarSeverity;
  duration?: number;
}

interface UIState {
  // Sidebar
  sidebarCollapsed: boolean;
  sidebarWidth: number;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;

  // Active page (replaces activePage useState in Dashboard)
  activePage: string;
  setActivePage: (page: string) => void;

  // Loading overlay
  globalLoading: boolean;
  setGlobalLoading: (loading: boolean) => void;

  // Snackbar / toast queue
  snackbar: SnackbarState;
  showSnackbar: (message: string, severity?: SnackbarSeverity, duration?: number) => void;
  hideSnackbar: () => void;

  // Command palette (future)
  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;

  // Preferences
  reducedMotion: boolean;
  setReducedMotion: (reduced: boolean) => void;
}

// ─── Constants ──────────────────────────────────────────────────

const SIDEBAR_EXPANDED_WIDTH = 280;
const SIDEBAR_COLLAPSED_WIDTH = 72;

// ─── Store ──────────────────────────────────────────────────────

export const useUIStore = create<UIState>()((set, get) => ({
  // Sidebar
  sidebarCollapsed: false,
  sidebarWidth: SIDEBAR_EXPANDED_WIDTH,
  toggleSidebar: () => {
    const collapsed = !get().sidebarCollapsed;
    set({
      sidebarCollapsed: collapsed,
      sidebarWidth: collapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_EXPANDED_WIDTH,
    });
  },
  setSidebarCollapsed: (collapsed) =>
    set({
      sidebarCollapsed: collapsed,
      sidebarWidth: collapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_EXPANDED_WIDTH,
    }),

  // Active page
  activePage: 'dashboard',
  setActivePage: (page) => set({ activePage: page }),

  // Global loading
  globalLoading: false,
  setGlobalLoading: (loading) => set({ globalLoading: loading }),

  // Snackbar
  snackbar: { open: false, message: '', severity: 'success' as const },
  showSnackbar: (message, severity = 'success', duration = 6000) =>
    set({ snackbar: { open: true, message, severity, duration } }),
  hideSnackbar: () =>
    set((state) => ({
      snackbar: { ...state.snackbar, open: false },
    })),

  // Command palette
  commandPaletteOpen: false,
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),

  // Reduced motion
  reducedMotion:
    typeof window !== 'undefined'
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false,
  setReducedMotion: (reduced) => set({ reducedMotion: reduced }),
}));

// ─── Selectors (memoized) ───────────────────────────────────────

export const selectActivePage = (state: UIState) => state.activePage;
export const selectSidebarCollapsed = (state: UIState) => state.sidebarCollapsed;
export const selectSidebarWidth = (state: UIState) => state.sidebarWidth;
export const selectSnackbar = (state: UIState) => state.snackbar;
