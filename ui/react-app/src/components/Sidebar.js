import React from 'react';
import { Drawer, List, ListItem, ListItemIcon, ListItemText, Toolbar, Divider, Box, Typography } from '@mui/material';
import { 
  Dashboard, PersonAdd, CameraAlt, BarChart, 
  Settings, ExitToApp, AdminPanelSettings, 
  Videocam, Gavel, Code
} from '@mui/icons-material';

const drawerWidth = 240;

const Sidebar = ({ activePage, setActivePage, onLogout, user }) => {
  const allItems = [
    { id: 'dashboard', text: 'Dashboard', icon: <Dashboard />, roles: ['admin', 'security', 'hr', 'viewer'] },
    { id: 'enroll', text: 'Enroll', icon: <PersonAdd />, roles: ['admin', 'hr'] },
    { id: 'recognize', text: 'Recognize', icon: <CameraAlt />, roles: ['admin', 'security'] },
    { id: 'cameras', text: 'Cameras', icon: <Videocam />, roles: ['admin', 'security'] },
    { id: 'analytics', text: 'Analytics', icon: <BarChart />, roles: ['admin', 'security', 'hr', 'viewer'] },
    { id: 'compliance', text: 'Compliance', icon: <Gavel />, roles: ['admin'] },
    { id: 'developer', text: 'Developer', icon: <Code />, roles: ['admin'] },
    { id: 'admin', text: 'Admin Panel', icon: <AdminPanelSettings />, roles: ['admin'] },
  ];

  const menuItems = allItems.filter(item => 
    !user.role || item.roles.includes(user.role.toLowerCase())
  );

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
      }}
    >
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          FaceAI Pro
        </Typography>
      </Toolbar>
      <Box sx={{ overflow: 'auto', display: 'flex', flexDirection: 'column', height: '100%' }}>
        <List>
          {menuItems.map((item) => (
            <ListItem 
              button 
              key={item.id} 
              selected={activePage === item.id}
              onClick={() => setActivePage(item.id)}
            >
              <ListItemIcon sx={{ color: activePage === item.id ? 'primary.main' : 'inherit' }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItem>
          ))}
        </List>
        <Divider />
        <List>
          <ListItem button onClick={() => setActivePage('settings')}>
            <ListItemIcon><Settings /></ListItemIcon>
            <ListItemText primary="Settings" />
          </ListItem>
        </List>
        
        <Box sx={{ flexGrow: 1 }} />
        
        <Divider />
        <List>
          {user && (
            <ListItem sx={{ py: 2 }}>
              <ListItemText 
                primary={user.name || user.email} 
                secondary={user.subscription_tier || 'Free'} 
                primaryTypographyProps={{ variant: 'body2', fontWeight: 'bold' }}
                secondaryTypographyProps={{ variant: 'caption' }}
              />
            </ListItem>
          )}
          <ListItem button onClick={onLogout}>
            <ListItemIcon><ExitToApp color="error" /></ListItemIcon>
            <ListItemText primary="Logout" primaryTypographyProps={{ color: 'error' }} />
          </ListItem>
        </List>
      </Box>
    </Drawer>
  );
};

export default Sidebar;
