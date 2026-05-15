import React, { createContext, useContext, useState, useEffect, useMemo, useCallback, ReactNode } from 'react';

export type UserRole = 'super_admin' | 'admin' | 'operator' | 'auditor' | 'analyst' | 'viewer' | 'security' | 'hr';

export interface User {
  user_id: string;
  email: string;
  name: string;
  role: UserRole;
  subscription_tier: string;
}

export interface Organization {
  org_id: string;
  name: string;
  subscription_tier: string;
  is_default?: boolean;
  billing_email?: string;
}

export interface AuthContextType {
  user: User | null;
  organization: Organization | null;
  organizations: Organization[];
  loading: boolean;
  hasPermission: (permission: string) => boolean;
  canAccessRoute: (requiredPermissions: string[]) => boolean;
  switchOrganization: (org: Organization) => void;
  login: (userData: User, orgsData: Organization[]) => Promise<void>;
  logout: () => void;
  userRole: string | undefined;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const ROLES = {
  SUPER_ADMIN: 'super_admin' as UserRole,
  ADMIN: 'admin' as UserRole,
  OPERATOR: 'operator' as UserRole,
  AUDITOR: 'auditor' as UserRole,
  ANALYST: 'analyst' as UserRole,
  VIEWER: 'viewer' as UserRole,
  SECURITY: 'security' as UserRole,
  HR: 'hr' as UserRole
};

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
  MANAGE_SUBSCRIPTION: 'manage_subscription'
};

export const ROLE_PERMISSIONS: Record<string, string[]> = {
  [ROLES.SUPER_ADMIN]: Object.values(PERMISSIONS),
  [ROLES.ADMIN]: Object.values(PERMISSIONS), // Admin has all for now
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
    PERMISSIONS.VIEW_EXPLANATIONS
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
    PERMISSIONS.VIEW_RECOGNITIONS
  ],
  [ROLES.VIEWER]: [
    PERMISSIONS.VIEW_DASHBOARD,
    PERMISSIONS.VIEW_RECOGNITIONS,
    PERMISSIONS.VIEW_IDENTITIES
  ]
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);

   useEffect(() => {
     // Check auth state without reading token from localStorage (httpOnly cookie)
     const checkAuth = async () => {
       try {
         const baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
         const res = await fetch(`${baseURL}/api/users/me`, {
           credentials: 'include',  // Required for httpOnly cookies
         });
        if (res.ok) {
          const userData = await res.json();
          setUser(userData);
          // Get orgs from local storage only (not auth-sensitive)
          const storedOrgs = localStorage.getItem('organizations');
          const storedOrg = localStorage.getItem('organization');
          if (storedOrgs) {
            const parsedOrgs = JSON.parse(storedOrgs);
            setOrganizations(parsedOrgs);
            if (storedOrg) {
              const parsedOrg = JSON.parse(storedOrg);
              setOrganization(parsedOrg);
            } else if (parsedOrgs.length > 0) {
              setOrganization(parsedOrgs[0]);
            }
          }
        }
      } catch (e) {
        console.error("Auth check failed", e);
      } finally {
        setLoading(false);
      }
    };
    checkAuth();
  }, []);

  const hasPermission = useMemo(() => (permission: string): boolean => {
    if (!user?.role) return false;
    const userRole = user.role.toLowerCase();
    const permissions = ROLE_PERMISSIONS[userRole] || [];
    return permissions.includes(permission);
  }, [user?.role]);

  const canAccessRoute = useMemo(() => (requiredPermissions: string[]): boolean => {
    if (!requiredPermissions || requiredPermissions.length === 0) return true;
    return requiredPermissions.some(permission => hasPermission(permission));
  }, [hasPermission]);

  const switchOrganization = useCallback((org: Organization) => {
    setOrganization(org);
    localStorage.setItem('organization', JSON.stringify(org));
  }, []);

  const login = useCallback(async (userData: User, orgsData: Organization[]) => {
    setUser(userData);
    setOrganizations(orgsData);
    if (orgsData.length > 0) {
      const defaultOrg = orgsData.find(o => o.is_default) || orgsData[0];
      setOrganization(defaultOrg);
      localStorage.setItem('organization', JSON.stringify(defaultOrg));
    }
    // Non-auth data only in localStorage (httpOnly cookie handles auth)
    localStorage.setItem('organizations', JSON.stringify(orgsData));
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setOrganization(null);
    setOrganizations([]);
    localStorage.removeItem('organization');
    localStorage.removeItem('organizations');
    // Call backend logout to clear httpOnly cookie
    const baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    fetch(`${baseURL}/api/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    }).finally(() => {
      window.location.reload();
    });
  }, []);

  const value = useMemo(() => ({
    user,
    organization,
    organizations,
    loading,
    hasPermission,
    canAccessRoute,
    switchOrganization,
    login,
    logout,
    userRole: user?.role?.toLowerCase()
  }), [user, organization, organizations, loading, hasPermission, canAccessRoute, switchOrganization, login, logout]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};


