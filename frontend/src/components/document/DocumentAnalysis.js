import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { 
  Container, Row, Col, Card, Button, Alert, 
  Tab, Tabs, Badge, Spinner, Form, InputGroup 
} from 'react-bootstrap';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { 
  getDocumentAnalysis,
  queryDocument,
  downloadDocument,
  downloadAnalysisReport,
  saveAnalysisToLocal
} from '../../services/documentService';

const DocumentAnalysis = () => {
  const { documentId } = useParams();
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [queryResult, setQueryResult] = useState(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [downloadingFile, setDownloadingFile] = useState(false);
  const [downloadingReport, setDownloadingReport] = useState(false);
  const [savingLocal, setSavingLocal] = useState(false);
  
  // Colors for risk levels
  const RISK_COLORS = {
    high: '#d9534f',
    medium: '#f0ad4e',
    low: '#5bc0de',
    negligible: '#5cb85c'
  };
  
  // COLORS for PieChart
  const COLORS = ['#d9534f', '#f0ad4e', '#5bc0de', '#5cb85c'];

  // Load document analysis on component mount
  useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        setLoading(true);
        const data = await getDocumentAnalysis(documentId);
        setAnalysis(data);
      } catch (err) {
        setError('Failed to load document analysis. Please try again later.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalysis();
  }, [documentId]);

  // Handle document query
  const handleQuery = async (e) => {
    e.preventDefault();
    
    if (!query.trim()) return;
    
    try {
      setQueryLoading(true);
      setQueryResult(null);
      
      const result = await queryDocument(documentId, query);
      setQueryResult(result);
    } catch (err) {
      console.error(err);
      setQueryResult({ error: 'Failed to process query. Please try again.' });
    } finally {
      setQueryLoading(false);
    }
  };

  // Handle document download
  const handleDownloadDocument = async () => {
    if (!analysis) return;
    
    try {
      setDownloadingFile(true);
      await downloadDocument(documentId, analysis.filename);
    } catch (err) {
      console.error(err);
      setError('Failed to download document. Please try again later.');
    } finally {
      setDownloadingFile(false);
    }
  };

  // Handle report download
  const handleDownloadReport = async () => {
    if (!analysis) return;
    
    try {
      setDownloadingReport(true);
      await downloadAnalysisReport(documentId, analysis.filename);
    } catch (err) {
      console.error(err);
      setError('Failed to download analysis report. Please try again later.');
    } finally {
      setDownloadingReport(false);
    }
  };

  // Handle saving analysis to local folder
  const handleSaveLocal = async () => {
    if (!analysis) return;
    
    try {
      setSavingLocal(true);
      await saveAnalysisToLocal(analysis);
    } catch (err) {
      console.error(err);
      setError('Failed to save analysis to local folder. Please try again later.');
    } finally {
      setSavingLocal(false);
    }
  };

  // Group clauses by risk level for the risk distribution chart
  const getRiskDistribution = () => {
    if (!analysis || !analysis.important_clauses) return [];
    
    const counts = {
      high: 0,
      medium: 0,
      low: 0,
      negligible: 0
    };
    
    analysis.important_clauses.forEach(clause => {
      counts[clause.risk_level] = (counts[clause.risk_level] || 0) + 1;
    });
    
    return [
      { name: 'High Risk', value: counts.high },
      { name: 'Medium Risk', value: counts.medium },
      { name: 'Low Risk', value: counts.low },
      { name: 'Negligible', value: counts.negligible },
    ].filter(item => item.value > 0);
  };

  // Get clause type distribution for chart
  const getClauseDistribution = () => {
    if (!analysis || !analysis.important_clauses) return [];
    
    const counts = {};
    
    analysis.important_clauses.forEach(clause => {
      const type = clause.type.replace('_', ' ');
      counts[type] = (counts[type] || 0) + 1;
    });
    
    return Object.keys(counts).map(type => ({
      name: type.charAt(0).toUpperCase() + type.slice(1),
      count: counts[type]
    }));
  };

  // Display loading spinner
  if (loading) {
    return (
      <Container className="d-flex justify-content-center align-items-center" style={{ minHeight: '60vh' }}>
        <div className="text-center">
          <Spinner animation="border" />
          <div className="mt-3">Loading document analysis...</div>
        </div>
      </Container>
    );
  }

  // Display error message
  if (error) {
    return (
      <Container className="mt-4">
        <Alert variant="danger">{error}</Alert>
        <Button variant="primary" onClick={() => window.history.back()}>
          Go Back
        </Button>
      </Container>
    );
  }

  // Display if no analysis found
  if (!analysis) {
    return (
      <Container className="mt-4">
        <Alert variant="warning">No analysis found for this document.</Alert>
        <Button variant="primary" onClick={() => window.history.back()}>
          Go Back
        </Button>
      </Container>
    );
  }

  return (
    <Container fluid className="mt-4">
      <Row>
        <Col md={12} lg={12}>
          <Card className="mb-4">
            <Card.Header className="d-flex justify-content-between align-items-center">
              <h4>{analysis.filename}</h4>
              <div>
                <Button 
                  variant="primary" 
                  className="me-2" 
                  onClick={handleDownloadDocument}
                  disabled={downloadingFile}
                >
                  {downloadingFile ? 'Downloading...' : 'Download Document'}
                </Button>
                <Button 
                  variant="success" 
                  className="me-2" 
                  onClick={handleDownloadReport}
                  disabled={downloadingReport}
                >
                  {downloadingReport ? 'Generating Report...' : 'Download Report'}
                </Button>
                <Button 
                  variant="secondary" 
                  onClick={handleSaveLocal}
                  disabled={savingLocal}
                >
                  {savingLocal ? 'Saving...' : 'Save Analysis Locally'}
                </Button>
              </div>
            </Card.Header>
            <Card.Body>
              <div className="mb-4">
                <h5>Document Summary</h5>
                <div className="d-flex mb-3">
                  <div className="me-4">
                    <strong>Document Type:</strong> {analysis.document_type}
                  </div>
                  <div className="me-4">
                    <strong>Analysis Date:</strong> {analysis.analysis_date}
                  </div>
                  <div>
                    <strong>Overall Risk Score:</strong>{' '}
                    <Badge 
                      bg={
                        analysis.overall_risk_score >= 0.7 ? 'danger' :
                        analysis.overall_risk_score >= 0.4 ? 'warning' :
                        analysis.overall_risk_score >= 0.1 ? 'info' : 'success'
                      }
                    >
                      {analysis.overall_risk_score.toFixed(2)}
                    </Badge>
                  </div>
                </div>
                <Card>
                  <Card.Body>
                    <p>{analysis.summary}</p>
                  </Card.Body>
                </Card>
              </div>

              <Tabs defaultActiveKey="visualizations" className="mb-3">
                <Tab eventKey="visualizations" title="Visualizations">
                  <Row>
                    <Col md={6}>
                      <Card className="mb-4">
                        <Card.Header>Risk Distribution</Card.Header>
                        <Card.Body>
                          <ResponsiveContainer width="100%" height={300}>
                            <PieChart>
                              <Pie
                                data={getRiskDistribution()}
                                cx="50%"
                                cy="50%"
                                labelLine={true}
                                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                                outerRadius={80}
                                fill="#8884d8"
                                dataKey="value"
                              >
                                {getRiskDistribution().map((entry, index) => (
                                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                              </Pie>
                              <Tooltip formatter={(value) => [`${value} clauses`, 'Count']} />
                              <Legend />
                            </PieChart>
                          </ResponsiveContainer>
                        </Card.Body>
                      </Card>
                    </Col>
                    <Col md={6}>
                      <Card className="mb-4">
                        <Card.Header>Clause Types</Card.Header>
                        <Card.Body>
                          <ResponsiveContainer width="100%" height={300}>
                            <BarChart
                              data={getClauseDistribution()}
                              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                            >
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis dataKey="name" />
                              <YAxis />
                              <Tooltip />
                              <Legend />
                              <Bar dataKey="count" name="Number of Clauses" fill="#8884d8" />
                            </BarChart>
                          </ResponsiveContainer>
                        </Card.Body>
                      </Card>
                    </Col>
                  </Row>
                </Tab>

                <Tab eventKey="clauses" title="Clauses Analysis">
                  <div className="mb-4">
                    <h5>Important Clauses</h5>
                    
                    {/* Filter buttons for risk levels */}
                    <div className="mb-3">
                      <Button variant="outline-danger" className="me-2 mb-2">High Risk</Button>
                      <Button variant="outline-warning" className="me-2 mb-2">Medium Risk</Button>
                      <Button variant="outline-info" className="me-2 mb-2">Low Risk</Button>
                      <Button variant="outline-success" className="me-2 mb-2">Negligible Risk</Button>
                      <Button variant="outline-secondary" className="mb-2">All</Button>
                    </div>
                    
                    {/* Clauses */}
                    {analysis.important_clauses.map((clause, index) => (
                      <Card 
                        key={index} 
                        className="mb-3"
                        style={{ borderLeft: `5px solid ${RISK_COLORS[clause.risk_level]}` }}
                      >
                        <Card.Header className="d-flex justify-content-between align-items-center">
                          <div>
                            <strong>{clause.type.replace('_', ' ').toUpperCase()}</strong>
                            <Badge 
                              bg={
                                clause.risk_level === 'high' ? 'danger' :
                                clause.risk_level === 'medium' ? 'warning' :
                                clause.risk_level === 'low' ? 'info' : 'success'
                              }
                              className="ms-2"
                            >
                              {clause.risk_level} Risk ({clause.risk_score.toFixed(2)})
                            </Badge>
                          </div>
                        </Card.Header>
                        <Card.Body>
                          <p><strong>Explanation:</strong> {clause.explanation}</p>
                          <div className="bg-light p-3 mt-2 rounded">
                            <p className="mb-0">
                              <strong>Clause Text:</strong> {clause.text}
                            </p>
                          </div>
                        </Card.Body>
                      </Card>
                    ))}
                  </div>
                </Tab>

                <Tab eventKey="query" title="Query Document">
                  <Card>
                    <Card.Body>
                      <h5>Ask a Question About This Document</h5>
                      <Form onSubmit={handleQuery}>
                        <InputGroup className="mb-3">
                          <Form.Control
                            placeholder="e.g., What are the payment terms?"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            disabled={queryLoading}
                          />
                          <Button 
                            variant="primary" 
                            type="submit"
                            disabled={queryLoading || !query.trim()}
                          >
                            {queryLoading ? 'Processing...' : 'Ask'}
                          </Button>
                        </InputGroup>
                      </Form>
                      
                      {queryLoading && (
                        <div className="text-center my-4">
                          <Spinner animation="border" />
                          <div>Processing your question...</div>
                        </div>
                      )}
                      
                      {queryResult && !queryResult.error && (
                        <Card>
                          <Card.Header>Answer</Card.Header>
                          <Card.Body>
                            <p>{queryResult.answer}</p>
                            
                            {queryResult.document_info && (
                              <div className="text-muted mt-3">
                                <small>
                                  Source: {queryResult.document_info.filename || 'Document'} 
                                  ({queryResult.document_info.doc_type || 'Unknown type'})
                                </small>
                              </div>
                            )}
                          </Card.Body>
                        </Card>
                      )}
                      
                      {queryResult && queryResult.error && (
                        <Alert variant="danger">{queryResult.error}</Alert>
                      )}
                    </Card.Body>
                  </Card>
                </Tab>
              </Tabs>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default DocumentAnalysis;