import React, { useState, KeyboardEvent } from 'react';
import styled from 'styled-components';

interface InputAreaProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

const Container = styled.div`
  padding: 20px;
  background: white;
  border-top: 1px solid #e0e0e0;
`;

const InputWrapper = styled.div`
  display: flex;
  align-items: center;
  background: #f5f5f5;
  border-radius: 25px;
  padding: 5px 5px 5px 20px;
  transition: all 0.3s ease;
  
  &:focus-within {
    background: white;
    box-shadow: 0 0 0 2px #667eea;
  }
`;

const Input = styled.input`
  flex: 1;
  border: none;
  background: transparent;
  padding: 10px;
  font-size: 15px;
  outline: none;
  
  &::placeholder {
    color: #999;
  }
`;

const Button = styled.button<{ primary?: boolean }>`
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  background: ${props => props.primary ? 
    'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 
    'transparent'};
  color: ${props => props.primary ? 'white' : '#666'};
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  margin-left: 5px;
  font-size: ${props => props.primary ? '20px' : '18px'};
  
  &:hover {
    transform: scale(1.1);
    background: ${props => !props.primary && '#e0e0e0'};
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const Suggestions = styled.div`
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
  flex-wrap: wrap;
`;

const SuggestionChip = styled.button`
  padding: 8px 16px;
  border: 1px solid #667eea;
  border-radius: 20px;
  background: white;
  color: #667eea;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.3s ease;
  
  &:hover {
    background: #667eea;
    color: white;
  }
`;

const CharCount = styled.span`
  font-size: 12px;
  color: #999;
  margin-right: 10px;
`;

const InputArea: React.FC<InputAreaProps> = ({ onSendMessage, disabled }) => {
  const [message, setMessage] = useState('');
  const maxLength = 500;

  const suggestions = [
    '강남구 아파트 시세가 어떻게 되나요?',
    '대출 한도는 얼마까지 가능한가요?',
    '판교 지역 교통은 어떤가요?',
    '취득세는 얼마나 나올까요?',
  ];

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setMessage(suggestion);
  };

  return (
    <Container>
      {message.length === 0 && (
        <Suggestions>
          {suggestions.map((suggestion, index) => (
            <SuggestionChip
              key={index}
              onClick={() => handleSuggestionClick(suggestion)}
              disabled={disabled}
            >
              {suggestion}
            </SuggestionChip>
          ))}
        </Suggestions>
      )}
      
      <InputWrapper>
        <Input
          type="text"
          placeholder="부동산 관련 질문을 입력하세요..."
          value={message}
          onChange={(e) => setMessage(e.target.value.slice(0, maxLength))}
          onKeyPress={handleKeyPress}
          disabled={disabled}
        />
        
        <CharCount>
          {message.length}/{maxLength}
        </CharCount>
        
        <Button disabled={disabled}>
          📎
        </Button>
        
        <Button disabled={disabled}>
          🎤
        </Button>
        
        <Button
          primary
          onClick={handleSend}
          disabled={disabled || !message.trim()}
        >
          ➤
        </Button>
      </InputWrapper>
    </Container>
  );
};

export default InputArea;