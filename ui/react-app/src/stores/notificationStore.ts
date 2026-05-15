/**
 * Notification Store — Zustand
 *
 * Manages real-time notifications, alert counts, and toast queue.
 */
import { create } from 'zustand';

// ─── Types ──────────────────────────────────────────────────────

export interface Notification {
  id: string;
  type: 'alert' | 'incident' | 'system' | 'ai' | 'security';
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  actionUrl?: string;
  metadata?: Record<string, unknown>;
}

interface NotificationState {
  // State
  notifications: Notification[];
  unreadCount: number;
  criticalAlerts: number;
  pendingIncidents: number;

  // Actions
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  removeNotification: (id: string) => void;
  clearAll: () => void;
  setCriticalAlerts: (count: number) => void;
  setPendingIncidents: (count: number) => void;
  setNotifications: (notifications: Notification[]) => void;
}

// ─── Store ──────────────────────────────────────────────────────

export const useNotificationStore = create<NotificationState>()((set, get) => ({
  notifications: [],
  unreadCount: 0,
  criticalAlerts: 0,
  pendingIncidents: 0,

  addNotification: (notification) => {
    const newNotification: Notification = {
      ...notification,
      id: `notif-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      timestamp: new Date().toISOString(),
      read: false,
    };
    set((state) => ({
      notifications: [newNotification, ...state.notifications].slice(0, 100), // Keep max 100
      unreadCount: state.unreadCount + 1,
    }));
  },

  markAsRead: (id) =>
    set((state) => {
      const notifications = state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n,
      );
      return {
        notifications,
        unreadCount: notifications.filter((n) => !n.read).length,
      };
    }),

  markAllAsRead: () =>
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),

  removeNotification: (id) =>
    set((state) => {
      const notifications = state.notifications.filter((n) => n.id !== id);
      return {
        notifications,
        unreadCount: notifications.filter((n) => !n.read).length,
      };
    }),

  clearAll: () => set({ notifications: [], unreadCount: 0 }),

  setCriticalAlerts: (count) => set({ criticalAlerts: count }),
  setPendingIncidents: (count) => set({ pendingIncidents: count }),
  setNotifications: (notifications) =>
    set({
      notifications,
      unreadCount: notifications.filter((n) => !n.read).length,
    }),
}));
