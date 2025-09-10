import axios from 'axios';
import { ChatRequest, ChatResponse, SessionResponse } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Session Management
export const createSession = async (userId: string, userName: string): Promise<SessionResponse> => {
  const response = await api.post<SessionResponse>('/sessions', {
    user_id: userId,
    user_name: userName,
    user_role: 'user',
  });
  return response.data;
};

export const deleteSession = async (sessionId: string): Promise<void> => {
  await api.delete(`/sessions/${sessionId}`);
};

// Chat
export const sendMessage = async (
  sessionId: string,
  request: ChatRequest
): Promise<ChatResponse> => {
  const response = await api.post<ChatResponse>(`/chat/${sessionId}`, request);
  return response.data;
};

// System Status
export const getSystemStatus = async () => {
  const response = await api.get('/status');
  return response.data;
};

// Mock Data Service (for development)
export const mockApi = {
  createSession: async (): Promise<SessionResponse> => {
    return {
      sessionId: 'mock-session-' + Date.now(),
      userId: 'user123',
      userName: 'Test User',
      userRole: 'user',
      createdAt: new Date().toISOString(),
      availableAgents: ['analyzer_agent', 'price_search_agent', 'finance_agent', 'location_agent', 'legal_agent'],
      features: {
        enable_memory: true,
        enable_tools: true,
        enable_streaming: false,
      },
    };
  },

  sendMessage: async (message: string): Promise<ChatResponse> => {
    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    return {
      response: `분석 결과: "${message}"에 대한 답변입니다. 강남구 아파트 평균 시세는 평당 5,000만원입니다.`,
      threadId: 'thread-' + Date.now(),
      workflowStatus: 'completed',
      intent: 'price_inquiry',
      confidence: 0.95,
      agentsUsed: ['analyzer_agent', 'price_search_agent'],
      executionTime: 2.5,
    };
  },

  simulateWorkflow: async (
    onProgress: (status: any) => void
  ): Promise<ChatResponse> => {
    // Stage 1: Analyzing
    for (let i = 0; i <= 100; i += 25) {
      onProgress({
        stage: 'analyzing',
        progress: i,
        message: '사용자 질의를 분석하고 있습니다...',
      });
      await new Promise(resolve => setTimeout(resolve, 300));
    }

    // Stage 2: Planning
    for (let i = 0; i <= 100; i += 33) {
      onProgress({
        stage: 'planning',
        progress: Math.min(i, 100),
        message: '실행 계획을 수립하고 있습니다...',
      });
      await new Promise(resolve => setTimeout(resolve, 250));
    }

    // Stage 3: Executing
    const agents = ['price_search_agent', 'finance_agent', 'legal_agent'];
    for (let i = 0; i < agents.length; i++) {
      // Each agent progresses from 0 to 100
      for (let progress = 0; progress <= 100; progress += 20) {
        const overallProgress = ((i * 100 + progress) / agents.length);
        onProgress({
          stage: 'executing',
          progress: Math.min(overallProgress, 100),
          currentAgent: agents[i],
          message: `에이전트를 실행하고 있습니다...`,
        });
        await new Promise(resolve => setTimeout(resolve, 200));
      }
    }

    // Stage 4: Completed
    onProgress({
      stage: 'completed',
      progress: 100,
      message: '처리 완료',
    });

    return {
      response: '종합 분석 결과: 강남구 아파트 평균 시세는 평당 5,000만원이며, 대출 가능 금액은 최대 6억원입니다. 취득세는 약 3,000만원이 예상됩니다.',
      threadId: 'thread-' + Date.now(),
      workflowStatus: 'completed',
      intent: 'purchase_consultation',
      confidence: 0.92,
      agentsUsed: agents,
      executionTime: 5.5,
    };
  },
};

// Export the appropriate service based on environment
const USE_MOCK = process.env.REACT_APP_USE_MOCK === 'true' || !process.env.REACT_APP_API_URL;

export default USE_MOCK ? mockApi : api;