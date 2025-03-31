import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Button, Alert, Spinner, Badge } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getUserDocuments } from '../services/documentService';
import { useAuth } from '../context/AuthContext';

const Dashboard = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { currentUser } = useAuth();

  // Load user's documents on component mount
  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        setLoading(true);
        const data = await getUserDocuments();
        setDocuments(data);
      } catch (err) {
        setError('Failed to load dashboard data. Please try again later.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchDocuments();
  }, []);

  // Get risk distribution data for chart
  const getRiskDistributionData = () => {
    // Count documents by document type and risk level
    const distribution = {};
    
    documents.forEach(doc => {
      const riskLevel = getRiskLevel(doc.overall_risk_score);
      if (!distribution[doc.document_type]) {
        distribution[doc.document_type] = { name: doc.document_type };
      }
      distribution[doc.document_type][riskLevel] = (distribution[doc.document_type][riskLevel] || 0) + 1;
    });
    
    return Object.values(distribution);
  };

  // Get risk level from score
  const getRiskLevel = (score) => {
    if (score >= 0.7) return 'High';
    if (score >= 0.4) return 'Medium';
    if (score >= 0.1) return 'Low';
    return 'Negligible';
  };

  // Get badge variant from risk score
  const getRiskBadgeVariant = (score) => {
    if (score >= 0.7) return 'danger';
    if (score >= 0.4) return 'warning';
    if (score >= 0.1) return 'info';
    return 'success';
  };

  // Get recent documents (last 5)
  const getRecentDocuments = () => {
    return [...documents]
      .sort((a, b) => new Date(b.analysis_date) - new Date(a.analysis_date))
      .slice(0, 5);
  };

  // Display loading spinner
  if (loading) {
    return (
      <Container className="d-flex justify-content-center align-items-center" style={{ minHeight: '60vh' }}>
        <div className="text-center">
          <Spinner animation="border" />
          <div className="mt-3">Loading dashboard data...</div>
        </div>
      </Container>
    );
  }

  return (
    <Container className="mt-4">
      {error && <Alert variant="danger">{error}</Alert>}
      
      <Row className="mb-4">
        <Col>
          <Card>
            <Card.Body>
              <h4>Welcome back, {currentUser?.name || 'User'}!</h4>
              <p>
                Use Contract Analyzer to analyze and understand your legal documents.
                Upload a document to get started.
              </p>
              <Link to="/upload">
                <Button variant="primary">Upload New Document</Button>
              </Link>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      
      <Row className="mb-4">
        <Col md={4}>
          <Card className="text-center h-100">
            <Card.Body>
              <h1>{documents.length}</h1>
              <h5>Total Documents</h5>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className="text-center h-100">
            <Card.Body>
              <h1>
                {documents.filter(doc => doc.overall_risk_score >= 0.7).length}
              </h1>
              <h5>High Risk Documents</h5>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className="text-center h-100">
            <Card.Body>
              <h1>
                {documents.filter(doc => doc.overall_risk_score < 0.4).length}
              </h1>
              <h5>Low Risk Documents</h5>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      
      <Row className="mb-4">
        <Col>
          <Card>
            <Card.Header>Document Risk Distribution</Card.Header>
            <Card.Body>
              {documents.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart
                    data={getRiskDistributionData()}
                    margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="High" stackId="a" fill="#d9534f" />
                    <Bar dataKey="Medium" stackId="a" fill="#f0ad4e" />
                    <Bar dataKey="Low" stackId="a" fill="#5bc0de" />
                    <Bar dataKey="Negligible" stackId="a" fill="#5cb85c" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center py-5">
                  <p>No documents to display. Upload a document to see analytics.</p>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
      
      <Row>
        <Col>
          <Card>
            <Card.Header className="d-flex justify-content-between align-items-center">
              <h5 className="mb-0">Recent Documents</h5>
              <Link to="/documents">
                <Button variant="outline-primary" size="sm">View All</Button>
              </Link>
            </Card.Header>
            <Card.Body>
              {getRecentDocuments().length > 0 ? (
                <div className="table-responsive">
                  <table className="table table-hover">
                    <thead>
                      <tr>
                        <th>Document</th>
                        <th>Type</th>
                        <th>Date</th>
                        <th>Risk Score</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {getRecentDocuments().map((doc) => (
                        <tr key={doc.document_id}>
                          <td>{doc.filename}</td>
                          <td>{doc.document_type}</td>
                          <td>{new Date(doc.analysis_date).toLocaleDateString()}</td>
                          <td>
                            <Badge bg={getRiskBadgeVariant(doc.overall_risk_score)}>
                              {doc.overall_risk_score.toFixed(2)}
                            </Badge>
                          </td>
                          <td>
                            <Link to={`/analysis/${doc.document_id}`}>
                              <Button variant="outline-primary" size="sm">View</Button>
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-4">
                  <p>No documents found. Upload your first document to get started.</p>
                  <Link to="/upload">
                    <Button variant="primary">Upload Document</Button>
                  </Link>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default Dashboard;