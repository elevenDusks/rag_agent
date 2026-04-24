import { useState, useRef, useEffect } from 'react';
import { Button, Input, Dropdown, Tooltip, message } from 'antd';
import type { MenuProps } from 'antd';
import {
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  MoonOutlined,
  SunOutlined,
  LogoutOutlined,
  SettingOutlined,
  ClearOutlined,
  CopyOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import MarkdownIt from 'markdown-it';
import { chatApi } from '../services/api';
import type { Message } from '../types/chat';
import './ChatWindow.css';

const { TextArea } = Input;
const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
});

interface ChatWindowProps {
  onLogout: () => void;
}

export function ChatWindow({ onLogout }: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null;
    if (savedTheme) {
      setTheme(savedTheme);
      document.documentElement.setAttribute('data-theme', savedTheme);
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  const copyMessage = async (content: string, id: string) => {
    await navigator.clipboard.writeText(content);
    setCopiedId(id);
    message.success('已复制');
    setTimeout(() => setCopiedId(null), 2000);
  };

  const clearChat = async () => {
    try {
      await chatApi.clearMemory(sessionId);
      message.success('对话已清空');
    } catch {
      message.warning('清空本地对话成功，服务端记忆清除失败');
    }
    setMessages([]);
  };

  const renderContent = (content: string) => {
    return (
      <div
        className="markdown-content"
        dangerouslySetInnerHTML={{ __html: md.render(content) }}
      />
    );
  };

  const handleSend = async () => {
    if (!inputValue.trim() || loading) return;

    const userMessage: Message = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setLoading(true);

    try {
      const response = await chatApi.sendMessage({
        message: inputValue,
        session_id: sessionId,
      });

      const assistantMessage: Message = {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: response.message,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch {
      const errorMessage: Message = {
        id: `error_${Date.now()}`,
        role: 'assistant',
        content: '抱歉，发生了错误，请稍后重试。',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
      onClick: onLogout,
    },
  ];

  const getMessageActions = (msg: Message) => {
    if (msg.role === 'user') return null;
    return (
      <div className="message-actions">
        <Tooltip title={copiedId === msg.id ? '已复制' : '复制'}>
          <Button
            type="text"
            size="small"
            icon={copiedId === msg.id ? <CheckOutlined /> : <CopyOutlined />}
            onClick={() => copyMessage(msg.content, msg.id)}
            className="action-btn"
          />
        </Tooltip>
      </div>
    );
  };

  return (
    <div className="chat-window">
      <header className="chat-header">
        <div className="header-left">
          <div className="logo">
            <svg className="logo-icon" viewBox="0 0 48 48" fill="none">
              <rect width="48" height="48" rx="12" fill="url(#header-logo-gradient)" />
              <path d="M14 18h20v4H14v-4zm0 8h16v4H14v-4zm0 8h12v4H14v-4z" fill="white" />
              <defs>
                <linearGradient id="header-logo-gradient" x1="0" y1="0" x2="48" y2="48">
                  <stop stopColor="#6366f1" />
                  <stop offset="1" stopColor="#8b5cf6" />
                </linearGradient>
              </defs>
            </svg>
            <div className="logo-text">
              <h1>RAG 智能助手</h1>
              <span className="status">
                <span className="status-dot" />
                在线
              </span>
            </div>
          </div>
        </div>
        <div className="header-right">
          <Tooltip title={theme === 'light' ? '深色模式' : '浅色模式'}>
            <Button
              type="text"
              icon={theme === 'light' ? <MoonOutlined /> : <SunOutlined />}
              onClick={toggleTheme}
              className="theme-toggle"
            />
          </Tooltip>
          <Tooltip title="清空对话">
            <Button
              type="text"
              icon={<ClearOutlined />}
              onClick={clearChat}
              className="clear-btn"
            />
          </Tooltip>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Button type="text" className="user-avatar">
              <UserOutlined />
            </Button>
          </Dropdown>
        </div>
      </header>

      <main className="chat-main">
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="welcome-screen">
              <div className="welcome-icon">
                <RobotOutlined />
              </div>
              <h2>有什么可以帮助您的？</h2>
              <p>输入您的问题，AI 助手将为您提供智能解答</p>
              <div className="suggestion-chips">
                <button className="chip" onClick={() => setInputValue('介绍一下 RAG 技术')}>
                  介绍一下 RAG 技术
                </button>
                <button className="chip" onClick={() => setInputValue('如何优化向量检索？')}>
                  如何优化向量检索？
                </button>
                <button className="chip" onClick={() => setInputValue('Embedding 模型有哪些？')}>
                  Embedding 模型有哪些？
                </button>
              </div>
            </div>
          ) : (
            messages.map(msg => (
              <div key={msg.id} className={`message ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                </div>
                <div className="message-content-wrapper">
                  <div className="message-bubble">
                    {renderContent(msg.content)}
                  </div>
                  {getMessageActions(msg)}
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="message assistant">
              <div className="message-avatar">
                <RobotOutlined />
              </div>
              <div className="message-content-wrapper">
                <div className="message-bubble loading">
                  <span className="loading-dot" />
                  <span className="loading-dot" />
                  <span className="loading-dot" />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </main>

      <footer className="chat-footer">
        <div className="input-container">
          <TextArea
            ref={textareaRef}
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息... (Shift + Enter 换行)"
            autoSize={{ minRows: 1, maxRows: 4 }}
            className="chat-input"
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={loading}
            disabled={!inputValue.trim()}
            className="send-btn"
          />
        </div>
        <p className="input-hint">
          RAG 智能助手可以犯错，请核对重要信息。
        </p>
      </footer>
    </div>
  );
}
