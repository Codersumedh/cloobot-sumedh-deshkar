import React from 'react';
import { Container, Row, Col, Card, Button } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Home = () => {
  const { isLoggedIn } = useAuth();

  return (
    <div>
      {/* Hero Section */}
      <div className="bg-primary text-white py-5">
        <Container>
          <Row className="align-items-center">
            <Col md={6} className="mb-4 mb-md-0">
              <h1>Contract Analyzer</h1>
              <p className="lead">
                Analyze your legal documents with AI-powered risk assessment and clause detection
              </p>
              {isLoggedIn ? (
                <Link to="/dashboard">
                  <Button variant="light" size="lg">Go to Dashboard</Button>
                </Link>
              ) : (
                <div>
                  <Link to="/login">
                    <Button variant="light" size="lg" className="me-3">Login</Button>
                  </Link>
                  <Link to="/signup">
                    <Button variant="outline-light" size="lg">Sign Up</Button>
                  </Link>
                </div>
              )}
            </Col>
            <Col md={6}>
              <img 
                src="/priority.png" 
                alt="Contract Analysis" 
                className="img-fluid rounded shadow-lg"
                onError={(e) => {
                  e.target.onerror = null; 
                  e.target.src = 'https://via.placeholder.com/600x400?text=Contract+Analyzer';
                }}
              />
            </Col>
          </Row>
        </Container>
      </div>

      {/* Features Section */}
      <Container className="py-5">
        <h2 className="text-center mb-5">Key Features</h2>
        <Row>
          <Col md={4} className="mb-4">
            <Card className="h-100 shadow-sm">
              <Card.Body className="d-flex flex-column">
                <div className="text-center mb-3">
                  <i className="bi bi-file-earmark-text" style={{ fontSize: '3rem', color: '#0d6efd' }}></i>
                </div>
                <Card.Title className="text-center">Document Analysis</Card.Title>
                <Card.Text>
                  Extract key clauses and analyze their risk level automatically. Get insights into payment terms, liabilities, warranties, and more.
                </Card.Text>
              </Card.Body>
            </Card>
          </Col>
          <Col md={4} className="mb-4">
            <Card className="h-100 shadow-sm">
              <Card.Body className="d-flex flex-column">
                <div className="text-center mb-3">
                  <i className="bi bi-graph-up" style={{ fontSize: '3rem', color: '#0d6efd' }}></i>
                </div>
                <Card.Title className="text-center">Risk Assessment</Card.Title>
                <Card.Text>
                  Get comprehensive risk scores for each document and clause. Identify potential issues before they become problems.
                </Card.Text>
              </Card.Body>
            </Card>
          </Col>
          <Col md={4} className="mb-4">
            <Card className="h-100 shadow-sm">
              <Card.Body className="d-flex flex-column">
                <div className="text-center mb-3">
                  <i className="bi bi-search" style={{ fontSize: '3rem', color: '#0d6efd' }}></i>
                </div>
                <Card.Title className="text-center">Document Query</Card.Title>
                <Card.Text>
                  Ask questions in natural language about your documents. Get instant answers without having to read the entire text.
                </Card.Text>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </Container>

      {/* How It Works Section */}
      <div className="bg-light py-5">
        <Container>
          <h2 className="text-center mb-5">How It Works</h2>
          <Row>
            <Col md={3} className="text-center mb-4">
              <div className="bg-white rounded-circle shadow d-inline-flex justify-content-center align-items-center mb-3" style={{ width: '80px', height: '80px' }}>
                <h3 className="mb-0">1</h3>
              </div>
              <h5>Upload Document</h5>
              <p>Upload your contract or legal document (PDF, JPG, PNG).</p>
            </Col>
            <Col md={3} className="text-center mb-4">
              <div className="bg-white rounded-circle shadow d-inline-flex justify-content-center align-items-center mb-3" style={{ width: '80px', height: '80px' }}>
                <h3 className="mb-0">2</h3>
              </div>
              <h5>AI Analysis</h5>
              <p>Our AI engine identifies clauses and assesses risks.</p>
            </Col>
            <Col md={3} className="text-center mb-4">
              <div className="bg-white rounded-circle shadow d-inline-flex justify-content-center align-items-center mb-3" style={{ width: '80px', height: '80px' }}>
                <h3 className="mb-0">3</h3>
              </div>
              <h5>Risk Assessment</h5>
              <p>Each clause is ranked by risk level with explanations.</p>
            </Col>
            <Col md={3} className="text-center mb-4">
              <div className="bg-white rounded-circle shadow d-inline-flex justify-content-center align-items-center mb-3" style={{ width: '80px', height: '80px' }}>
                <h3 className="mb-0">4</h3>
              </div>
              <h5>Interactive Results</h5>
              <p>Review analysis, ask questions, and export reports.</p>
            </Col>
          </Row>
          <div className="text-center mt-4">
            {isLoggedIn ? (
              <Link to="/upload">
                <Button variant="primary" size="lg">Upload Document</Button>
              </Link>
            ) : (
              <Link to="/signup">
                <Button variant="primary" size="lg">Get Started</Button>
              </Link>
            )}
          </div>
        </Container>
      </div>

      {/* CTA Section */}
      <Container className="py-5">
        <Card className="bg-primary text-white text-center p-4">
          <Card.Body>
            <h3>Ready to analyze your documents?</h3>
            <p className="lead">
              Start using our document analyzer today and get insights into your contracts and legal documents.
            </p>
            {isLoggedIn ? (
              <Link to="/upload">
                <Button variant="light" size="lg">Upload Document</Button>
              </Link>
            ) : (
              <Link to="/signup">
                <Button variant="light" size="lg">Sign Up Now</Button>
              </Link>
            )}
          </Card.Body>
        </Card>
      </Container>
    </div>
  );
};

export default Home;