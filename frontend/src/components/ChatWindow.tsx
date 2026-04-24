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

    let assistantMessageId = `assistant_${Date.now()}`;
    let fullContent = '';

    // 添加占位消息（显示加载动画）
    setMessages(prev => [...prev, {
      id: assistantMessageId,
      role: 'assistant',
      content: '',  // 空内容表示正在加载
      timestamp: new Date(),
    }]);

    // 使用流式接口
    const cleanup = chatApi.sendMessageStream(
      {
        message: inputValue,
        session_id: sessionId,
      },
      (token) => {
        fullContent += token;
        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantMessageId
              ? { ...msg, content: fullContent }
              : msg
          )
        );
      },
      () => {
        setLoading(false);
      },
      (error) => {
        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantMessageId
              ? { ...msg, content: '抱歉，发生了错误，请稍后重试。' }
              : msg
          )
        );
        setLoading(false);
      }
    );
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
              <rect width="48" height="48" rx="8" fill="#E2231A" />
              <path d="M24 10c-7.7 0-14 6.3-14 14s6.3 14 14 14 14-6.3 14-14-6.3-14-14-14zm0 24c-5.5 0-10-4.5-10-10s4.5-10 10-10 10 4.5 10 10-4.5 10-10 10zm-2-14h4v8h-4v-8zm0-4h4v3h-4v-3z" fill="white" />
            </svg>
            <div className="logo-text">
              <h1>京东智能客服</h1>
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
              <h2>您好，我是京东智能客服</h2>
              <p>购物、配送、售后、会员等问题，都可以问我</p>
              <div className="suggestion-chips">
                <button className="chip" onClick={() => setInputValue('7天无理由退货流程是什么？')}>
                  7天无理由退货流程
                </button>
                <button className="chip" onClick={() => setInputValue('如何申请价格保护？')}>
                  如何申请价格保护
                </button>
                <button className="chip" onClick={() => setInputValue('PLUS会员有哪些权益？')}>
                  PLUS会员权益
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
                    {msg.content ? (
                      renderContent(msg.content)
                    ) : (
                      <div className="loading-dots">
                        <span className="loading-dot" />
                        <span className="loading-dot" />
                        <span className="loading-dot" />
                      </div>
                    )}
                  </div>
                  {getMessageActions(msg)}
                </div>
              </div>
            ))
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
            placeholder="输入购物咨询... (Shift + Enter 换行)"
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
          京东智能客服可以帮您解答购物问题，重要信息请以官方为准。
        </p>
      </footer>
    </div>
  );
}
