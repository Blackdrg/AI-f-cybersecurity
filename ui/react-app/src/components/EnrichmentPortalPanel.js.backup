import React, { useState, useEffect, useMemo } from 'react';
import {
  Box, Typography, Paper, Grid, Card, CardContent,
  TextField, Button, Chip, List, ListItem, ListItemText,
  ListItemIcon, Avatar, CircularProgress, Alert, IconButton,
  Tabs, Tab, Divider, Tooltip, Badge, Collapse, CardHeader,
  Table, TableBody, TableCell, TableHead, TableRow, Stack
} from '@mui/material';
import {
  Search, Web, Description, Link as LinkIcon,
  Public, Book, Article, OpenInNew,
  Info, Timeline, AccountTree, NetworkCheck,
  Star, History, Download, Share, Refresh,
  Category, Language, Today, Person
} from '@mui/icons-material';
import API from '../services/api';

const EnrichmentPortalPanel = ({ 
  personId,
  onEnrichmentComplete,
  onAlertAction
}) => {
  const [activeTab, setActiveTab] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [enrichmentResults, setEnrichmentResults] = useState([]);
  const [history, setHistory] = useState([]);
  const [providers, setProviders] = useState([
    { id: 'bing', name: 'Bing Search', active: true, requests: 0, successRate: 0.95, latency: 120 },
    { id: 'wikipedia', name: 'Wikipedia', active: true, requests: 0, successRate: 0.98, latency: 85 },
    { id: 'threatIntel', name: 'Threat Intelligence', active: true, requests: 0, successRate: 0.92, latency: 200 },
    { id: 'darkweb', name: 'Dark Web Monitor', active: false, requests: 0, successRate: 0.0, latency: null }
  ]);
  const [expandStates, setExpandStates] = useState({});
  const [riskScores, setRiskScores] = useState({});
  const [enrichmentSummary, setEnrichmentSummary] = useState(null);
  const [correlationGraph, setCorrelationGraph] = useState(null);

  useEffect(() => {
    fetchEnrichmentHistory();
    const interval = setInterval(fetchEnrichmentHistory, 60000);
    return () => clearInterval(interval);
  }, [personId]);

  const fetchEnrichmentHistory = async () => {
    if (!personId) return;
    try {
      const res = await API.get(`/api/enrichments?person_id=${personId}`);
      setHistory(res.data?.results || []);
    } catch (err) {
      console.warn('No enrichment history available');
    }
  };

  const performSearch = async () => {
    if (!searchQuery.trim() && !personId) return;
    
    setIsSearching(true);
    const searchTerm = searchQuery.trim() || `Person ID: ${personId}`;
    
    try {
      // Simulate Bing provider search
      updateProviderRequests('bing');
      const bingResults = await mockBingSearch(searchTerm);
      
      // Simulate Wikipedia provider search
      updateProviderRequests('wikipedia');
      const wikiResults = await mockWikipediaSearch(searchTerm);
      
      const combined = [...bingResults, ...wikiResults];
      setEnrichmentResults(combined);
      
      // Generate correlation analysis
      const correlation = generateCorrelationAnalysis(combined);
      setCorrelationGraph(correlation);
      
      // Generate enrichment summary
      const summary = generateEnrichmentSummary(combined, personId);
      setEnrichmentSummary(summary);
      
      // Calculate risk scores
      const riskMap = calculateRiskScores(combined);
      setRiskScores(riskMap);
      
      // Log to history
      await logEnrichmentQuery(searchTerm, combined);
      
      onEnrichmentComplete && onEnrichmentComplete(combined);
    } catch (err) {
      console.error('Enrichment search failed:', err);
    } finally {
      setIsSearching(false);
    }
  };

  const updateProviderRequests = (providerId) => {
    setProviders(prev => prev.map(p => 
      p.id === providerId ? { ...p, requests: p.requests + 1 } : p
    ));
  };

  const mockBingSearch = async (query) => {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    const topics = query.toLowerCase().includes('security') || query.toLowerCase().includes('threat') 
      ? ['cybersecurity', 'intelligence', 'monitoring']
      : query.toLowerCase().includes('identity') || query.toLowerCase().includes('person')
      ? ['identity verification', 'biometric systems', 'authentication']
      : ['facial recognition', 'AI systems', 'privacy'];
    
    return [
      {
        id: `bing_${Date.now()}_1`,
        provider: 'bing',
        providerName: 'Bing Search',
        title: `${query} - Comprehensive Intelligence Report`,
        snippet: `Analysis of ${query} in the context of biometric identification systems and security protocols. Recent developments in multi-modal recognition technologies.`,
        url: `https://bing.com/search?q=${encodeURIComponent(query)}`,
        confidence: 0.87,
        type: 'intelligence_report',
        timestamp: new Date().toISOString(),
        relevanceScore: 0.92,
        tags: topics
      },
      {
        id: `bing_${Date.now()}_2`,
        provider: 'bing',
        providerName: 'Bing Search',
        title: `Latest ${query} Updates and Threat Assessments`,
        snippet: `Real-time threat intelligence and security updates. Monitoring systems have detected patterns related to the query with high confidence.`,
        url: `https://bing.com/news/search?q=${encodeURIComponent(query)}`,
        confidence: 0.79,
        type: 'threat_intelligence',
        timestamp: new Date().toISOString(),
        relevanceScore: 0.85,
        tags: ['threat', 'security', 'monitoring']
      },
      {
        id: `bing_${Date.now()}_3`,
        provider: 'bing',
        providerName: 'Bing Search',
        title: `Technical Documentation: ${query}`,
        snippet: `Technical specifications, implementation guides, and best practices for systems related to the query.`,
        url: `https://bing.com/docs/search?q=${encodeURIComponent(query)}`,
        confidence: 0.72,
        type: 'documentation',
        timestamp: new Date().toISOString(),
        relevanceScore: 0.78,
        tags: ['technical', 'documentation', 'guides']
      }
    ];
  };

  const mockWikipediaSearch = async (query) => {
    await new Promise(resolve => setTimeout(resolve, 400));
    
    const subjects = [
      { title: 'Biometric Recognition Systems', category: 'Technology' },
      { title: 'Facial Recognition Technology', category: 'Computer Vision' },
      { title: 'Identity Verification', category: 'Security' },
      { title: 'Machine Learning in Security', category: 'AI/ML' }
    ];
    
    const subject = subjects[Math.floor(Math.random() * subjects.length)];
    
    return [
      {
        id: `wiki_${Date.now()}_1`,
        provider: 'wikipedia',
        providerName: 'Wikipedia',
        title: subject.title,
        snippet: `A comprehensive overview of ${subject.title.toLowerCase()}. Discusses principles, implementation, and ethical considerations in modern systems.`,
        url: `https://en.wikipedia.org/wiki/${subject.title.replace(/\s+/g, '_')}`,
        confidence: 0.95,
        type: 'reference_article',
        timestamp: new Date().toISOString(),
        relevanceScore: 0.88,
        category: subject.category,
        lastUpdated: '2026-03-15'
      },
      {
        id: `wiki_${Date.now()}_2`,
        provider: 'wikipedia',
        providerName: 'Wikipedia',
        title: 'Artificial Intelligence Ethics',
        snippet: `Ethical frameworks and considerations for AI systems, including bias detection, fairness, and explainability in automated decision-making.`,
        url: 'https://en.wikipedia.org/wiki/AI_ethics',
        confidence: 0.89,
        type: 'reference_article',
        timestamp: new Date().toISOString(),
        relevanceScore: 0.82,
        category: 'Ethics',
        lastUpdated: '2026-04-01'
      },
      {
        id: `wiki_${Date.now()}_3`,
        provider: 'wikipedia',
        providerName: 'Wikipedia',
        title: 'Privacy and Data Protection',
        snippet: `Legal frameworks and technical measures for protecting personal data, including GDPR compliance and anonymization techniques.`,
        url: 'https://en.wikipedia.org/wiki/Data_protection',
        confidence: 0.85,
        type: 'reference_article',
        timestamp: new Date().toISOString(),
        relevanceScore: 0.76,
        category: 'Law',
        lastUpdated: '2026-02-28'
      }
    ];
  };

  const logEnrichmentQuery = async (query, results) => {
    try {
      await API.post('/api/enrichments/log', {
        query,
        person_id: personId,
        results: results.map(r => ({
          provider: r.provider,
          title: r.title,
          confidence: r.confidence,
          relevance: r.relevanceScore
        }))
      });
    } catch (err) {
      console.warn('Failed to log enrichment query');
    }
  };

  const handleExpand = (id) => {
    setExpandStates(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const getCategoryColor = (category) => {
    const colors = {
      'Technology': 'primary',
      'Security': 'error',
      'AI/ML': 'info',
      'Ethics': 'warning',
      'Law': 'secondary',
      'Computer Vision': 'success'
    };
    return colors[category] || 'default';
  };

  const getProviderColor = (provider) => ({
    bing: '#0078d4',
    wikipedia: '#6b6b6b'
  }[provider] || '#94a3b8');

  const getConfidenceColor = (score) => {
    if (score >= 0.9) return { color: '#10b981', bg: 'rgba(16, 185, 129, 0.2)' };
    if (score >= 0.8) return { color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.2)' };
    if (score >= 0.7) return { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.2)' };
    return { color: '#ef4444', bg: 'rgba(239, 68, 68, 0.2)' };
  };

  const getRelevanceColor = (score) => {
    if (score >= 0.9) return '#10b981';
    if (score >= 0.8) return '#3b82f6';
    if (score >= 0.7) return '#f59e0b';
    return '#9ca3af';
  };

  const renderProviderStats = () => (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="subtitle2" gutterBottom>
          Active Providers
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          {providers.map(provider => (
            <Chip
              key={provider.id}
              icon={
                <Box sx={{
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  bgcolor: getProviderColor(provider.id)
                }} />
              }
              label={`${provider.name} (${provider.requests})`}
              variant={provider.active ? 'filled' : 'outlined'}
              sx={{
                bgcolor: provider.active ? `${getProviderColor(provider.id)}22` : 'transparent',
                color: provider.active ? getProviderColor(provider.id) : 'text.secondary',
                borderColor: getProviderColor(provider.id)
              }}
            />
          ))}
        </Box>
      </CardContent>
    </Card>
  );

  const renderSearchBar = () => (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="subtitle2" gutterBottom>
          Intelligence Search
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            fullWidth
            size="small"
            placeholder={personId ? `Search for person ${personId}...` : 'Enter search query...'}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && performSearch()}
            InputProps={{
              startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
            }}
          />
          <Button
            variant="contained"
            startIcon={isSearching ? <CircularProgress size={20} /> : <Search />}
            onClick={performSearch}
            disabled={isSearching || (!searchQuery.trim() && !personId)}
            sx={{ minWidth: 120 }}
          >
            {isSearching ? 'Searching' : 'Search'}
          </Button>
        </Box>
      </CardContent>
    </Card>
  );

  const renderResultCard = (result, index) => {
    const confidenceColor = getConfidenceColor(result.confidence);
    const relevanceColor = getRelevanceColor(result.relevanceScore);
    const isExpanded = expandStates[result.id];

    return (
      <Card key={result.id} sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
            <Box sx={{ 
              mt: 0.5,
              width: 8,
              height: 8,
              borderRadius: '50%',
              bgcolor: getProviderColor(result.provider),
              flexShrink: 0
            }} />
            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                  {result.title}
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5 }}>
                  <Chip
                    size="small"
                    label={result.providerName}
                    sx={{
                      bgcolor: `${getProviderColor(result.provider)}22`,
                      color: getProviderColor(result.provider)
                    }}
                  />
                  <Typography variant="caption" sx={{
                    bgcolor: confidenceColor.bg,
                    color: confidenceColor.color,
                    px: 1,
                    py: 0.25,
                    borderRadius: 1,
                    fontSize: '0.75rem'
                  }}>
                    {(result.confidence * 100).toFixed(0)}% confidence
                  </Typography>
                </Box>
              </Box>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                {result.snippet}
              </Typography>

              <Box sx={{ display: 'flex', gap: 0.5, mb: 1, flexWrap: 'wrap' }}>
                {result.tags?.map((tag, i) => (
                  <Chip
                    key={i}
                    label={tag}
                    size="small"
                    variant="outlined"
                    sx={{ fontSize: '0.7rem', height: 20 }}
                  />
                ))}
                {result.category && (
                  <Chip
                    label={result.category}
                    size="small"
                    color={getCategoryColor(result.category)}
                    variant="outlined"
                    sx={{ fontSize: '0.7rem', height: 20 }}
                  />
                )}
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
                <Typography variant="caption" color="text.secondary">
                  Relevance: <Box component="span" sx={{ 
                    color: relevanceColor,
                    fontWeight: 600
                  }}>
                    {(result.relevanceScore * 100).toFixed(0)}%
                  </Box>
                </Typography>
                
                {result.lastUpdated && (
                  <Typography variant="caption" color="text.secondary">
                    Updated: {result.lastUpdated}
                  </Typography>
                )}
              </Box>

              <Collapse in={isExpanded} timeout="auto" sx={{ mt: 2 }}>
                <Box sx={{ 
                  p: 2, 
                  bgcolor: 'background.paper',
                  borderRadius: 1,
                  border: '1px solid rgba(255,255,255,0.1)'
                }}>
                  <Typography variant="body2" color="text.secondary">
                    <strong>Source:</strong> {result.url}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    <strong>Retrieved:</strong> {new Date(result.timestamp).toLocaleString()}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    <strong>Type:</strong> {result.type?.replace(/_/g, ' ')}
                  </Typography>
                  {result.person_name && (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      <strong>Person:</strong> {result.person_name}
                    </Typography>
                  )}
                </Box>
              </Collapse>

              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
                <Button
                  size="small"
                  startIcon={<OpenInNew />}
                  component="a"
                  href={result.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  View Source
                </Button>
                <IconButton
                  size="small"
                  onClick={() => handleExpand(result.id)}
                >
                  <Info color={isExpanded ? "primary" : "action"} />
                  <Typography variant="caption" sx={{ ml: 0.5 }}>
                    {isExpanded ? 'Hide' : 'Details'}
                  </Typography>
                </IconButton>
              </Box>
            </Box>
          </Box>
        </CardContent>
      </Card>
    );
  };

  const renderEnrichmentResults = () => (
    <Card sx={{ mb: 3 }}>
      <CardHeader
        title={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Article color="primary" />
            Enrichment Results
            {enrichmentResults.length > 0 && (
              <Badge badgeContent={enrichmentResults.length} color="primary" />
            )}
          </Box>
        }
      />
      <CardContent>
        {enrichmentResults.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Info sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography color="text.secondary">
              {searchQuery ? 'No results found. Try a different query.' : 'No searches performed yet.'}
            </Typography>
          </Box>
        ) : (
          <Stack spacing={2}>
            {enrichmentResults.map((result) => renderResultCard(result))}
          </Stack>
        )}
      </CardContent>
    </Card>
  );

  const renderEnrichmentHistory = () => (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <History color="primary" />
          Enrichment History
        </Typography>
        
        {history.length === 0 ? (
          <Typography color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
            No enrichment history available
          </Typography>
        ) : (
          <List dense>
            {history.slice(0, 10).map((item, idx) => (
              <React.Fragment key={idx}>
                <ListItem
                  sx={{
                    bgcolor: 'background.paper',
                    borderRadius: 1,
                    mb: 0.5
                  }}
                >
                  <ListItemIcon>
                    <Article sx={{ fontSize: 16, color: 'primary.main' }} />
                  </ListItemIcon>
                  <ListItemText
                    primary={item.query || 'Enrichment Query'}
                    secondary={`${new Date(item.timestamp).toLocaleString()} - ${item.results_count || 0} results`}
                    primaryTypographyProps={{ fontSize: '0.85rem' }}
                    secondaryTypographyProps={{ fontSize: '0.75rem' }}
                  />
                  <Chip
                    label={`${item.results_count || 0}`}
                    size="small"
                    sx={{ bgcolor: 'primary.main', color: 'white' }}
                  />
                </ListItem>
                <Divider />
              </React.Fragment>
            ))}
          </List>
        )}
      </CardContent>
    </Card>
  );

  // --- Dynamic Analysis Functions ---
  
  const generateCorrelationAnalysis = (results) => {
    const entityMap = new Map();
    
    results.forEach(result => {
      if (result.entities) {
        result.entities.forEach(entity => {
          if (!entityMap.has(entity)) {
            entityMap.set(entity, { occurrences: 0, sources: [], riskScore: 0 });
          }
          const entry = entityMap.get(entity);
          entry.occurrences++;
          entry.sources.push(result.provider);
          entry.riskScore = Math.max(entry.riskScore, result.riskScore || 0);
        });
      }
    });
    
    const correlatedEntities = [];
    const entityArray = Array.from(entityMap.entries());
    for (let i = 0; i < entityArray.length; i++) {
      for (let j = i + 1; j < entityArray.length; j++) {
        const [entity1, data1] = entityArray[i];
        const [entity2, data2] = entityArray[j];
        const sharedSources = data1.sources.filter(s => data2.sources.includes(s));
        if (sharedSources.length > 0) {
          correlatedEntities.push({
            entity1,
            entity2,
            sharedSources,
            combinedRisk: Math.max(data1.riskScore, data2.riskScore),
            connectionStrength: sharedSources.length
          });
        }
      }
    }
    
    return {
      entities: Array.from(entityMap.entries()).map(([entity, data]) => ({
        entity,
        occurrences: data.occurrences,
        sources: [...new Set(data.sources)],
        riskScore: data.riskScore
      })).sort((a, b) => b.riskScore - a.riskScore),
      correlations: correlatedEntities.sort((a, b) => b.combinedRisk - a.combinedRisk)
    };
  };
  
  const generateEnrichmentSummary = (results, personId) => {
    const totalResults = results.length;
    const avgConfidence = results.reduce((sum, r) => sum + (r.confidence || 0), 0) / totalResults || 0;
    const avgRelevance = results.reduce((sum, r) => sum + (r.relevanceScore || 0), 0) / totalResults || 0;
    const maxRiskScore = Math.max(...results.map(r => r.riskScore || 0));
    
    const riskDistribution = {
      critical: results.filter(r => (r.riskScore || 0) >= 0.8).length,
      high: results.filter(r => (r.riskScore || 0) >= 0.6 && (r.riskScore || 0) < 0.8).length,
      medium: results.filter(r => (r.riskScore || 0) >= 0.3 && (r.riskScore || 0) < 0.6).length,
      low: results.filter(r => (r.riskScore || 0) < 0.3).length
    };
    
    const commonTags = {};
    results.forEach(r => {
      (r.tags || []).forEach(tag => {
        commonTags[tag] = (commonTags[tag] || 0) + 1;
      });
    });
    
    return {
      totalResults,
      avgConfidence,
      avgRelevance,
      maxRiskScore,
      riskDistribution,
      topTags: Object.entries(commonTags).sort((a, b) => b[1] - a[1]).slice(0, 5),
      personId,
      timestamp: new Date().toISOString()
    };
  };
  
  const calculateRiskScores = (results) => {
    const riskMap = {
      overall: 0,
      byProvider: {},
      byType: {},
      highRiskItems: []
    };
    
    results.forEach(r => {
      const risk = r.riskScore || 0;
      riskMap.overall = Math.max(riskMap.overall, risk);
      
      if (!riskMap.byProvider[r.provider]) {
        riskMap.byProvider[r.provider] = { maxRisk: 0, count: 0 };
      }
      riskMap.byProvider[r.provider].maxRisk = Math.max(riskMap.byProvider[r.provider].maxRisk, risk);
      riskMap.byProvider[r.provider].count++;
      
      if (!riskMap.byType[r.type]) {
        riskMap.byType[r.type] = { maxRisk: 0, count: 0 };
      }
      riskMap.byType[r.type].maxRisk = Math.max(riskMap.byType[r.type].maxRisk, risk);
      riskMap.byType[r.type].count++;
      
      if (risk >= 0.7) {
        riskMap.highRiskItems.push({
          id: r.id,
          title: r.title,
          riskScore: risk,
          riskLevel: r.riskLevel || 'high'
        });
      }
    });
    
    riskMap.highRiskItems.sort((a, b) => b.riskScore - a.riskScore);
    return riskMap;
  };  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h5" gutterBottom sx={{ fontWeight: 700 }}>
        Enrichment Portal
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Cross-reference identities with external intelligence sources (Bing, Wikipedia)
      </Typography>

      <Box sx={{ flexGrow: 1, overflow: 'auto', pr: 2 }}>
        <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)} sx={{ mb: 2 }}>
          <Tab label="Search" />
          <Tab label="History" />
        </Tabs>

        {activeTab === 0 && (
          <Box>
            {renderProviderStats()}
            {renderSearchBar()}
            {renderEnrichmentResults()}
          </Box>
        )}

        {activeTab === 1 && (
          <Box>
            {renderEnrichmentHistory()}
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default EnrichmentPortalPanel;