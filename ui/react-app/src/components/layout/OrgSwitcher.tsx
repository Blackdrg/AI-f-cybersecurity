import React, { useState, useEffect } from 'react';
import { Box, Button, Menu, MenuItem, List, ListItem, ListItemText, ListItemButton,
  ListItemIcon, Typography, Chip, Avatar, Divider, Paper,
  IconButton, Tooltip, Card, CardContent,  TextField,
  Dialog, DialogTitle, DialogContent, DialogActions,
  FormControl, InputLabel, Select, LinearProgress } from '@mui/material';
import { Grid } from '@mui/material';
import {
  AccountTree, Add, Settings, AccountCircle,
  Business, Payment, Security, Key, People,
  ChevronRight, ExpandMore, ExpandLess, CheckCircle,
  Error as ErrorIcon, Warning, Info, Store
} from '@mui/icons-material';
import { useAuth, Organization as OrgType } from '../../contexts/AuthContext';
import API from '../../services/api';

interface Subscription {
  plan_name: string;
  monthly_price: number;
  current_period_start: string | null;
  next_invoice_date: string | null;
  status: string;
  recognitions_used: number;
  recognitions_limit: number;
}

interface BillingUsage {
  [orgId: string]: Subscription;
}

export const OrgSwitcher = () => {
  const { organization, organizations, switchOrganization, user, hasPermission } = useAuth();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [createOrgOpen, setCreateOrgOpen] = useState<boolean>(false);
  const [newOrgName, setNewOrgName] = useState<string>('');
  const [newOrgEmail, setNewOrgEmail] = useState<string>('');
  const [orgBilling, setOrgBilling] = useState<BillingUsage>({});

  useEffect(() => {
    // Fetch billing info for current org
    if (organization?.org_id) {
      fetchBillingInfo(organization.org_id);
    }
  }, [organization]);

  const fetchBillingInfo = async (orgId: string) => {
    try {
      const res = await API.get(`/api/subscriptions/org/${orgId}`).catch(() => null);
      if (res?.data) {
        setOrgBilling(prev => ({ ...prev, [orgId]: res.data }));
      }
    } catch (err: any) {
      console.warn('Failed to fetch billing info');
    }
  };

  const handleOrgSwitch = (org: OrgType) => {
    switchOrganization(org);
    setAnchorEl(null);
  };

  const handleCreateOrg = async () => {
    try {
      const res = await API.post('/api/organizations', {
        name: newOrgName,
        billing_email: newOrgEmail
      });
      const newOrgs = [...organizations, res.data];
      // Update auth context
      // Note: In production, refetch orgs from backend
      switchOrganization(res.data);
      setCreateOrgOpen(false);
      setNewOrgName('');
      setNewOrgEmail('');
    } catch (err: any) {
      console.error('Failed to create organization:', err);
    }
  };

  const getTierColor = (tier: string | undefined) => {
    const colors: Record<string, string> = {
      free: '#64748b',
      pro: '#3b82f6',
      enterprise: '#8b5cf6',
      custom: '#f59e0b'
    };
    return tier ? (colors[tier.toLowerCase()] || '#64748b') : '#64748b';
  };

  const getTierFeatures = (tier: string | undefined) => {
    const features: Record<string, string[]> = {
      free: ['Up to 5 users', '10,000 recognitions/mo', 'Basic support'],
      pro: ['Up to 50 users', '100,000 recognitions/mo', 'Priority support', 'Advanced analytics'],
      enterprise: ['Unlimited users', 'Unlimited recognitions', '24/7 support', 'Custom deployments', 'SLA guarantee']
    };
    return tier ? (features[tier.toLowerCase()] || features.free) : features.free;
  };

  const currentTier = organization?.subscription_tier || 'free';

  return (
    <>
      <Button
        variant="outlined"
        startIcon={<AccountTree />}
        endIcon={anchorEl ? <ExpandLess /> : <ExpandMore />}
        onClick={(e) => setAnchorEl(e.currentTarget)}
        sx={{
          borderColor: 'rgba(255,255,255,0.2)',
          color: '#e2e8f0',
          textTransform: 'none',
          minWidth: '200px',
          justifyContent: 'space-between',
          '&:hover': {
            borderColor: 'rgba(255,255,255,0.4)',
            backgroundColor: 'rgba(255,255,255,0.05)'
          }
        }}
      >
        <Box sx={{ textAlign: 'left' }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {organization?.name || 'Select Organization'}
          </Typography>
          <Typography variant="caption" sx={{ opacity: 0.7 }}>
            {currentTier.charAt(0).toUpperCase() + currentTier.slice(1)} Plan
          </Typography>
        </Box>
      </Button>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
        PaperProps={{
          sx: {
            width: 320,
            maxHeight: 500,
            bgcolor: '#1e293b',
            border: '1px solid',
            borderColor: 'rgba(255,255,255,0.1)',
            mt: 1
          }
        }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'rgba(255,255,255,0.1)' }}>
          <Typography variant="subtitle2" color="text.secondary">
            Your Organizations
          </Typography>
        </Box>
        <List sx={{ maxHeight: 300, overflow: 'auto' }}>
          {organizations.map((org) => (
            <React.Fragment key={org.org_id}>
              <ListItemButton
                selected={organization?.org_id === org.org_id}
                onClick={() => handleOrgSwitch(org)}
                sx={{
                  borderRadius: 1,
                  mx: 1,
                  my: 0.5,
                  '&.Mui-selected': {
                    bgcolor: 'rgba(59, 130, 246, 0.15)',
                    border: '1px solid rgba(59, 130, 246, 0.3)'
                  }
                }}
              >
                <ListItemIcon>
                  <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: '0.8rem' }}>
                    {org.name[0].toUpperCase()}
                  </Avatar>
                </ListItemIcon>
                <ListItemText
                  primary={org.name}
                  secondary={org.billing_email}
                  primaryTypographyProps={{ fontSize: '0.9rem' }}
                  secondaryTypographyProps={{ fontSize: '0.75rem' }}
                />
                {organization?.org_id === org.org_id && (
                  <CheckCircle sx={{ color: 'success.main', fontSize: 16 }} />
                )}
              </ListItemButton>
              {organization?.org_id === org.org_id && (
                <Box sx={{ px: 2, pb: 2 }}>
                  <Paper sx={{ p: 1.5, bgcolor: 'action.hover', borderRadius: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      Current Plan:{' '}
                      <Chip
                        label={org.subscription_tier}
                        size="small"
                        sx={{
                          ml: 0.5,
                          bgcolor: `${getTierColor(org.subscription_tier)}20`,
                          color: getTierColor(org.subscription_tier),
                          border: `1px solid ${getTierColor(org.subscription_tier)}`
                        }}
                      />
                    </Typography>
                  </Paper>
                </Box>
              )}
            </React.Fragment>
          ))}
        </List>
        <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)' }} />
        <Box sx={{ p: 1 }}>
          <Button
            fullWidth
            variant="outlined"
            startIcon={<Add />}
            onClick={() => {
              setAnchorEl(null);
              setCreateOrgOpen(true);
            }}
            sx={{
              borderColor: 'rgba(255,255,255,0.2)',
              color: '#e2e8f0',
              '&:hover': {
                borderColor: 'rgba(59, 130, 246, 0.5)',
                bgcolor: 'rgba(59, 130, 246, 0.1)'
              }
            }}
          >
            Create New Organization
          </Button>
        </Box>
      </Menu>

      {/* Create Organization Dialog */}
      <Dialog open={createOrgOpen} onClose={() => setCreateOrgOpen(false)}>
        <DialogTitle>Create New Organization</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              autoFocus
              label="Organization Name"
              fullWidth
              value={newOrgName}
              onChange={(e) => setNewOrgName(e.target.value)}
            />
            <TextField
              label="Billing Email"
              type="email"
              fullWidth
              value={newOrgEmail}
              onChange={(e) => setNewOrgEmail(e.target.value)}
            />
            <Paper sx={{ p: 2, bgcolor: 'action.hover' }}>
              <Typography variant="subtitle2" gutterBottom>Starting Plan: Free</Typography>
              <Typography variant="body2" color="text.secondary">
                • Up to 5 users<br/>
                • 10,000 recognitions/month<br/>
                • Basic support
              </Typography>
            </Paper>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOrgOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateOrg} variant="contained" disabled={!newOrgName || !newOrgEmail}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export const BillingWidget = ({ orgId }: { orgId: string }) => {
  const [billingInfo, setBillingInfo] = useState<Subscription | null>(null);
  const [billingDialogOpen, setBillingDialogOpen] = useState<boolean>(false);

  useEffect(() => {
    if (orgId) {
      fetchBillingInfo();
    }
  }, [orgId]);

  const fetchBillingInfo = async () => {
    try {
      const res = await API.get(`/api/subscriptions/org/${orgId}`).catch(() => null);
      if (res?.data) {
        // Ensure the data has default values for optional properties
        const data: Subscription = {
          plan_name: res.data.plan_name || 'Free',
          monthly_price: res.data.monthly_price || 0,
          current_period_start: res.data.current_period_start || null,
          next_invoice_date: res.data.next_invoice_date || null,
          status: res.data.status || 'active',
          recognitions_used: res.data.recognitions_used || 0,
          recognitions_limit: res.data.recognitions_limit || 0
        };
        setBillingInfo(data);
      }
    } catch (err: any) {
      console.warn('Failed to fetch billing info');
    }
  };

  const getUsageColor = (percentage: number) => {
    if (percentage > 90) return '#ef4444';
    if (percentage > 70) return '#f59e0b';
    return '#10b981';
  };

  if (!billingInfo) {
    return (
      <Card sx={{ p: 2 }}>
        <Typography variant="subtitle2" color="text.secondary">
          Loading billing info...
        </Typography>
      </Card>
    );
  }

  const recUsagePercent = billingInfo.recognitions_limit > 0
    ? Math.round((billingInfo.recognitions_used / billingInfo.recognitions_limit) * 100)
    : 0;

  return (
    <>
      <Card sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle2">Usage</Typography>
          <IconButton size="small" onClick={() => setBillingDialogOpen(true)}>
            <Settings fontSize="small" />
          </IconButton>
        </Box>
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary">Recognitions</Typography>
          <LinearProgress
            variant="determinate"
            value={recUsagePercent}
            sx={{
              height: 6,
              borderRadius: 3,
              bgcolor: 'rgba(255,255,255,0.1)',
              '& .MuiLinearProgress-bar': {
                bgcolor: getUsageColor(recUsagePercent)
              }
            }}
          />
          <Typography variant="caption" color="text.secondary">
            {billingInfo.recognitions_used?.toLocaleString() || 0} / {billingInfo.recognitions_limit?.toLocaleString() || 0}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">
            Plan: {billingInfo.plan_name || 'Free'}
          </Typography>
          <Chip label="Active" size="small" sx={{ ml: 1, bgcolor: 'success.dark' }} />
        </Box>
      </Card>

      <Dialog open={billingDialogOpen} onClose={() => setBillingDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Billing & Subscription</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid size={{ xs: 12 }} >
              <Card sx={{ p: 2, bgcolor: 'action.hover' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="h6">{billingInfo.plan_name || 'Free'}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      ${billingInfo.monthly_price || 0}/month
                    </Typography>
                  </Box>
                  <Chip label="Current" color="primary" />
                </Box>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }} >
              <Card sx={{ p: 2 }}>
                <Typography variant="subtitle2" gutterBottom>Recognitions</Typography>
                <Typography variant="h5">{billingInfo.recognitions_used?.toLocaleString() || 0}</Typography>
                <Typography variant="caption" color="text.secondary">
                  of {billingInfo.recognitions_limit?.toLocaleString() || 0} monthly
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={recUsagePercent}
                  sx={{
                    mt: 1,
                    height: 6,
                    borderRadius: 3,
                    bgcolor: 'rgba(255,255,255,0.1)',
                    '& .MuiLinearProgress-bar': {
                      bgcolor: getUsageColor(recUsagePercent)
                    }
                  }}
                />
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }} >
              <Card sx={{ p: 2 }}>
                <Typography variant="subtitle2" gutterBottom>Billing Cycle</Typography>
                <Typography variant="body2">
                  Current period: {billingInfo.current_period_start ? new Date(billingInfo.current_period_start).toLocaleDateString() : 'N/A'}
                </Typography>
                <Typography variant="body2">
                  Next invoice: {billingInfo.next_invoice_date ? new Date(billingInfo.next_invoice_date).toLocaleDateString() : 'N/A'}
                </Typography>
              </Card>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBillingDialogOpen(false)}>Close</Button>
          <Button variant="contained" color="primary">Upgrade Plan</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default OrgSwitcher;

