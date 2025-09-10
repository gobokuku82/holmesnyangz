import React, { useState, useEffect, useCallback } from 'react';
import styled from 'styled-components';
import MessageList from './MessageList';
import InputArea from './InputArea';
import SpinnerModal from './SpinnerModal';
import { Message, WorkflowStatus, AgentStatus as AgentStatusType, SpinnerConfig } from '../types';
import { mockApi } from '../services/api';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f0f2f5;
`;

const Header = styled.header`
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
`;

const HeaderContent = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const Title = styled.h1`
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
`;

const Status = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  opacity: 0.9;
`;

const StatusDot = styled.div<{ online: boolean }>`
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: ${props => props.online ? '#4CAF50' : '#f44336'};
  animation: ${props => props.online ? 'pulse 2s infinite' : 'none'};
  
  @keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7); }
    70% { box-shadow: 0 0 0 10px rgba(76, 175, 80, 0); }
    100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0); }
  }
`;

const MainContent = styled.main`
  flex: 1;
  display: flex;
  flex-direction: column;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  background: white;
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
`;

const ChatContainer = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
`;

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [workflowStatus, setWorkflowStatus] = useState<WorkflowStatus>({
    stage: 'idle',
    progress: 0,
  });
  const [agentStatuses, setAgentStatuses] = useState<AgentStatusType[]>([]);
  const [spinnerConfig, setSpinnerConfig] = useState<SpinnerConfig | null>(null);
  const [sessionId, setSessionId] = useState<string>('');

  // Initialize session
  useEffect(() => {
    const initSession = async () => {
      try {
        const session = await mockApi.createSession();
        setSessionId(session.sessionId);
        
        // Add welcome message
        const welcomeMessage: Message = {
          id: 'welcome',
          content: '안녕하세요! 부동산 AI 어시스턴트입니다. 무엇을 도와드릴까요?',
          sender: 'bot',
          timestamp: new Date(),
        };
        setMessages([welcomeMessage]);
      } catch (error) {
        console.error('Failed to create session:', error);
      }
    };
    
    initSession();
  }, []);

  const handleSendMessage = useCallback(async (content: string) => {
    if (isProcessing) return;

    // Add user message
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      content,
      sender: 'user',
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsProcessing(true);

    try {
      // Simulate workflow with progress updates
      await mockApi.simulateWorkflow((status) => {
        setWorkflowStatus(status);
        
        // Create system message for workflow status        
        switch (status.stage) {
          case 'analyzing':
            const analyzeMessage: Message = {
              id: `system-analyzing-${Date.now()}`,
              content: '사용자 질의를 분석하고 있습니다...',
              sender: 'system',
              timestamp: new Date(),
              metadata: {
                type: 'progress',
                stage: 'analyzing',
                progress: status.progress,
              },
            };
            setMessages(prev => {
              const filteredMessages = prev.filter(m => m.sender !== 'system');
              return [...filteredMessages, analyzeMessage];
            });
            setSpinnerConfig({
              type: 'thinking',
              message: '사용자 질의를 분석하고 있습니다...',
              progress: status.progress,
            });
            break;
          case 'planning':
            const planMessage: Message = {
              id: `system-planning-${Date.now()}`,
              content: '최적의 실행 계획을 수립하고 있습니다...',
              sender: 'system',
              timestamp: new Date(),
              metadata: {
                type: 'progress',
                stage: 'planning',
                progress: status.progress,
              },
            };
            setMessages(prev => {
              const filteredMessages = prev.filter(m => m.sender !== 'system');
              return [...filteredMessages, planMessage];
            });
            setSpinnerConfig({
              type: 'planning',
              message: '최적의 실행 계획을 수립하고 있습니다...',
              progress: status.progress,
            });
            break;
          case 'executing':
            // Update agent statuses
            const agents = ['price_search_agent', 'finance_agent', 'legal_agent'];
            const agentNames: { [key: string]: string } = {
              'price_search_agent': '시세 검색',
              'finance_agent': '금융 분석',
              'legal_agent': '법률 검토',
            };
            const currentAgentIndex = Math.floor(status.progress / (100 / agents.length));
            
            const currentAgents = agents.map((id, index) => ({
              id,
              name: agentNames[id] || id,
              status: index < currentAgentIndex ? 'completed' : 
                      index === currentAgentIndex ? 'running' : 'pending',
              progress: index === currentAgentIndex ? 
                        (status.progress % (100 / agents.length)) * agents.length : 
                        index < currentAgentIndex ? 100 : 0,
            } as AgentStatusType));
            
            setAgentStatuses(currentAgents);
            
            const executeMessage: Message = {
              id: `system-executing-${Date.now()}`,
              content: '에이전트를 실행하고 있습니다',
              sender: 'system',
              timestamp: new Date(),
              metadata: {
                type: 'agent-status',
                stage: 'executing',
                progress: status.progress,
                agents: currentAgents,
              },
            };
            
            setMessages(prev => {
              const filteredMessages = prev.filter(m => m.sender !== 'system');
              return [...filteredMessages, executeMessage];
            });
            
            setSpinnerConfig({
              type: 'executing',
              message: '에이전트를 실행하고 있습니다...',
              progress: status.progress,
            });
            break;
          case 'completed':
            setSpinnerConfig(null);
            break;
        }
      });

      // Get response
      const response = await mockApi.sendMessage(content);
      
      // Add bot response
      const botMessage: Message = {
        id: `bot-${Date.now()}`,
        content: response.response,
        sender: 'bot',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, botMessage]);
      
    } catch (error) {
      console.error('Failed to send message:', error);
      
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        content: '죄송합니다. 처리 중 오류가 발생했습니다. 다시 시도해 주세요.',
        sender: 'bot',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
      
    } finally {
      setIsProcessing(false);
      setSpinnerConfig(null);
      setWorkflowStatus({ stage: 'idle', progress: 0 });
      setAgentStatuses([]);
    }
  }, [isProcessing]);

  return (
    <Container>
      <Header>
        <HeaderContent>
          <Title>
            🏠 부동산 AI 어시스턴트
          </Title>
          <Status>
            <StatusDot online={true} />
            <span>온라인 | 세션: {sessionId}</span>
          </Status>
        </HeaderContent>
      </Header>

      <MainContent>
        <ChatContainer>
          <MessageList messages={messages} />
          <InputArea 
            onSendMessage={handleSendMessage} 
            disabled={isProcessing}
          />
        </ChatContainer>
      </MainContent>

      <SpinnerModal 
        config={spinnerConfig}
        agentStatuses={agentStatuses.map(agent => ({
          name: agent.name,
          progress: agent.progress,
        }))}
      />
    </Container>
  );
};

export default ChatInterface;