// Types for the Real Estate Chatbot

export interface Message {
  id: string;
  content: string;
  sender: 'user' | 'bot' | 'system';
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
  metadata?: {
    type?: 'progress' | 'agent-status' | 'workflow';
    stage?: string;
    progress?: number;
    agents?: AgentStatus[];
  };
}

export interface WorkflowStatus {
  stage: 'idle' | 'analyzing' | 'planning' | 'executing' | 'completed' | 'error';
  progress: number;
  currentAgent?: string;
  message?: string;
  agentsSequence?: Agent[];
  currentAgentIndex?: number;
  agentProgress?: number;
}

export interface Agent {
  id: string;
  name: string;
  order: number;
  status: 'pending' | 'running' | 'completed' | 'error';
  progress: number;
  startTime?: string;
  endTime?: string;
  result?: any;
  error?: string;
}

export interface AgentStatus {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  progress: number;
  message?: string;
}

export interface WorkflowUpdateEvent {
  type: 'workflow_update';
  sessionId: string;
  threadId: string;
  stage: 'idle' | 'analyzing' | 'planning' | 'executing' | 'completed' | 'error';
  stageProgress: number;
  agentsSequence: Agent[];
  currentAgent?: string;
  currentAgentIndex: number;
  agentProgress: number;
  message?: string;
  timestamp: string;
  elapsedTime: number;
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