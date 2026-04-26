export interface ChatRequest {
  message: string;
  session_id?: string;
  context?: string[];
}

export interface ChatResponse {
  message: string;
  session_id: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name?: string;
}

// ============ Agent 相关类型 ============

export interface ToolCall {
  tool: string;
  input: Record<string, unknown>;
  output: unknown;
  success: boolean;
  error?: string;
}

export interface AgentRequest {
  message: string;
  agent_type: 'react' | 'plan_execute' | 'conversational';
  session_id?: string;
  tools?: string[];
  stream?: boolean;
  context?: string[];
}

export interface AgentResponse {
  answer: string;
  tool_calls: ToolCall[];
  iterations: number;
  agent_type: string;
  session_id?: string;
  intermediate_steps: string[];
}

export interface ToolSchema {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface ToolListResponse {
  tools: ToolSchema[];
  total: number;
}
