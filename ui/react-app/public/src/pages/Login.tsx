import React, { useState } from 'react';
import { Box, Paper, TextField, Button, Typography, Container, Avatar, Alert } from '@mui/material';
import { LockOutlined } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { login as apiLogin } from '../services/api';

const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoggingIn(true);
    setError(null);
    try {
      const res = await apiLogin(email, password);
      await login(res.user, res.organizations || []);
      navigate('/dashboard');
    } catch (err: unknown) {
      setError((err as Error).message || "Login failed");
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleDemoLogin = async () => {
    setIsLoggingIn(true);
    setError(null);
    try {
      const demoEmail = process.env.REACT_APP_DEMO_EMAIL;
      const demoPassword = process.env.REACT_APP_DEMO_PASSWORD;
      if (!demoEmail || !demoPassword) {
        throw new Error("Demo credentials not configured");
      }
      const res = await apiLogin(demoEmail, demoPassword);
      await login(res.user, res.organizations || []);
      navigate('/dashboard');
    } catch (err: unknown) {
      setError((err as Error).message || "Demo login failed");
    } finally {
      setIsLoggingIn(false);
    }
  };

  return (
    <Container component="main" maxWidth="xs">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Avatar sx={{ m: 1, bgcolor: 'primary.main' }}>
          <LockOutlined />
        </Avatar>
        <Typography component="h1" variant="h5">
          Sign in
        </Typography>
        <Box component="form" onSubmit={handleSubmit} noValidate sx={{ mt: 1 }}>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <TextField
            margin="normal"
            required
            fullWidth
            id="email"
            label="Email Address"
            name="email"
            autoComplete="email"
            autoFocus
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isLoggingIn}
          />
          <TextField
            margin="normal"
            required
            fullWidth
            name="password"
            label="Password"
            type="password"
            id="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoggingIn}
          />
          <Button
            type="submit"
            fullWidth
            variant="contained"
            sx={{ mt: 3, mb: 2 }}
            disabled={isLoggingIn}
          >
            {isLoggingIn ? 'Signing In...' : 'Sign In'}
          </Button>
          {process.env.REACT_APP_ENABLE_DEMO === 'true' && (
            <Button
              fullWidth
              variant="outlined"
              onClick={handleDemoLogin}
              sx={{ mb: 2 }}
              disabled={isLoggingIn}
            >
              Demo Login
            </Button>
          )}
        </Box>
      </Box>
    </Container>
  );
};

export default LoginPage;
