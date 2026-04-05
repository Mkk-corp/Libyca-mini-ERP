import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// Listen for forced logout (token refresh failure)
window.addEventListener('libyca:logout', () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  window.location.href = '/login';
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
