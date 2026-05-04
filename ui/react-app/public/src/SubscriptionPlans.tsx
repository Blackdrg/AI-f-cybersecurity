import React, { useState, useEffect } from 'react';
import axios from 'axios';
import type { Plan } from '../types';
import { Card, CardContent, Typography, Button, Grid, Chip, Alert, CircularProgress } from '@mui/material';
import { CreditCard, CheckCircle, Star } from '@mui/icons-material';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, useStripe, useElements } from '@stripe/react-stripe-js';

const stripePromise = loadStripe(process.env.REACT_APP_STRIPE_PUBLISHABLE_KEY || 'pk_test_...');

const SubscriptionPlans = () => {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const [processing, setProcessing] = useState(false);
  const [message, setMessage] = useState('');
  const [severity, setSeverity] = useState('success');
  const stripe = useStripe();
  const elements = useElements();

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      const response = await axios.get('/api/plans');
      setPlans(response.data);
    } catch (error) {
      console.error('Failed to fetch plans');
      setMessage('Failed to load subscription plans');
      setSeverity('error');
    }
    setLoading(false);
  };

  const handleSubscribe = async (plan) => {
    setSelectedPlan(plan);
    setProcessing(true);
    try {
      // Create checkout session via backend
      const paymentResponse = await axios.post('/api/payments/create-session', {
        plan_id: plan.plan_id,
        amount: plan.price
      });

      // Redirect to Stripe Checkout
      const result = await stripe.redirectToCheckout({ sessionId: paymentResponse.data.session_id });

      if (result.error) {
        // If redirectToCheckout fails (e.g., due to a network error)
        setMessage(result.error.message);
        setSeverity('error');
      }
    } catch (error) {
      console.error('Payment failed');
      setMessage('Payment failed. Please try again.');
      setSeverity('error');
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return <CircularProgress />;
  }

  return (
    <div style={{ padding: '20px' }}>
      <Typography variant="h4" gutterBottom>
        Subscription Plans
      </Typography>

      <Grid container spacing={3}>
        {plans.map((plan) => (
          <Grid item xs={12} md={4} key={plan.plan_id}>
            <Card elevation={3} style={{ height: '100%', position: 'relative' }}>
              {plan.name === 'Enterprise' && (
                <Chip
                  icon={<Star />}
                  label="FREE for daredevil0101a@gmail.com"
                  color="secondary"
                  style={{ position: 'absolute', top: 10, right: 10 }}
                />
              )}
              {plan.name === 'Pro' && (
                <Chip
                  icon={<Star />}
                  label="Popular"
                  color="primary"
                  style={{ position: 'absolute', top: 10, right: 10 }}
                />
              )}
              <CardContent style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <Typography variant="h5" component="div" gutterBottom>
                  {plan.name}
                </Typography>
                <Typography variant="h4" color="primary" gutterBottom>
                  ${plan.price}/month
                </Typography>

                <div style={{ flexGrow: 1, marginBottom: '20px' }}>
                  {plan.features.map((feature, index) => (
                    <div key={index} style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <CheckCircle color="success" style={{ marginRight: '8px' }} />
                      <Typography variant="body2">{feature}</Typography>
                    </div>
                  ))}
                </div>

                <Button
                  variant="contained"
                  color="primary"
                  fullWidth
                  disabled={processing}
                  onClick={() => handleSubscribe(plan)}
                  startIcon={<CreditCard />}
                >
                  {processing ? 'Processing...' : 'Subscribe'}
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {message && (
        <Alert severity={severity} style={{ marginTop: '20px' }}>
          {message}
        </Alert>
      )}
    </div>
  );
};

export default SubscriptionPlans;