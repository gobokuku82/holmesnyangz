import React, { useRef, useEffect } from 'react';
import styled from 'styled-components';
import { Message, AgentStatus } from '../types';

interface MessageListProps {
  messages: Message[];
}

const Container = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f5f5f5;
`;

const MessageItem = styled.div<{ isUser: boolean; isSystem?: boolean }>`
  display: flex;
  justify-content: ${props => props.isUser ? 'flex-end' : props.isSystem ? 'center' : 'flex-start'};
  margin-bottom: 15px;
  animation: fadeIn 0.3s ease;
  
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
`;

const MessageBubble = styled.div<{ isUser: boolean }>`
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 18px;
  background: ${props => props.isUser ? 
    'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 
    'white'};
  color: ${props => props.isUser ? 'white' : '#333'};
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
  position: relative;
  
  &::before {
    content: '';
    position: absolute;
    bottom: 0;
    ${props => props.isUser ? 'right: -8px' : 'left: -8px'};
    width: 0;
    height: 0;
    border-style: solid;
    border-width: ${props => props.isUser ? '10px 0 10px 10px' : '10px 10px 10px 0'};
    border-color: ${props => props.isUser ? 
      'transparent transparent transparent #764ba2' : 
      'transparent white transparent transparent'};
  }
`;

const MessageText = styled.p`
  margin: 0;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
`;

const MessageTime = styled.span`
  display: block;
  font-size: 11px;
  opacity: 0.7;
  margin-top: 5px;
`;

const Avatar = styled.div<{ isUser: boolean }>`
  width: 40px;
  height: 40px;
  border-radius: 50%;
  margin: ${props => props.isUser ? '0 0 0 10px' : '0 10px 0 0'};
  background: ${props => props.isUser ? '#667eea' : '#e0e0e0'};
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
`;

const MessageContent = styled.div<{ isUser: boolean }>`
  display: flex;
  align-items: flex-end;
  flex-direction: ${props => props.isUser ? 'row-reverse' : 'row'};
`;

const SystemMessage = styled.div`
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 12px;
  padding: 15px;
  max-width: 80%;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
`;

const ProgressContainer = styled.div`
  margin-top: 10px;
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 4px;
  overflow: hidden;
`;

const ProgressFill = styled.div<{ progress: number }>`
  width: ${props => props.progress}%;
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s ease;
`;

const ProgressText = styled.div`
  font-size: 12px;
  margin-top: 5px;
  color: #666;
  text-align: center;
`;

const AgentGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
  margin-top: 10px;
`;

const AgentCard = styled.div<{ status: string }>`
  padding: 10px;
  border-radius: 8px;
  background: ${props => {
    switch (props.status) {
      case 'completed': return 'linear-gradient(135deg, #4CAF50, #8BC34A)';
      case 'running': return 'linear-gradient(135deg, #FFC107, #FFD54F)';
      case 'error': return 'linear-gradient(135deg, #f44336, #e57373)';
      default: return 'linear-gradient(135deg, #e0e0e0, #f5f5f5)';
    }
  }};
  color: ${props => props.status === 'pending' ? '#666' : 'white'};
  font-size: 12px;
  text-align: center;
  transition: all 0.3s ease;
`;

const AgentName = styled.div`
  font-weight: 600;
  margin-bottom: 5px;
`;

const AgentProgress = styled.div`
  font-size: 11px;
  opacity: 0.9;
`;

const TypingIndicator = styled.div`
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: white;
  border-radius: 18px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
  
  span {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #999;
    margin: 0 2px;
    animation: typing 1.4s infinite;
    
    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
  
  @keyframes typing {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-10px); }
  }
`;

const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const formatTime = (date: Date) => {
    return new Date(date).toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const renderSystemMessage = (message: Message) => {
    if (!message.metadata) return null;
    
    return (
      <SystemMessage>
        <MessageText>{message.content}</MessageText>
        
        {message.metadata.type === 'progress' && message.metadata.progress !== undefined && (
          <ProgressContainer>
            <ProgressBar>
              <ProgressFill progress={message.metadata.progress} />
            </ProgressBar>
            <ProgressText>{message.metadata.progress}% 완료</ProgressText>
          </ProgressContainer>
        )}
        
        {message.metadata.type === 'agent-status' && message.metadata.agents && (
          <AgentGrid>
            {message.metadata.agents.map((agent) => (
              <AgentCard key={agent.id} status={agent.status}>
                <AgentName>{agent.name}</AgentName>
                {agent.status === 'running' && (
                  <AgentProgress>{agent.progress}%</AgentProgress>
                )}
                {agent.status === 'completed' && (
                  <AgentProgress>✓ 완료</AgentProgress>
                )}
                {agent.status === 'pending' && (
                  <AgentProgress>대기중</AgentProgress>
                )}
              </AgentCard>
            ))}
          </AgentGrid>
        )}
      </SystemMessage>
    );
  };

  return (
    <Container>
      {messages.map((message) => (
        <MessageItem 
          key={message.id} 
          isUser={message.sender === 'user'}
          isSystem={message.sender === 'system'}
        >
          {message.sender === 'system' ? (
            renderSystemMessage(message)
          ) : (
            <MessageContent isUser={message.sender === 'user'}>
              <Avatar isUser={message.sender === 'user'}>
                {message.sender === 'user' ? '👤' : '🏠'}
              </Avatar>
              <MessageBubble isUser={message.sender === 'user'}>
                <MessageText>{message.content}</MessageText>
                <MessageTime>{formatTime(message.timestamp)}</MessageTime>
              </MessageBubble>
            </MessageContent>
          )}
        </MessageItem>
      ))}
      
      {/* Show typing indicator when bot is processing */}
      {messages.length > 0 && messages[messages.length - 1].sender === 'user' && (
        <MessageItem isUser={false}>
          <MessageContent isUser={false}>
            <Avatar isUser={false}>🏠</Avatar>
            <TypingIndicator>
              <span />
              <span />
              <span />
            </TypingIndicator>
          </MessageContent>
        </MessageItem>
      )}
      
      <div ref={messagesEndRef} />
    </Container>
  );
};

export default MessageList;