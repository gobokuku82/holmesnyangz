// Types for the Real Estate Chatbot

export interface Message {
  id: string;
  content: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
}

export interface WorkflowStatus {
  stage: 'idle' | 'analyzing' | 'planning' | 'executing' | 'completed' | 'error';
  progress: number;
  currentAgent?: string;
  message?: string;
}

export interface AgentStatus {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  progress: number;
  message?: string;
}

export interface ChatSession {
  sessionId: string;
  threadId?: string;
  userId: string;
  userName: string;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface ChatRequest {
  query: string;
  threadId?: string;
  streaming?: boolean;
}

export interface ChatResponse {
  response: string;
  threadId: string;
  workflowStatus: string;
  intent?: string;
  confidence?: number;
  agentsUsed?: string[];
  executionTime?: number;
  error?: string;
}

export interface SessionResponse {
  sessionId: string;
  userId: string;
  userName: string;
  userRole: string;
  createdAt: string;
  availableAgents: string[];
  features: Record<string, boolean>;
}

export type SpinnerType = 'thinking' | 'planning' | 'executing' | 'main';

export interface SpinnerConfig {
  type: SpinnerType;
  message: string;
  progress?: number;
}