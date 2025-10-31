import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, Typography, Button, Grid, Chip, Dialog, DialogTitle, DialogContent, DialogActions, TextField, Alert, CircularProgress } from '@mui/material';
import { CreditCard, CheckCircle, Star } from '@mui/icons-material';

const SubscriptionPlans = () => {
    const [plans, setPlans] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedPlan, setSelectedPlan] = useState(null);
    const [paymentDialog, setPaymentDialog] = useState(false);
    const [cardDetails, setCardDetails] = useState({
        number: '',
        expiry: '',
        cvc: '',
        name: ''
    });
    const [processing, setProcessing] = useState(false);
    const [message, setMessage] = useState('');
    const [severity, setSeverity] = useState('success');

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

    const handleSubscribe = (plan) => {
        setSelectedPlan(plan);
        setPaymentDialog(true);
    };

    const handlePayment = async () => {
        setProcessing(true);
        try {
            // Create payment intent
            const paymentResponse = await axios.post('/api/payments', {
                plan_id: selectedPlan.plan_id,
                amount: selectedPlan.price
            });

            // Process payment with Stripe (simplified)
            const result = await axios.post('/api/payments/process', {
                payment_id: paymentResponse.data.payment_id,
                card_details: cardDetails
            });

            setMessage('Subscription activated successfully!');
            setSeverity('success');
            setPaymentDialog(false);
            setCardDetails({ number: '', expiry: '', cvc: '', name: '' });
        } catch (error) {
            console.error('Payment failed');
            setMessage('Payment failed. Please try again.');
            setSeverity('error');
        }
        setProcessing(false);
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
                                    onClick={() => handleSubscribe(plan)}
                                    startIcon={<CreditCard />}
                                >
                                    Subscribe
                                </Button>
                            </CardContent>
                        </Card>
                    </Grid>
                ))}
            </Grid>

            {/* Payment Dialog */}
            <Dialog open={paymentDialog} onClose={() => setPaymentDialog(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Complete Payment</DialogTitle>
                <DialogContent>
                    <Typography variant="h6" gutterBottom>
                        {selectedPlan?.name} Plan - ${selectedPlan?.price}
                    </Typography>

                    <TextField
                        fullWidth
                        label="Card Number"
                        value={cardDetails.number}
                        onChange={(e) => setCardDetails({...cardDetails, number: e.target.value})}
                        margin="normal"
                        placeholder="1234 5678 9012 3456"
                    />
                    <Grid container spacing={2}>
                        <Grid item xs={6}>
                            <TextField
                                fullWidth
                                label="Expiry Date"
                                value={cardDetails.expiry}
                                onChange={(e) => setCardDetails({...cardDetails, expiry: e.target.value})}
                                placeholder="MM/YY"
                            />
                        </Grid>
                        <Grid item xs={6}>
                            <TextField
                                fullWidth
                                label="CVC"
                                value={cardDetails.cvc}
                                onChange={(e) => setCardDetails({...cardDetails, cvc: e.target.value})}
                                placeholder="123"
                            />
                        </Grid>
                    </Grid>
                    <TextField
                        fullWidth
                        label="Cardholder Name"
                        value={cardDetails.name}
                        onChange={(e) => setCardDetails({...cardDetails, name: e.target.value})}
                        margin="normal"
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setPaymentDialog(false)}>Cancel</Button>
                    <Button
                        onClick={handlePayment}
                        variant="contained"
                        disabled={processing}
                        startIcon={processing ? <CircularProgress size={20} /> : <CreditCard />}
                    >
                        {processing ? 'Processing...' : 'Pay Now'}
                    </Button>
                </DialogActions>
            </Dialog>

            {message && (
                <Alert severity={severity} style={{ marginTop: '20px' }}>
                    {message}
                </Alert>
            )}
        </div>
    );
};

export default SubscriptionPlans;
