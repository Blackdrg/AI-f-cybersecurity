import React, { useState } from 'react';
import { Box, Paper, TextField, Button, Typography, Container, Avatar, Alert } from '@mui/material';
import { LockOutlined } from '@mui/icons-material';
import { login } from '../services/api';

const LoginPage = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoggingIn(true);
    setError(null);
    try {
      const res = await login(email, password);
      onLogin(res.user);
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleDemoLogin = async () => {
    setIsLoggingIn(true);
    setError(null);
    try {
      const res = await login('demo@example.com', 'password');
      onLogin(res.user);
    } catch (err) {
      setError(err.message || "Demo login failed");
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
          <Button
            fullWidth
            variant="outlined"
            onClick={handleDemoLogin}
            sx={{ mb: 2 }}
            disabled={isLoggingIn}
          >
            Demo Login
          </Button>
        </Box>
      </Box>
    </Container>
  );
};

export default LoginPage;
