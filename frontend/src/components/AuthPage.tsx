import { useState } from 'react';
import { Form, Input, Button, Card, message, Tabs } from 'antd';
import { UserOutlined, MailOutlined, LockOutlined, GoogleOutlined, GithubOutlined } from '@ant-design/icons';
import { authApi, setAuthToken, setStoredUser } from '../services/api';
import type { LoginRequest, RegisterRequest } from '../types/chat';
import './AuthPage.css';

interface AuthPageProps {
  onLoginSuccess: () => void;
}

export function AuthPage({ onLoginSuccess }: AuthPageProps) {
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('login');

  const handleLogin = async (values: LoginRequest) => {
    setLoading(true);
    try {
      const response = await authApi.login(values);
      setAuthToken(response.access_token);
      const user = await authApi.getMe();
      setStoredUser(user);
      message.success('登录成功');
      onLoginSuccess();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '登录失败，请检查用户名和密码');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (values: RegisterRequest) => {
    setLoading(true);
    try {
      await authApi.register(values);
      message.success('注册成功，请登录');
      setActiveTab('login');
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '注册失败');
    } finally {
      setLoading(false);
    }
  };

  const handleOAuthLogin = (provider: string) => {
    message.info(`${provider} OAuth 登录功能开发中...`);
  };

  const items = [
    {
      key: 'login',
      label: '登录',
      children: (
        <Form<LoginRequest>
          name="login"
          onFinish={handleLogin}
          layout="vertical"
          requiredMark={false}
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input
              prefix={<UserOutlined className="input-icon" />}
              placeholder="用户名"
              autoComplete="username"
            />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              prefix={<LockOutlined className="input-icon" />}
              placeholder="密码"
              autoComplete="current-password"
            />
          </Form.Item>
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              className="submit-btn"
            >
              登录
            </Button>
          </Form.Item>
        </Form>
      ),
    },
    {
      key: 'register',
      label: '注册',
      children: (
        <Form<RegisterRequest>
          name="register"
          onFinish={handleRegister}
          layout="vertical"
          requiredMark={false}
          size="large"
        >
          <Form.Item
            name="username"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '用户名至少3个字符' },
            ]}
          >
            <Input
              prefix={<UserOutlined className="input-icon" />}
              placeholder="用户名"
              autoComplete="username"
            />
          </Form.Item>
          <Form.Item
            name="email"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input
              prefix={<MailOutlined className="input-icon" />}
              placeholder="邮箱"
              autoComplete="email"
            />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少6个字符' },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined className="input-icon" />}
              placeholder="密码"
              autoComplete="new-password"
            />
          </Form.Item>
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              className="submit-btn"
            >
              注册
            </Button>
          </Form.Item>
        </Form>
      ),
    },
  ];

  return (
    <div className="auth-page">
      <div className="auth-background">
        <div className="bg-gradient" />
        <div className="bg-grid" />
        <div className="bg-blur-1" />
        <div className="bg-blur-2" />
      </div>
      <div className="auth-container">
        <Card className="auth-card" bordered={false}>
          <div className="auth-header">
            <div className="logo-container">
              <svg className="logo-icon" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect width="48" height="48" rx="12" fill="url(#logo-gradient)" />
                <path d="M14 18h20v4H14v-4zm0 8h16v4H14v-4zm0 8h12v4H14v-4z" fill="white" />
                <defs>
                  <linearGradient id="logo-gradient" x1="0" y1="0" x2="48" y2="48">
                    <stop stopColor="#6366f1" />
                    <stop offset="1" stopColor="#8b5cf6" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <h1 className="auth-title">RAG 智能助手</h1>
            <p className="auth-subtitle">登录以开始智能问答之旅</p>
          </div>

          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={items}
            className="auth-tabs"
          />

          <div className="oauth-divider">
            <span>或使用以下方式登录</span>
          </div>

          <div className="oauth-buttons">
            <Button
              icon={<GoogleOutlined />}
              onClick={() => handleOAuthLogin('Google')}
              className="oauth-btn oauth-google"
              size="large"
            >
              Google
            </Button>
            <Button
              icon={<GithubOutlined />}
              onClick={() => handleOAuthLogin('GitHub')}
              className="oauth-btn oauth-github"
              size="large"
            >
              GitHub
            </Button>
          </div>
        </Card>

        <p className="auth-footer">
          登录即表示您同意我们的
          <a href="#terms">服务条款</a> 和
          <a href="#privacy">隐私政策</a>
        </p>
      </div>
    </div>
  );
}
