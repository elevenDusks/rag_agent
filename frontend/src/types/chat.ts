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
