import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Container } from 'react-bootstrap';
import { AuthProvider } from './context/AuthContext';

// Layout components
import NavigationBar from './components/layout/Navbar';
import ProtectedRoute from './components/layout/ProtectedRoute';

// Page components
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import Login from './components/auth/Login';
import Signup from './components/auth/Signup';
import UploadDocument from './components/document/UploadDocument';
import DocumentList from './components/document/DocumentList';
import DocumentAnalysis from './components/document/DocumentAnalysis';

// Import Bootstrap CSS
import 'bootstrap/dist/css/bootstrap.min.css';
// Import custom CSS
import './index.css';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="app">
          <NavigationBar />
          <main>
            <Routes>
              {/* Public routes */}
              <Route path="/" element={<Home />} />
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />
              
              {/* Protected routes */}
              <Route 
                path="/dashboard" 
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/upload" 
                element={
                  <ProtectedRoute>
                    <UploadDocument />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/documents" 
                element={
                  <ProtectedRoute>
                    <DocumentList />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/analysis/:documentId" 
                element={
                  <ProtectedRoute>
                    <DocumentAnalysis />
                  </ProtectedRoute>
                } 
              />
              
              {/* Fallback route */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
          <footer className="bg-light text-center py-3 mt-5">
            <Container>
              <p className="mb-0">© {new Date().getFullYear()} Contract Analyzer. All rights reserved.</p>
            </Container>
          </footer>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;