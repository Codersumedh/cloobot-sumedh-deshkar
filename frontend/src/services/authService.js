import axios from 'axios';

const API_URL = 'http://localhost:5000/api'; // Adjust to your backend URL

// Register a new user
export const register = async (userData) => {
  try {
    const response = await axios.post(`${API_URL}/auth/register`, userData);
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : new Error('Server error');
  }
};

// Login user
export const login = async (credentials) => {
  try {
    const response = await axios.post(`${API_URL}/auth/login`, credentials);
    
    // Store the token in session storage
    if (response.data.token) {
      sessionStorage.setItem('user_token', response.data.token);
    }
    
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : new Error('Server error');
  }
};

// Logout user
export const logout = () => {
  sessionStorage.removeItem('user_token');
};

// Get current user token
export const getCurrentUserToken = () => {
  return sessionStorage.getItem('user_token');
};

// Check if user is authenticated
export const isAuthenticated = () => {
  const token = getCurrentUserToken();
  return !!token;
};

// Create axios instance with auth header
export const authAxios = axios.create({
  baseURL: API_URL,
});

// Add authentication header to requests
authAxios.interceptors.request.use(
  (config) => {
    const token = getCurrentUserToken();
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);