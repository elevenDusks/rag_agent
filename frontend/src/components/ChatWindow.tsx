import { useState, useRef, useEffect } from 'react';
import { Button, Input, Dropdown, Tooltip, message, Switch, Collapse, Tag } from 'antd';
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
  ThunderboltOutlined,
  ToolOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import MarkdownIt from 'markdown-it';
// @ts-ignore - markdown-it 类型定义问题
import { chatApi, agentApi } from '../services/api';
import type { Message, ToolCall } from '../types/chat';
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

  // Agent mode state
  const [agentMode, setAgentMode] = useState(false);
  const [currentToolCalls, setCurrentToolCalls] = useState<ToolCall[]>([]);
  const [agentType] = useState<'react' | 'plan_execute' | 'conversational'>('react');
  const [showToolPanel, setShowToolPanel] = useState(false);

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
    setCurrentToolCalls([]);

    let assistantMessageId = `assistant_${Date.now()}`;
    let fullContent = '';

    // 添加占位消息（显示加载动画）
    setMessages(prev => [...prev, {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    }]);

    if (agentMode) {
      // Agent 模式
      try {
        const response = await agentApi.chat({
          message: inputValue,
          session_id: sessionId,
          agent_type: agentType,
          stream: false,
        });

        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantMessageId
              ? { ...msg, content: response.answer }
              : msg
          )
        );
        setCurrentToolCalls(response.tool_calls || []);
      } catch (error) {
        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantMessageId
              ? { ...msg, content: '抱歉，发生了错误，请稍后重试。' }
              : msg
          )
        );
      } finally {
        setLoading(false);
      }
    } else {
      // 普通聊天模式
      chatApi.sendMessageStream(
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
        () => {
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
              <rect width="48" height="48" rx="12" fill="#1890ff" />
              <circle cx="24" cy="20" r="8" stroke="white" strokeWidth="3" fill="none" />
              <path d="M24 32c-6 0-11 3-11 8v2h22v-2c0-5-5-8-11-8z" stroke="white" strokeWidth="3" fill="none" />
            </svg>
            <div className="logo-text">
              <h1>{agentMode ? '智能助手' : '京东客服'}</h1>
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
              <h2>{agentMode ? '您好，我是智能助手' : '您好，我是京东客服'}</h2>
              <p>{agentMode ? '我可以帮您回答各类问题，也可以搜索知识库或互联网获取信息' : '购物、配送、售后、会员等问题，都可以问我'}</p>
              <div className="suggestion-chips">
                {agentMode ? (
                  <>
                    <button className="chip" onClick={() => setInputValue('今天有什么新闻？')}>
                      今天有什么新闻
                    </button>
                    <button className="chip" onClick={() => setInputValue('帮我计算 123 * 456')}>
                      计算数学题
                    </button>
                    <button className="chip" onClick={() => setInputValue('介绍一下 RAG 技术')}>
                      介绍 RAG 技术
                    </button>
                  </>
                ) : (
                  <>
                    <button className="chip" onClick={() => setInputValue('7天无理由退货流程是什么？')}>
                      7天无理由退货流程
                    </button>
                    <button className="chip" onClick={() => setInputValue('如何申请价格保护？')}>
                      如何申请价格保护
                    </button>
                    <button className="chip" onClick={() => setInputValue('PLUS会员有哪些权益？')}>
                      PLUS会员权益
                    </button>
                  </>
                )}
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
        {agentMode && (
          <div className="agent-tool-panel">
            <div className="tool-panel-header">
              <ToolOutlined />
              <span>工具调用记录</span>
              <Tag color="blue">{currentToolCalls.length} 个工具</Tag>
              <Button
                type="text"
                size="small"
                onClick={() => setShowToolPanel(!showToolPanel)}
              >
                {showToolPanel ? '收起' : '展开'}
              </Button>
            </div>
            {showToolPanel && currentToolCalls.length > 0 && (
              <Collapse ghost className="tool-collapse">
                {currentToolCalls.map((tc, index) => (
                  <Collapse.Panel
                    key={index}
                    header={
                      <span>
                        <Tag color={tc.success ? 'green' : 'red'}>
                          {tc.success ? <CheckOutlined /> : <LoadingOutlined />}
                        </Tag>
                        {tc.tool}
                      </span>
                    }
                  >
                    <div className="tool-detail">
                      <div><strong>输入:</strong> {JSON.stringify(tc.input)}</div>
                      <div><strong>输出:</strong> {String(tc.output).slice(0, 200)}</div>
                      {tc.error && <div className="tool-error"><strong>错误:</strong> {tc.error}</div>}
                    </div>
                  </Collapse.Panel>
                ))}
              </Collapse>
            )}
          </div>
        )}
        <div className="input-container">
          <div className="mode-switch">
            <Tooltip title={agentMode ? '切换到普通模式' : '开启 Agent 模式（可使用工具）'}>
              <div className="switch-wrapper">
                <ThunderboltOutlined className={agentMode ? 'agent-icon active' : 'agent-icon'} />
                <Switch
                  size="small"
                  checked={agentMode}
                  onChange={(checked) => setAgentMode(checked)}
                />
              </div>
            </Tooltip>
          </div>
          <TextArea
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={agentMode ? 'Agent 模式：可以调用工具...' : '输入您想咨询的问题...'}
            autoSize={{ minRows: 1, maxRows: 4 }}
            className="chat-input"
          />
          <Button
            type="primary"
            icon={agentMode ? <ThunderboltOutlined /> : <SendOutlined />}
            onClick={handleSend}
            loading={loading}
            disabled={!inputValue.trim()}
            className="send-btn"
          />
        </div>
        <p className="input-hint">
          {agentMode ? (
            <span className="agent-hint">
              Agent 模式已开启，AI 可以调用工具获取信息 | 类型: {agentType}
            </span>
          ) : (
            <span className="agent-hint">
              京东客服可以帮您解答购物问题，开启 Agent 模式可获取更全面的信息
            </span>
          )}
        </p>
      </footer>
    </div>
  );
}
