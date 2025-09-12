import React, { useState, useEffect, useCallback } from 'react';
import styled from 'styled-components';
import MessageList from './MessageList';
import InputArea from './InputArea';
import { Message, WorkflowStatus, WorkflowUpdateEvent, Agent } from '../types';
import { createSession } from '../services/api';
import websocketService, { WebSocketMessage } from '../services/websocket';

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
    agentsSequence: [],
  });
  const [sessionId, setSessionId] = useState<string>('');
  const [isConnected, setIsConnected] = useState(false);
  const [useWebSocket, setUseWebSocket] = useState(true); // WebSocket 사용 여부

  // Initialize session and WebSocket
  useEffect(() => {
    const initSession = async () => {
      try {
        // Create real session with backend
        const session = await createSession('user-' + Date.now(), 'User');
        setSessionId(session.sessionId);
        
        // WebSocket 연결 시도 (선택적)
        if (useWebSocket) {
          try {
            await websocketService.connect(session.sessionId);
            setIsConnected(true);
            
            // WebSocket 이벤트 리스너 등록
            websocketService.on('workflow_update', handleWorkflowUpdate);
            websocketService.on('response', handleResponse);
            websocketService.on('error', handleError);
          } catch (wsError) {
            console.error('WebSocket connection failed:', wsError);
            setIsConnected(false);
          }
        }
        
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
    
    // Cleanup
    return () => {
      if (isConnected) {
        websocketService.off('workflow_update', handleWorkflowUpdate);
        websocketService.off('response', handleResponse);
        websocketService.off('error', handleError);
        websocketService.disconnect();
      }
    };
  }, [useWebSocket]);

  // WebSocket 이벤트 핸들러
  const handleWorkflowUpdate = useCallback((message: WebSocketMessage) => {
    if (message.metadata) {
      const event = message.metadata as WorkflowUpdateEvent;
      
      // 워크플로우 상태 업데이트
      setWorkflowStatus({
        stage: event.stage,
        progress: event.stageProgress,
        currentAgent: event.currentAgent,
        message: event.message,
        agentsSequence: event.agentsSequence,
        currentAgentIndex: event.currentAgentIndex,
        agentProgress: event.agentProgress,
      });
      
      // 워크플로우 완료 시 처리
      if (event.stage === 'completed') {
        setIsProcessing(false);
      }
    }
  }, []);

  const handleResponse = useCallback((message: WebSocketMessage) => {
    if (message.content) {
      const botMessage: Message = {
        id: `bot-ws-${Date.now()}`,
        content: message.content,
        sender: 'bot',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, botMessage]);
      
      // 스트리밍이 아닌 경우 처리 완료
      if (!message.metadata?.streaming) {
        setIsProcessing(false);
        // 워크플로우 상태를 completed로 변경
        setWorkflowStatus(prev => ({
          ...prev,
          stage: 'completed',
          progress: 100
        }));
        
        // 2초 후 idle 상태로 리셋
        setTimeout(() => {
          setWorkflowStatus({ stage: 'idle', progress: 0, agentsSequence: [] });
        }, 2000);
      }
    }
  }, []);

  const handleError = useCallback((message: WebSocketMessage) => {
    console.error('WebSocket error:', message.content);
    const errorMessage: Message = {
      id: `error-ws-${Date.now()}`,
      content: message.content || '오류가 발생했습니다.',
      sender: 'system',
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, errorMessage]);
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
      if (isConnected && useWebSocket) {
        // WebSocket을 통한 메시지 전송
        websocketService.sendQuery(content);
        // WebSocket 이벤트로 응답을 받음
      } else {
        // WebSocket 연결 실패 시 명확한 에러 메시지
        const errorMessage: Message = {
          id: `error-${Date.now()}`,
          content: `❌ WebSocket 연결 실패\n\n다음 사항을 확인해주세요:\n1. 백엔드 서버가 실행 중인지 확인 (http://localhost:8000)\n2. 터미널에서 'cd backend && python main.py' 실행\n3. OpenAI API 키가 .env 파일에 올바르게 설정되어 있는지 확인\n\n현재 상태: ${isConnected ? '연결됨' : '연결 안됨'}\n세션 ID: ${sessionId || '생성되지 않음'}`,
          sender: 'system',
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, errorMessage]);
        /*await mockApi.simulateWorkflow((status) => {
          setWorkflowStatus({
            ...status,
            agentsSequence: status.agentsSequence || [
              { id: 'analyzer_agent', name: '분석 에이전트', order: 0, status: 'completed', progress: 100 },
              { id: 'price_search_agent', name: '시세 검색', order: 1, status: 'completed', progress: 100 },
              { id: 'finance_agent', name: '금융 분석', order: 2, status: 'running', progress: 50 },
              { id: 'legal_agent', name: '법률 검토', order: 3, status: 'pending', progress: 0 },
            ],
            currentAgentIndex: 2,
            agentProgress: 50,
          });
        });*/

        // Get response
        //const response = await mockApi.sendMessage(content);
        
        // Add bot response
        /*const botMessage: Message = {
          id: `bot-${Date.now()}`,
          content: response.response,
          sender: 'bot',
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, botMessage]);*/
      }
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
      if (!isConnected || !useWebSocket) {
        setIsProcessing(false);
        // Keep the completed status for a moment before resetting
        setTimeout(() => {
          setWorkflowStatus({ stage: 'idle', progress: 0, agentsSequence: [] });
        }, 2000);
      }
    }
  }, [isProcessing, isConnected, useWebSocket]);

  return (
    <Container>
      <Header>
        <HeaderContent>
          <Title>
            🏠 부동산 AI 어시스턴트
          </Title>
          <Status>
            <StatusDot online={isConnected || !useWebSocket} />
            <span>
              {isConnected ? 'WebSocket 연결됨' : useWebSocket ? 'WebSocket 연결 끊김' : 'Mock API'} | 세션: {sessionId}
            </span>
          </Status>
        </HeaderContent>
      </Header>

      <MainContent>
        <ChatContainer>
          <MessageList 
            messages={messages} 
            workflowStatus={workflowStatus}
            isProcessing={isProcessing}
          />
          <InputArea 
            onSendMessage={handleSendMessage} 
            disabled={isProcessing}
          />
        </ChatContainer>
      </MainContent>
    </Container>
  );
};

export default ChatInterface;