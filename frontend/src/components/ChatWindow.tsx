import { useState, useRef, useEffect, useMemo } from 'react';
import { Input, Button, Spin } from 'antd';
import { SendOutlined, UserOutlined, RobotOutlined, ShoppingOutlined } from '@ant-design/icons';
import type { Message } from '../types/chat';
import { chatApi } from '../services/api';
import MarkdownIt from 'markdown-it';

const { TextArea } = Input;

const md = new MarkdownIt();

const markdownStyles = `
  .markdown-body {
    line-height: 1.7;
    font-size: 15px;
  }
  .markdown-body p {
    margin: 0 0 10px 0;
    text-indent: 2em;
  }
  .markdown-body p:first-child {
    margin-top: 0;
  }
  .markdown-body p:last-child {
    margin-bottom: 0;
  }
  .markdown-body ul, .markdown-body ol {
    margin: 10px 0;
    padding-left: 2em;
  }
  .markdown-body li {
    margin: 5px 0;
  }
  .markdown-body strong {
    font-weight: 600;
  }
  .markdown-body br {
    content: '';
    display: block;
    margin: 4px 0;
  }
`;

export function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const renderContent = (content: string, role: 'user' | 'assistant') => {
    if (role === 'user') {
      return <div style={{ textIndent: 0 }}>{content}</div>;
    }
    return (
      <>
        <style>{markdownStyles}</style>
        <div
          className="markdown-body"
          dangerouslySetInnerHTML={{ __html: md.render(content) }}
        />
      </>
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
    } catch (error) {
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: 24,
    }}>
      <div style={{
        flex: 1,
        maxWidth: 900,
        width: '100%',
        margin: '0 auto',
        background: 'white',
        borderRadius: 16,
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '20px 24px',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}>
          <div style={{
            width: 48,
            height: 48,
            borderRadius: '50%',
            background: 'rgba(255, 255, 255, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <ShoppingOutlined style={{ fontSize: 24 }} />
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>电商客服智能助手</h1>
            <p style={{ margin: '4px 0 0 0', fontSize: 13, opacity: 0.9 }}>在线为您服务</p>
          </div>
        </div>

        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: 24,
          background: 'linear-gradient(180deg, #f7f9fc 0%, #fff 100%)',
        }}>
          {messages.length === 0 ? (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: '#666',
            }}>
              <div style={{
                width: 100,
                height: 100,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: 24,
                boxShadow: '0 8px 24px rgba(102, 126, 234, 0.4)',
              }}>
                <RobotOutlined style={{ fontSize: 50, color: 'white' }} />
              </div>
              <h2 style={{ margin: '0 0 8px 0', fontSize: 20, color: '#333' }}>欢迎咨询</h2>
              <p style={{ margin: 0, color: '#888', fontSize: 14 }}>请输入您的问题，我会尽力为您解答</p>
            </div>
          ) : (
            messages.map(msg => (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  marginBottom: 20,
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    maxWidth: '75%',
                    flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                    gap: 12,
                  }}
                >
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: '50%',
                      background: msg.role === 'user' 
                        ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                        : 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                      flexShrink: 0,
                    }}
                  >
                    {msg.role === 'user' ? (
                      <UserOutlined style={{ color: 'white', fontSize: 20 }} />
                    ) : (
                      <RobotOutlined style={{ color: 'white', fontSize: 20 }} />
                    )}
                  </div>
                  <div
                    style={{
                      padding: '14px 18px',
                      borderRadius: msg.role === 'user' 
                        ? '18px 18px 4px 18px'
                        : '18px 18px 18px 4px',
                      background: msg.role === 'user' 
                        ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                        : 'white',
                      color: msg.role === 'user' ? 'white' : '#333',
                      textAlign: 'left',
                      boxShadow: msg.role === 'user' 
                        ? '0 4px 12px rgba(102, 126, 234, 0.3)'
                        : '0 2px 8px rgba(0, 0, 0, 0.08)',
                      overflow: 'hidden',
                    }}
                  >
                    {renderContent(msg.content, msg.role)}
                  </div>
                </div>
              </div>
            ))
          )}
          {loading && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              marginBottom: 20,
              gap: 12,
            }}>
              <div style={{
                width: 40,
                height: 40,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <Spin size="small" style={{ color: 'white' }} />
              </div>
              <div style={{
                padding: '14px 18px',
                borderRadius: '18px 18px 18px 4px',
                background: 'white',
                color: '#888',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
              }}>
                客服正在思考中...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div style={{
          padding: '20px 24px 24px 24px',
          borderTop: '1px solid #f0f0f0',
          background: 'white',
        }}>
          <div style={{
            display: 'flex',
            gap: 12,
            alignItems: 'flex-end',
          }}>
            <TextArea
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="请输入您的问题，按 Enter 发送..."
              autoSize={{ minRows: 1, maxRows: 4 }}
              style={{
                flex: 1,
                borderRadius: 12,
                border: '2px solid #e8e8e8',
                padding: '12px 16px',
                fontSize: 15,
                transition: 'all 0.3s',
              }}
              onFocus={(e) => e.target.style.borderColor = '#667eea'}
              onBlur={(e) => e.target.style.borderColor = '#e8e8e8'}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              loading={loading}
              disabled={!inputValue.trim()}
              size="large"
              style={{
                height: 'auto',
                padding: '12px 32px',
                borderRadius: 12,
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: 'none',
                fontSize: 15,
                fontWeight: 500,
                boxShadow: '0 4px 12px rgba(102, 126, 234, 0.4)',
                transition: 'all 0.3s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 6px 16px rgba(102, 126, 234, 0.5)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
              }}
            >
              发送
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
