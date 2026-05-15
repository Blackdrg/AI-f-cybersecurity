/**
 * Auth Store — Zustand
 *
 * Replaces AuthContext with a simpler, testable Zustand store.
 * No provider wrapping needed — just import and use.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ─── Types ──────────────────────────────────────────────────────

export type UserRole =
  | 'super_admin'
  | 'admin'
  | 'operator'
  | 'auditor'
  | 'analyst'
  | 'viewer'
  | 'security'
  | 'hr';

export interface User {
  user_id: string;
  email: string;
  name: string;
  role: UserRole;
  subscription_tier: string;
  created_at?: string;
}

export interface Organization {
  org_id: string;
  name: string;
  subscription_tier: string;
  is_default?: boolean;
  billing_email?: string;
}

// ─── Permissions ────────────────────────────────────────────────

export const PERMISSIONS = {
  VIEW_DASHBOARD: 'view_dashboard',
  VIEW_ANALYTICS: 'view_analytics',
  ENROLL_IDENTITY: 'enroll_identity',
  VIEW_IDENTITIES: 'view_identities',
  EDIT_IDENTITY: 'edit_identity',
  DELETE_IDENTITY: 'delete_identity',
  MERGE_IDENTITIES: 'merge_identities',
  VIEW_RECOGNITIONS: 'view_recognitions',
  VIEW_LIVE_SESSIONS: 'view_live_sessions',
  TERMINATE_SESSION: 'terminate_session',
  VIEW_ALERTS: 'view_alerts',
  CREATE_ALERT_RULE: 'create_alert_rule',
  MANAGE_INCIDENTS: 'manage_incidents',
  ESCALATE_INCIDENT: 'escalate_incident',
  VIEW_AUDIT_LOGS: 'view_audit_logs',
  VIEW_FORENSIC_TRACE: 'view_forensic_trace',
  VERIFY_CHAIN: 'verify_chain',
  EXPORT_DATA: 'export_data',
  DELETE_DATA: 'delete_data',
  VIEW_COMPLIANCE: 'view_compliance',
  MANAGE_USERS: 'manage_users',
  MANAGE_ORGS: 'manage_orgs',
  MANAGE_POLICIES: 'manage_policies',
  VIEW_SYSTEM_HEALTH: 'view_system_health',
  MANAGE_API_KEYS: 'manage_api_keys',
  CONFIGURE_INTEGRATIONS: 'configure_integrations',
  VIEW_THREATS: 'view_threats',
  MANAGE_SECURITY: 'manage_security',
  VIEW_EXPLANATIONS: 'view_explanations',
  VIEW_BIAS_REPORTS: 'view_bias_reports',
  VIEW_BILLING: 'view_billing',
  MANAGE_SUBSCRIPTION: 'manage_subscription',
} as const;

export const ROLES = {
  SUPER_ADMIN: 'super_admin' as UserRole,
  ADMIN: 'admin' as UserRole,
  OPERATOR: 'operator' as UserRole,
  AUDITOR: 'auditor' as UserRole,
  ANALYST: 'analyst' as UserRole,
  VIEWER: 'viewer' as UserRole,
  SECURITY: 'security' as UserRole,
  HR: 'hr' as UserRole,
};

const ALL_PERMISSIONS = Object.values(PERMISSIONS);

export const ROLE_PERMISSIONS: Record<string, string[]> = {
  [ROLES.SUPER_ADMIN]: ALL_PERMISSIONS,
  [ROLES.ADMIN]: ALL_PERMISSIONS,
  [ROLES.OPERATOR]: [
    PERMISSIONS.VIEW_DASHBOARD,
    PERMISSIONS.VIEW_RECOGNITIONS,
    PERMISSIONS.VIEW_LIVE_SESSIONS,
    PERMISSIONS.VIEW_IDENTITIES,
    PERMISSIONS.VIEW_ALERTS,
    PERMISSIONS.MANAGE_INCIDENTS,
    PERMISSIONS.TERMINATE_SESSION,
    PERMISSIONS.ESCALATE_INCIDENT,
    PERMISSIONS.VIEW_SYSTEM_HEALTH,
    PERMISSIONS.VIEW_EXPLANATIONS,
  ],
  [ROLES.AUDITOR]: [
    PERMISSIONS.VIEW_DASHBOARD,
    PERMISSIONS.VIEW_ANALYTICS,
    PERMISSIONS.VIEW_AUDIT_LOGS,
    PERMISSIONS.VIEW_FORENSIC_TRACE,
    PERMISSIONS.VERIFY_CHAIN,
    PERMISSIONS.VIEW_COMPLIANCE,
    PERMISSIONS.VIEW_BIAS_REPORTS,
    PERMISSIONS.EXPORT_DATA,
    PERMISSIONS.VIEW_IDENTITIES,
    PERMISSIONS.VIEW_RECOGNITIONS,
  ],
  [ROLES.ANALYST]: [
    PERMISSIONS.VIEW_DASHBOARD,
    PERMISSIONS.VIEW_ANALYTICS,
    PERMISSIONS.ENROLL_IDENTITY,
    PERMISSIONS.VIEW_IDENTITIES,
    PERMISSIONS.VIEW_RECOGNITIONS,
    PERMISSIONS.VIEW_EXPLANATIONS,
    PERMISSIONS.VIEW_BIAS_REPORTS,
  ],
  [ROLES.SECURITY]: [
    PERMISSIONS.VIEW_DASHBOARD,
    PERMISSIONS.VIEW_RECOGNITIONS,
    PERMISSIONS.VIEW_ALERTS,
    PERMISSIONS.VIEW_THREATS,
    PERMISSIONS.MANAGE_SECURITY,
    PERMISSIONS.VIEW_LIVE_SESSIONS,
    PERMISSIONS.MANAGE_INCIDENTS,
  ],
  [ROLES.HR]: [
    PERMISSIONS.VIEW_DASHBOARD,
    PERMISSIONS.VIEW_IDENTITIES,
    PERMISSIONS.ENROLL_IDENTITY,
  ],
  [ROLES.VIEWER]: [
    PERMISSIONS.VIEW_DASHBOARD,
    PERMISSIONS.VIEW_RECOGNITIONS,
    PERMISSIONS.VIEW_IDENTITIES,
  ],
};

// ─── Store ──────────────────────────────────────────────────────

interface AuthState {
  // State
  user: User | null;
  organization: Organization | null;
  organizations: Organization[];
  loading: boolean;
  initialized: boolean;

  // Actions
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  setInitialized: (initialized: boolean) => void;
  login: (userData: User, orgsData: Organization[]) => void;
  logout: () => void;
  switchOrganization: (org: Organization) => void;

  // Computed helpers
  hasPermission: (permission: string) => boolean;
  canAccessRoute: (requiredPermissions: string[]) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      organization: null,
      organizations: [],
      loading: true,
      initialized: false,

      // Setters
      setUser: (user) => set({ user }),
      setLoading: (loading) => set({ loading }),
      setInitialized: (initialized) => set({ initialized }),

      // Login: set user + orgs, select default org
      login: (userData, orgsData) => {
        const defaultOrg = orgsData.find((o) => o.is_default) || orgsData[0] || null;
        set({
          user: userData,
          organizations: orgsData,
          organization: defaultOrg,
          loading: false,
          initialized: true,
        });
      },

      // Logout: clear everything, call backend
      logout: () => {
        set({
          user: null,
          organization: null,
          organizations: [],
          loading: false,
        });
        const baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
        fetch(`${baseURL}/api/auth/logout`, {
          method: 'POST',
          credentials: 'include',
        }).catch(() => {
          // Silent fail on logout endpoint
        });
      },

      // Org switching
      switchOrganization: (org) => set({ organization: org }),

      // Permission checking
      hasPermission: (permission) => {
        const { user } = get();
        if (!user?.role) return false;
        const perms = ROLE_PERMISSIONS[user.role.toLowerCase()] || [];
        return perms.includes(permission);
      },

      canAccessRoute: (requiredPermissions) => {
        if (!requiredPermissions || requiredPermissions.length === 0) return true;
        const { hasPermission } = get();
        return requiredPermissions.some((p) => hasPermission(p));
      },
    }),
    {
      name: 'auth-storage',
      // Only persist non-sensitive org data — auth uses httpOnly cookies
      partialize: (state) => ({
        organization: state.organization,
        organizations: state.organizations,
      }),
    },
  ),
);

// ─── Auth Initialization Hook ───────────────────────────────────

export const initializeAuth = async () => {
  const { setUser, setLoading, setInitialized, login } = useAuthStore.getState();
  try {
    const baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    const res = await fetch(`${baseURL}/api/users/me`, {
      credentials: 'include',
    });
    if (res.ok) {
      const userData = await res.json();
      const { organization, organizations } = useAuthStore.getState();
      if (organizations.length > 0) {
        login(userData, organizations);
      } else {
        setUser(userData);
      }
    }
  } catch (e) {
    console.error('Auth initialization failed:', e);
  } finally {
    setLoading(false);
    setInitialized(true);
  }
};
