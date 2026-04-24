import { useState, useEffect } from 'react';
import { ConfigProvider, App as AntApp } from 'antd';
import type { ThemeConfig } from 'antd';
import { ChatWindow } from './components/ChatWindow';
import { AuthPage } from './components/AuthPage';
import { getAuthToken } from './services/api';

const theme: ThemeConfig = {
  token: {
    colorPrimary: '#6366f1',
    colorBgContainer: '#ffffff',
    colorBgElevated: '#ffffff',
    colorBorder: '#e8e8f0',
    colorText: '#1a1a2e',
    colorTextSecondary: '#4a4a6a',
    borderRadius: 10,
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  },
  components: {
    Button: {
      controlHeight: 42,
      paddingContentHorizontal: 24,
    },
    Input: {
      controlHeight: 44,
    },
  },
};

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getAuthToken();
    setIsAuthenticated(!!token);
    setLoading(false);
  }, []);

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setIsAuthenticated(false);
  };

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-secondary)',
      }}>
        <div className="loading-spinner" />
      </div>
    );
  }

  return (
    <ConfigProvider theme={theme}>
      <AntApp>
        {isAuthenticated ? (
          <ChatWindow onLogout={handleLogout} />
        ) : (
          <AuthPage onLoginSuccess={handleLoginSuccess} />
        )}
      </AntApp>
    </ConfigProvider>
  );
}

export default App;
