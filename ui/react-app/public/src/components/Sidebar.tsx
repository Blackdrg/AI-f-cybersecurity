import React, { useState } from 'react';
import { 
  Drawer, List, ListItem, ListItemIcon, ListItemText, 
  Toolbar, Divider, Box, Typography, Collapse, ListItemButton,
  Chip, Tooltip, Badge, Avatar
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import {
  ExpandLess, ExpandMore, Shield, Home, PersonAdd, CameraAlt,
  BarChart, Settings, ExitToApp, AdminPanelSettings, Security,
  Videocam, Gavel, Code, Monitor, Radar, NetworkCheck,
  ShowChart, CompareArrows, FilterCenterFocus, BugReport,
  Fingerprint, VisibilityOutlined as Eye, Style, BlurLinear, VerifiedUser, Key,
  Description, Layers, Storage, Public, Policy, Gavel as GavelIcon,
  Warning, Lock, TrendingUp, Analytics, PsychologyOutlined, StorageOutlined,
  VisibilityOutlined, Cloud, Domain, Timeline, AccountCircle, ChevronRight
} from '@mui/icons-material';

interface SidebarProps {
  activePage: string;
  setActivePage: (page: string) => void;
  onLogout: () => void;
  user?: {
    role?: string;
    [key: string]: any;
  };
}

const drawerWidth = 280;

const Sidebar = ({ activePage, setActivePage, onLogout, user }: SidebarProps) => {
  const theme = useTheme();
  const [expandedSections, setExpandedSections] = useState({
    core: true,
    monitoring: true,
    explainability: true,
    security: true,
    governance: true,
    identity: true
  });

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const navSections = [
    {
      key: 'core',
      label: 'Core System',
      icon: <Home />,
      items: [
        { id: 'dashboard', text: 'Dashboard', icon: <Home />, roles: ['super_admin', 'admin', 'operator', 'auditor', 'analyst', 'viewer'] },
        { id: 'enroll', text: 'Identity Enrollment', icon: <PersonAdd />, roles: ['super_admin', 'admin', 'analyst'] },
        { id: 'recognize', text: 'Real-time Recognize', icon: <CameraAlt />, roles: ['super_admin', 'admin', 'operator', 'security'] },
        { id: 'cameras', text: 'Camera Management', icon: <Videocam />, roles: ['super_admin', 'admin', 'operator'] },
      ]
    },
    {
      key: 'monitoring',
      label: 'Continuous Monitoring',
      icon: <Monitor />,
      badge: 3,
      items: [
        { id: 'sessions', text: 'Live Sessions', icon: <Monitor />, roles: ['super_admin', 'admin', 'operator', 'security'] },
        { id: 'analytics', text: 'Behavior Analytics', icon: <Radar />, roles: ['super_admin', 'admin', 'operator', 'auditor', 'analyst'] },
        { id: 'tracking', text: 'Multi-Camera Track', icon: <NetworkCheck />, roles: ['super_admin', 'admin', 'operator', 'security'] },
        { id: 'drift', text: 'Behavior Drift', icon: <TrendingUp />, badge: 2, roles: ['admin'] },
      ]
    },
    {
      key: 'explainability',
      label: 'Explainable AI',
      icon: <PsychologyOutlined />,
      items: [
        { id: 'explanations', text: 'Decision Breakdown', icon: <ShowChart />, roles: ['admin'] },
        { id: 'attribution', text: 'Visual Attribution', icon: <FilterCenterFocus />, roles: ['admin'] },
        { id: 'counterfactuals', text: 'Counterfactual Analysis', icon: <CompareArrows />, roles: ['admin'] },
        { id: 'calibration', text: 'Confidence Calibration', icon: <Analytics />, roles: ['admin'] },
        { id: 'bias-report', text: 'Bias Detection', icon: <AccountCircle />, roles: ['admin'] },
      ]
    },
    {
      key: 'security',
      label: 'Anti-Spoof & Defense',
      icon: <Security />,
      alert: true,
      items: [
        { id: 'deepfake', text: 'Deepfake Detection', icon: <BugReport />, badge: 12, roles: ['admin', 'security'] },
        { id: 'threats', text: 'Threat Intelligence', icon: <StorageOutlined />, roles: ['admin'] },
        { id: 'liveness', text: 'Liveness Analysis', icon: <VisibilityOutlined />, roles: ['admin', 'security'] },
        { id: 'gan-detection', text: 'GAN Artifacts', icon: <Style />, roles: ['admin'] },
        { id: 'watermarks', text: 'Watermark Detect', icon: <BlurLinear />, roles: ['admin'] },
      ]
    },
    {
      key: 'governance',
      label: 'Ethical Governance',
      icon: <GavelIcon />,
      items: [
        { id: 'policies', text: 'Policy Engine', icon: <Policy />, roles: ['admin'] },
        { id: 'jurisdictions', text: 'Cross-Border Rules', icon: <Public />, roles: ['admin'] },
        { id: 'consent', text: 'Consent Mgmt', icon: <VerifiedUser />, roles: ['super_admin', 'admin', 'analyst'] },
        { id: 'ethical-alerts', text: 'Ethical Alerts', icon: <Warning />, badge: 1, roles: ['admin'] },
        { id: 'audit', text: 'Audit Trails', icon: <Key />, roles: ['admin'] },
      ]
    },
    {
      key: 'identity',
      label: 'Decentralized ID',
      icon: <VerifiedUser />,
      items: [
        { id: 'dids', text: 'DID Management', icon: <Key />, roles: ['admin'] },
        { id: 'vc', text: 'Verifiable Credentials', icon: <Description />, roles: ['admin', 'hr'] },
        { id: 'tokens', text: 'Revocable Tokens', icon: <Lock />, roles: ['admin'] },
        { id: 'disclosure', text: 'Selective Disclosure', icon: <Layers />, roles: ['admin'] },
        { id: 'wallet', text: 'Secure Wallet', icon: <StorageOutlined />, roles: ['admin'] },
      ]
    },
  ];

  const menuItems = navSections.flatMap(section => section.items);

  const filteredMenuItems = menuItems.filter(item => 
    !user?.role || item.roles.includes(user.role.toLowerCase())
  );

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        [`& .MuiDrawer-paper`]: { 
          width: drawerWidth, 
          boxSizing: 'border-box',
          background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)',
          borderRight: '1px solid rgba(255,255,255,0.1)',
        },
      }}
    >
      <Toolbar>
        <Box sx={{ width: '100%', display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box sx={{
            width: 40,
            height: 40,
            borderRadius: 2,
            background: 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Shield sx={{ color: 'white', fontSize: 20 }} />
          </Box>
          <Box>
            <Typography variant="subtitle1" sx={{ color: '#f1f5f9', fontWeight: 700, fontSize: '0.9rem' }}>
              Zero-Knowledge ID
            </Typography>
            <Typography variant="caption" sx={{ color: '#64748b' }}>
              Enterprise v2.0
            </Typography>
          </Box>
        </Box>
      </Toolbar>
      
      <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)' }} />
      
      <Box sx={{ overflow: 'auto', display: 'flex', flexDirection: 'column', height: '100%' }}>
        {navSections.map((section) => (
          <Box key={section.key} sx={{ mb: 1 }}>
            <ListItemButton
              onClick={() => toggleSection(section.key)}
              sx={{
                px: 2,
                py: 1,
                minHeight: 40,
                borderRadius: 1,
                '&:hover': {
                  background: 'rgba(255,255,255,0.05)',
                },
              }}
            >
              <ListItemIcon sx={{ 
                minWidth: 40, 
                color: expandedSections[section.key] ? '#3b82f6' : '#94a3b8',
                fontSize: 18,
              }}>
                {section.icon}
              </ListItemIcon>
              <Typography variant="body2" sx={{
                flex: 1,
                color: expandedSections[section.key] ? '#f1f5f9' : '#94a3b8',
                fontWeight: expandedSections[section.key] ? 600 : 400,
                fontSize: '0.8rem',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}>
                {section.label}
              </Typography>
              {section.badge && (
                <Badge badgeContent={section.badge} color="error" />
              )}
              {expandedSections[section.key] ? 
                <ExpandLess sx={{ color: '#3b82f6', fontSize: 18 }} /> : 
                <ExpandMore sx={{ color: '#64748b', fontSize: 18 }} />
              }
            </ListItemButton>
            
            <Collapse in={expandedSections[section.key]} timeout="auto" unmountOnExit>
              <List component="div" disablePadding>
                {section.items
                  .filter(item => !user?.role || item.roles.includes(user.role.toLowerCase()))
                  .map((item) => (
                    <ListItemButton
                      key={item.id}
                      selected={activePage === item.id}
                      onClick={() => setActivePage(item.id)}
                      sx={{
                        pl: 4,
                        py: 0.75,
                        borderRadius: 1,
                        mx: 1,
                        mb: 0.5,
                        '&.Mui-selected': {
                          background: 'rgba(59, 130, 246, 0.15)',
                          borderLeft: '3px solid #3b82f6',
                          '&:hover': {
                            background: 'rgba(59, 130, 246, 0.25)',
                          },
                        },
                        '&:hover': {
                          background: 'rgba(255,255,255,0.05)',
                        },
                      }}
                    >
                      <ListItemIcon sx={{ 
                        minWidth: 36, 
                        fontSize: 16,
                        color: activePage === item.id ? '#3b82f6' : '#94a3b8',
                      }}>
                        {item.icon}
                      </ListItemIcon>
                      <ListItemText
                        primary={item.text}
                        primaryTypographyProps={{
                          fontSize: '0.8rem',
                          fontWeight: activePage === item.id ? 600 : 400,
                        }}
                      />
                      {item.badge && (
                        <Badge 
                          badgeContent={item.badge} 
                          color="error"
                          sx={{
                            '& .MuiBadge-badge': {
                              fontSize: '0.7rem',
                              height: 14,
                              minWidth: 14,
                            },
                          }}
                        />
                      )}
                    </ListItemButton>
                  ))}
              </List>
            </Collapse>
          </Box>
        ))}

        <Box sx={{ flexGrow: 1 }} />

        <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)', my: 1 }} />

        {user && (
          <Box sx={{ p: 2, mb: 1 }}>
            <Box sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              mb: 1.5,
            }}>
              <Avatar sx={{
                width: 36,
                height: 36,
                fontSize: '0.8rem',
                bgcolor: '#3b82f6',
              }}>
                {user.name?.[0] || user.email?.[0] || 'U'}
              </Avatar>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="body2" sx={{ 
                  color: '#f1f5f9', 
                  fontWeight: 600,
                  fontSize: '0.8rem',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}>
                  {user.name || user.email}
                </Typography>
                <Typography variant="caption" sx={{ 
                  color: '#64748b',
                  fontSize: '0.7rem',
                  textTransform: 'capitalize',
                }}>
                  {user.role || 'viewer'}
                </Typography>
              </Box>
            </Box>
            <Chip
              label={user.subscription_tier || 'Free Plan'}
              size="small"
              sx={{
                width: '100%',
                justifyContent: 'center',
                fontSize: '0.7rem',
                height: 20,
                bgcolor: 'rgba(59, 130, 246, 0.2)',
                color: '#3b82f6',
                border: '1px solid rgba(59, 130, 246, 0.3)',
              }}
            />
          </Box>
        )}
        
        <ListItemButton
          onClick={onLogout}
          sx={{
            mx: 1,
            mb: 1,
            py: 1,
            borderRadius: 1,
            '&:hover': {
              background: 'rgba(239, 68, 68, 0.1)',
            },
          }}
        >
          <ListItemIcon sx={{ minWidth: 36, color: '#ef4444', fontSize: 18 }}>
            <ExitToApp />
          </ListItemIcon>
          <ListItemText
            primary="Sign Out"
            primaryTypographyProps={{
              fontSize: '0.8rem',
              fontWeight: 500,
            }}
          />
        </ListItemButton>
      </Box>
    </Drawer>
  );
};

export default Sidebar;
