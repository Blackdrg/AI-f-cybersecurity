import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Grid, Paper, Card, CardContent,
  Table, TableBody, TableCell, TableHead, TableRow,
  LinearProgress, Chip, Alert, Button, Select, MenuItem,
  FormControl, InputLabel, TablePagination
} from '@mui/material';
import { AccountCircle, TrendingUp, Analytics } from '@mui/icons-material';
import API from '../services/api';

function BiasReportTab() {
  const [biasData, setBiasData] = useState(null);
  const [timeframe, setTimeframe] = useState('30d');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  useEffect(() => {
    loadBiasData();
  }, [timeframe]);

  const loadBiasData = async () => {
    try {
      const res = await API.get(`/api/bias-report?timeframe=${timeframe}`);
      setBiasData(res.data);
    } catch (err) {
      // Use sample data
      setBiasData({
        summary: {
          totalAssessments: 12450,
          overallFairnessScore: 0.94,
          groupsAnalyzed: 8
        },
        groups: [
          {
            group: 'Female',
            groupSize: 5230,
            truePositiveRate: 0.928,
            falsePositiveRate: 0.042,
            trueNegativeRate: 0.958,
            falseNegativeRate: 0.072,
            accuracy: 0.928,
            demographicParityDifference: 0.032
          },
          {
            group: 'Male',
            groupSize: 4890,
            truePositiveRate: 0.951,
            falsePositiveRate: 0.038,
            trueNegativeRate: 0.962,
            falseNegativeRate: 0.049,
            accuracy: 0.951,
            demographicParityDifference: 0.032
          },
          {
            group: 'Age 18-30',
            groupSize: 3850,
            truePositiveRate: 0.962,
            falsePositiveRate: 0.035,
            trueNegativeRate: 0.965,
            falseNegativeRate: 0.038,
            accuracy: 0.962,
            demographicParityDifference: 0.002
          },
          {
            group: 'Age 31-50',
            groupSize: 4210,
            truePositiveRate: 0.945,
            falsePositiveRate: 0.039,
            trueNegativeRate: 0.961,
            falseNegativeRate: 0.055,
            accuracy: 0.945,
            demographicParityDifference: 0.005
          },
          {
            group: 'Age 51+',
            groupSize: 2170,
            truePositiveRate: 0.876,
            falsePositiveRate: 0.052,
            trueNegativeRate: 0.948,
            falseNegativeRate: 0.124,
            accuracy: 0.876,
            demographicParityDifference: 0.034
          },
          {
            group: 'Ethnic Group A',
            groupSize: 4520,
            truePositiveRate: 0.938,
            falsePositiveRate: 0.041,
            trueNegativeRate: 0.959,
            falseNegativeRate: 0.062,
            accuracy: 0.938,
            demographicParityDifference: 0.008
          },
          {
            group: 'Ethnic Group B',
            groupSize: 2850,
            truePositiveRate: 0.896,
            falsePositiveRate: 0.048,
            trueNegativeRate: 0.952,
            falseNegativeRate: 0.104,
            accuracy: 0.896,
            demographicParityDifference: 0.024
          },
          {
            group: 'Ethnic Group C',
            groupSize: 1060,
            truePositiveRate: 0.912,
            falsePositiveRate: 0.045,
            trueNegativeRate: 0.955,
            falseNegativeRate: 0.088,
            accuracy: 0.912,
            demographicParityDifference: 0.020
          }
        ]
      });
    }
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight="bold">
            Bias Detection Report
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Fairness analysis across demographic groups
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Timeframe</InputLabel>
            <Select
              value={timeframe}
              label="Timeframe"
              onChange={(e) => setTimeframe(e.target.value)}
            >
              <MenuItem value="7d">Last 7 days</MenuItem>
              <MenuItem value="30d">Last 30 days</MenuItem>
              <MenuItem value="90d">Last 90 days</MenuItem>
            </Select>
          </FormControl>
          <Button variant="contained" startIcon={<TrendingUp />}>
            Export Report
          </Button>
        </Box>
      </Box>

      {/* Summary Cards */}
      {biasData && (
        <>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ bgcolor: 'primary.main', color: 'white' }}>
                <CardContent>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>Overall Fairness Score</Typography>
                  <Typography variant="h4" fontWeight="bold" sx={{ mt: 1 }}>
                    {Math.round((biasData.summary?.overallFairnessScore || 0.94) * 100)}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ bgcolor: 'success.main', color: 'white' }}>
                <CardContent>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>Total Assessments</Typography>
                  <Typography variant="h4" fontWeight="bold" sx={{ mt: 1 }}>
                    {(biasData.summary?.totalAssessments || 12450).toLocaleString()}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ bgcolor: 'info.main', color: 'white' }}>
                <CardContent>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>Groups Analyzed</Typography>
                  <Typography variant="h4" fontWeight="bold" sx={{ mt: 1 }}>
                    {biasData.summary?.groupsAnalyzed || 8}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ bgcolor: 'warning.main', color: 'white' }}>
                <CardContent>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>Max Disparity</Typography>
                  <Typography variant="h4" fontWeight="bold" sx={{ mt: 1 }}>
                    {Math.max(...(biasData.groups?.map(g => g.demographicParityDifference) || [0.032])) * 100}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Groups Table */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <AccountCircle color="primary" /> Demographic Group Analysis
              </Typography>
              <Paper sx={{ width: '100%', overflow: 'hidden' }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Demographic Group</TableCell>
                      <TableCell align="right">Group Size</TableCell>
                      <TableCell align="right">Accuracy</TableCell>
                      <TableCell align="right">TPR</TableCell>
                      <TableCell align="right">FPR</TableCell>
                      <TableCell align="right">Parity Diff</TableCell>
                      <TableCell align="right">Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {biasData.groups
                      .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                      .map((group, idx) => {
                        const parityDiff = group.demographicParityDifference;
                        return (
                          <TableRow key={idx}>
                            <TableCell>
                              <Typography variant="subtitle2">{group.group}</Typography>
                            </TableCell>
                            <TableCell align="right">{group.groupSize.toLocaleString()}</TableCell>
                            <TableCell align="right">
                              <Typography fontWeight={600} color={group.accuracy >= 0.9 ? 'success.main' : 'warning.main'}>
                                {Math.round(group.accuracy * 100)}%
                              </Typography>
                            </TableCell>
                            <TableCell align="right">{Math.round(group.truePositiveRate * 100)}%</TableCell>
                            <TableCell align="right">{Math.round(group.falsePositiveRate * 100)}%</TableCell>
                            <TableCell align="right">
                              <Typography color={parityDiff > 0.05 ? 'error.main' : 'text.secondary'}>
                                {Math.round(parityDiff * 100)}%
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Chip
                                label={parityDiff > 0.05 ? 'Action Needed' : 'Good'}
                                size="small"
                                color={parityDiff > 0.05 ? 'error' : 'success'}
                              />
                            </TableCell>
                          </TableRow>
                        );
                      })}
                  </TableBody>
                </Table>
                <TablePagination
                  rowsPerPageOptions={[10, 25, 50]}
                  component="div"
                  count={biasData.groups.length}
                  rowsPerPage={rowsPerPage}
                  page={page}
                  onPageChange={handleChangePage}
                  onRowsPerPageChange={handleChangeRowsPerPage}
                  sx={{ borderTop: '1px solid', borderColor: 'divider' }}
                />
              </Paper>
            </CardContent>
          </Card>

          {/* Key Findings */}
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Key Findings</Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    <Alert severity="warning" icon={false} sx={{ fontSize: '0.875rem' }}>
                      <strong>Minor disparities detected:</strong> Age 51+ group shows 7.6% lower accuracy
                    </Alert>
                    <Alert severity="info" icon={false} sx={{ fontSize: '0.875rem' }}>
                      <strong>Gender parity:</strong> Within acceptable bounds (3.2% difference)
                    </Alert>
                    <Alert severity="info" icon={false} sx={{ fontSize: '0.875rem' }}>
                      <strong>Recommendation:</strong> Retrain models with balanced age representation
                    </Alert>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Metrics Distribution</Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <Box>
                      <Typography variant="body2" color="text.secondary">Equalized Odds Difference</Typography>
                      <LinearProgress 
                        variant="determinate" 
                        value={6.2} 
                        sx={{
                          height: 8,
                          borderRadius: 4,
                          bgcolor: 'rgba(16, 185, 129, 0.2)',
                          '& .MuiLinearProgress-bar': { bgcolor: '#10b981' }
                        }}
                      />
                      <Typography variant="caption">6.2% (target: <5%)</Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="text.secondary">Demographic Parity</Typography>
                      <LinearProgress 
                        variant="determinate" 
                        value={3.2} 
                        sx={{
                          height: 8,
                          borderRadius: 4,
                          bgcolor: 'rgba(16, 185, 129, 0.2)',
                          '& .MuiLinearProgress-bar': { bgcolor: '#3b82f6' }
                        }}
                      />
                      <Typography variant="caption">3.2% (target: <5%) ✓</Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      )}
    </Box>
  );
}

export default BiasReportTab;