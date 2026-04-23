import axios from 'axios';
import type { ChatRequest, ChatResponse } from '../types/chat';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

export const chatApi = {
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>('/chat', request);
    return response.data;
  },
};
