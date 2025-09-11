import React, { useRef, useEffect } from 'react';
import styled from 'styled-components';
import { Message, WorkflowStatus } from '../types';
import ProgressFlow from './ProgressFlow';

interface MessageListProps {
  messages: Message[];
  workflowStatus: WorkflowStatus;
  isProcessing: boolean;
}

const Container = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f5f5f5;
`;

const MessageItem = styled.div<{ isUser: boolean }>`
  display: flex;
  justify-content: ${props => props.isUser ? 'flex-end' : 'flex-start'};
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
  width: ${props => props.isUser ? '40px' : '60px'};
  height: ${props => props.isUser ? '40px' : '60px'};
  border-radius: 50%;
  margin: ${props => props.isUser ? '0 0 0 10px' : '0 10px 0 0'};
  background: ${props => props.isUser ? '#667eea' : 'transparent'};
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
  overflow: hidden;
`;

const BotAvatarImg = styled.img`
  width: 100%;
  height: 100%;
  object-fit: cover;
`;

const MessageContent = styled.div<{ isUser: boolean }>`
  display: flex;
  align-items: flex-end;
  flex-direction: ${props => props.isUser ? 'row-reverse' : 'row'};
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

const MessageList: React.FC<MessageListProps> = ({ messages, workflowStatus, isProcessing }) => {
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

  return (
    <Container>
      {messages.filter(m => m.sender !== 'system').map((message) => (
        <MessageItem 
          key={message.id} 
          isUser={message.sender === 'user'}
        >
          <MessageContent isUser={message.sender === 'user'}>
            <Avatar isUser={message.sender === 'user'}>
              {message.sender === 'user' ? (
                '👤'
              ) : (
                <BotAvatarImg src="/character/img_main.png" alt="Bot" />
              )}
            </Avatar>
            <MessageBubble isUser={message.sender === 'user'}>
              <MessageText>{message.content}</MessageText>
              <MessageTime>{formatTime(message.timestamp)}</MessageTime>
            </MessageBubble>
          </MessageContent>
        </MessageItem>
      ))}
      
      {/* Show ProgressFlow when bot is processing */}
      {isProcessing && workflowStatus.stage !== 'idle' && (
        <MessageItem isUser={false}>
          <MessageContent isUser={false}>
            <Avatar isUser={false}>
              <BotAvatarImg src="/character/img_main.png" alt="Bot" />
            </Avatar>
            <ProgressFlow 
              status={workflowStatus}
              visible={true}
              style={{ minWidth: '700px' }}
            />
          </MessageContent>
        </MessageItem>
      )}
      
      <div ref={messagesEndRef} />
    </Container>
  );
};

export default MessageList;