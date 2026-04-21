import React from 'react';
import { Drawer, List, ListItem, ListItemIcon, ListItemText, Toolbar, Divider, Box, Typography } from '@mui/material';
import { 
  Dashboard, PersonAdd, CameraAlt, BarChart, 
  Settings, ExitToApp, AdminPanelSettings, 
  Videocam, Gavel, Code
} from '@mui/icons-material';

const drawerWidth = 240;

const Sidebar = ({ activePage, setActivePage, onLogout, user }) => {
  const menuItems = [
    { id: 'dashboard', text: 'Dashboard', icon: <Dashboard /> },
    { id: 'enroll', text: 'Enroll', icon: <PersonAdd /> },
    { id: 'recognize', text: 'Recognize', icon: <CameraAlt /> },
    { id: 'cameras', text: 'Cameras', icon: <Videocam /> },
    { id: 'analytics', text: 'Analytics', icon: <BarChart /> },
    { id: 'compliance', text: 'Compliance', icon: <Gavel /> },
    { id: 'developer', text: 'Developer', icon: <Code /> },
    { id: 'admin', text: 'Admin Panel', icon: <AdminPanelSettings /> },
  ];

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
