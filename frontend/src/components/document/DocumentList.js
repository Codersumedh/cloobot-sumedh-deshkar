import React, { useState, useEffect } from 'react';
import { Container, Card, Table, Button, Alert, Badge, Spinner } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { getUserDocuments } from '../../services/documentService';

const DocumentList = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Load user's documents on component mount
  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        setLoading(true);
        const data = await getUserDocuments();
        setDocuments(data);
      } catch (err) {
        setError('Failed to load documents. Please try again later.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchDocuments();
  }, []);

  // Get badge color based on risk score
  const getRiskBadgeVariant = (riskScore) => {
    if (riskScore >= 0.7) return 'danger';
    if (riskScore >= 0.4) return 'warning';
    if (riskScore >= 0.1) return 'info';
    return 'success';
  };

  // Display loading spinner
  if (loading) {
    return (
      <Container className="d-flex justify-content-center align-items-center" style={{ minHeight: '60vh' }}>
        <div className="text-center">
          <Spinner animation="border" />
          <div className="mt-3">Loading your documents...</div>
        </div>
      </Container>
    );
  }

  return (
    <Container className="mt-4">
      <Card>
        <Card.Header className="d-flex justify-content-between align-items-center">
          <h4>My Documents</h4>
          <Link to="/upload">
            <Button variant="primary">Upload New Document</Button>
          </Link>
        </Card.Header>
        <Card.Body>
          {error && <Alert variant="danger">{error}</Alert>}
          
          {documents.length === 0 ? (
            <div className="text-center py-5">
              <p>You haven't uploaded any documents yet.</p>
              <Link to="/upload">
                <Button variant="primary">Upload Your First Document</Button>
              </Link>
            </div>
          ) : (
            <Table responsive striped hover>
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Document Type</th>
                  <th>Upload Date</th>
                  <th>Risk Score</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
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
                        <Button variant="outline-primary" size="sm">
                          View Analysis
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>
    </Container>
  );
};

export default DocumentList;