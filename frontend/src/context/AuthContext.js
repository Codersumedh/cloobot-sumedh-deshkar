import React, { createContext, useState, useEffect, useContext } from 'react';
import { jwtDecode } from 'jwt-decode'; // Fixed import statement
import { getCurrentUserToken, isAuthenticated } from '../services/authService';

// Create the auth context
const AuthContext = createContext();

export const useAuth = () => {
  return useContext(AuthContext);
};

export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  // Initialize the auth state
  useEffect(() => {
    const initializeAuth = () => {
      const authenticated = isAuthenticated();
      setIsLoggedIn(authenticated);

      if (authenticated) {
        const token = getCurrentUserToken();
        try {
          // Decode the token to get user information
          const decoded = jwtDecode(token); // Using named export instead of default
          setCurrentUser({
            id: decoded.userId,
            email: decoded.email,
            name: decoded.name,
          });
        } catch (error) {
          console.error('Failed to decode token:', error);
        }
      }
      setLoading(false);
    };

    initializeAuth();
  }, []);

  // Update auth state when token changes
  const updateAuthState = () => {
    const authenticated = isAuthenticated();
    setIsLoggedIn(authenticated);

    if (authenticated) {
      const token = getCurrentUserToken();
      try {
        const decoded = jwtDecode(token); // Using named export instead of default
        setCurrentUser({
          id: decoded.userId,
          email: decoded.email,
          name: decoded.name,
        });
      } catch (error) {
        console.error('Failed to decode token:', error);
        setCurrentUser(null);
      }
    } else {
      setCurrentUser(null);
    }
  };

  const value = {
    currentUser,
    isLoggedIn,
    updateAuthState,
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};