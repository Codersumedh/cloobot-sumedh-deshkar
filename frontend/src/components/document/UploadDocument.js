import React, { useState } from 'react';
import { Container, Card, Form, Button, Alert, ProgressBar } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { uploadDocument } from '../../services/documentService';

const UploadDocument = () => {
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const navigate = useNavigate();

  // Handle file selection
  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    
    // Validate file type
    const validTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
    if (selectedFile && !validTypes.includes(selectedFile.type)) {
      setError('Please select a PDF or image file (JPG, JPEG, PNG)');
      setFile(null);
      return;
    }
    
    setFile(selectedFile);
    setError('');
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!file) {
      setError('Please select a file to upload');
      return;
    }
    
    try {
      setLoading(true);
      setError('');
      
      // Simulate progress for better UX
      const progressInterval = setInterval(() => {
        setProgress((prevProgress) => {
          const newProgress = prevProgress + 10;
          return newProgress > 90 ? 90 : newProgress;
        });
      }, 500);
      
      // Upload document
      const response = await uploadDocument(file);
      
      clearInterval(progressInterval);
      setProgress(100);
      
      // Redirect to analysis page with the document ID
      navigate(`/analysis/${response.document_id}`);
    } catch (error) {
      setError(error.message || 'Failed to upload document');
      setProgress(0);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container className="mt-4">
      <Card>
        <Card.Header>
          <h4>Upload Document for Analysis</h4>
        </Card.Header>
        <Card.Body>
          {error && <Alert variant="danger">{error}</Alert>}
          
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3">
              <Form.Label>Select Document</Form.Label>
              <Form.Control
                type="file"
                onChange={handleFileChange}
                accept=".pdf,.jpg,.jpeg,.png"
                disabled={loading}
              />
              <Form.Text className="text-muted">
                Supported formats: PDF, JPG, JPEG, PNG
              </Form.Text>
            </Form.Group>
            
            {loading && (
              <div className="mb-3">
                <ProgressBar now={progress} label={`${progress}%`} />
                <div className="text-center mt-2">
                  {progress < 100 ? 'Processing document...' : 'Analysis complete!'}
                </div>
              </div>
            )}
            
            <Button
              variant="primary"
              type="submit"
              disabled={!file || loading}
              className="w-100"
            >
              {loading ? 'Uploading...' : 'Upload and Analyze'}
            </Button>
          </Form>
        </Card.Body>
      </Card>
    </Container>
  );
};

export default UploadDocument;