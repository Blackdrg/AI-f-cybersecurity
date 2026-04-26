import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import API from '../services/api';
import { useNavigate } from 'react-router-dom';

const AuthContext = createContext(null);

export const ROLES = {
  SUPER_ADMIN: 'super_admin',
  ADMIN: 'admin',
  OPERATOR: 'operator',
  AUDITOR: 'auditor',
  ANALYST: 'analyst',
  VIEWER: 'viewer'
};

export const PERMISSIONS = {
  // Dashboard & Overview
  VIEW_DASHBOARD: 'view_dashboard',
  VIEW_ANALYTICS: 'view_analytics',
  
  // Identity Management
  ENROLL_IDENTITY: 'enroll_identity',
  VIEW_IDENTITIES: 'view_identities',
  EDIT_IDENTITY: 'edit_identity',
  DELETE_IDENTITY: 'delete_identity',
  MERGE_IDENTITIES: 'merge_identities',
  
  // Recognition & Monitoring
  VIEW_RECOGNITIONS: 'view_recognitions',
  VIEW_LIVE_SESSIONS: 'view_live_sessions',
  TERMINATE_SESSION: 'terminate_session',
  
  // Alerts & Incidents
  VIEW_ALERTS: 'view_alerts',
  CREATE_ALERT_RULE: 'create_alert_rule',
  MANAGE_INCIDENTS: 'manage_incidents',
  ESCALATE_INCIDENT: 'escalate_incident',
  
  // Audit & Compliance
  VIEW_AUDIT_LOGS: 'view_audit_logs',
  VIEW_FORENSIC_TRACE: 'view_forensic_trace',
  VERIFY_CHAIN: 'verify_chain',
  EXPORT_DATA: 'export_data',
  DELETE_DATA: 'delete_data',
  VIEW_COMPLIANCE: 'view_compliance',
  
  // System Administration
  MANAGE_USERS: 'manage_users',
  MANAGE_ORGS: 'manage_orgs',
  MANAGE_POLICIES: 'manage_policies',
  VIEW_SYSTEM_HEALTH: 'view_system_health',
  
  // API & Integration
  MANAGE_API_KEYS: 'manage_api_keys',
  CONFIGURE_INTEGRATIONS: 'configure_integrations',
  
  // Deepfake & Security
  VIEW_THREATS: 'view_threats',
  MANAGE_SECURITY: 'manage_security',
  
  // Explainable AI
  VIEW_EXPLANATIONS: 'view_explanations',
  VIEW_BIAS_REPORTS: 'view_bias_reports',
  
  // Billing
  VIEW_BILLING: 'view_billing',
  MANAGE_SUBSCRIPTION: 'manage_subscription'
};

// Role-to-Permission mapping
export const ROLE_PERMISSIONS = {
  [ROLES.SUPER_ADMIN]: Object.values(PERMISSIONS),
  [ROLES.ADMIN]: [
    PERMISSIONS.VIEW_DASHBOARD,
    PERMISSIONS.VIEW_ANALYTICS,
    PERMISSIONS.ENROLL_IDENTITY,
    PERMISSIONS.VIEW_IDENTITIES,
    PERMISSIONS.EDIT_IDENTITY,
    PERMISSIONS.MERGE_IDENTITIES,
    PERMISSIONS.VIEW_RECOGNITIONS,
    PERMISSIONS.VIEW_LIVE_SESSIONS,
    PERMISSIONS.VIEW_ALERTS,
    PERMISSIONS.CREATE_ALERT_RULE,
    PERMISSIONS.MANAGE_INCIDENTS,
    PERMISSIONS.VIEW_AUDIT_LOGS,
    PERMISSIONS.VIEW_FORENSIC_TRACE,
    PERMISSIONS.VIEW_COMPLIANCE,
    PERMISSIONS.MANAGE_USERS,
    PERMISSIONS.MANAGE_ORGS,
    PERMISSIONS.MANAGE_POLICIES,
    PERMISSIONS.VIEW_SYSTEM_HEALTH,
    PERMISSIONS.MANAGE_API_KEYS,
    PERMISSIONS.VIEW_THREATS,
    PERMISSIONS.MANAGE_SECURITY,
    PERMISSIONS.VIEW_EXPLANATIONS,
    PERMISSIONS.VIEW_BIAS_REPORTS,
    PERMISSIONS.VIEW_BILLING,
    PERMISSIONS.MANAGE_SUBSCRIPTION,
    PERMISSIONS.EXPORT_DATA,
    PERMISSIONS.DELETE_DATA
  ],
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
  [ROLES.ANALYST]: [
    PERMISSIONS.VIEW_DASHBOARD,
    PERMISSIONS.VIEW_ANALYTICS,
    PERMISSIONS.VIEW_RECOGNITIONS,
    PERMISSIONS.VIEW_LIVE_SESSIONS,
    PERMISSIONS.VIEW_EXPLANATIONS,
    PERMISSIONS.VIEW_BIAS_REPORTS,
    PERMISSIONS.VIEW_IDENTITIES
  ],
  [ROLES.VIEWER]: [
    PERMISSIONS.VIEW_DASHBOARD,
    PERMISSIONS.VIEW_RECOGNITIONS,
    PERMISSIONS.VIEW_IDENTITIES
  ]
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [organization, setOrganization] = useState(null);
  const [organizations, setOrganizations] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    const storedOrg = localStorage.getItem('organization');
    const orgs = localStorage.getItem('organizations');
    
    if (storedUser) {
      const parsedUser = JSON.parse(storedUser);
      setUser(parsedUser);
      
      if (orgs) {
        const parsedOrgs = JSON.parse(orgs);
        setOrganizations(parsedOrgs);
        
        if (storedOrg) {
          const parsedOrg = JSON.parse(storedOrg);
          setOrganization(parsedOrg);
        } else if (parsedOrgs.length > 0) {
          setOrganization(parsedOrgs[0]);
        }
      }
    }
    setLoading(false);
  }, []);

  const hasPermission = (permission) => {
    if (!user?.role) return false;
    const userRole = user.role.toLowerCase();
    const permissions = ROLE_PERMISSIONS[userRole] || [];
    return permissions.includes(permission);
  };

  const canAccessRoute = (requiredPermissions) => {
    if (!requiredPermissions || requiredPermissions.length === 0) return true;
    return requiredPermissions.some(permission => hasPermission(permission));
  };

  const switchOrganization = (org) => {
    setOrganization(org);
    localStorage.setItem('organization', JSON.stringify(org));
  };

  const login = async (userData, orgsData) => {
    setUser(userData);
    setOrganizations(orgsData);
    if (orgsData.length > 0) {
      const defaultOrg = orgsData.find(o => o.is_default) || orgsData[0];
      setOrganization(defaultOrg);
      localStorage.setItem('organization', JSON.stringify(defaultOrg));
    }
    localStorage.setItem('user', JSON.stringify(userData));
    localStorage.setItem('organizations', JSON.stringify(orgsData));
  };

  const logout = () => {
    setUser(null);
    setOrganization(null);
    setOrganizations([]);
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    localStorage.removeItem('organization');
    localStorage.removeItem('organizations');
    navigate('/login');
  };

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
  }), [user, organization, organizations, loading]);

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