import React from 'react';
import styled from 'styled-components';
import { WorkflowStatus } from '../types';

interface ProgressBarProps {
  status: WorkflowStatus;
}

const Container = styled.div`
  width: 100%;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
`;

const Title = styled.h3`
  margin: 0 0 15px 0;
  font-size: 16px;
  font-weight: 600;
`;

const StagesContainer = styled.div`
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
`;

const Stage = styled.div<{ active: boolean; completed: boolean }>`
  flex: 1;
  text-align: center;
  padding: 10px;
  position: relative;
  
  &:not(:last-child)::after {
    content: '';
    position: absolute;
    top: 50%;
    right: -50%;
    width: 100%;
    height: 2px;
    background: ${props => props.completed ? '#4CAF50' : '#ffffff40'};
    transform: translateY(-50%);
    z-index: -1;
  }
`;

const StageIcon = styled.div<{ active: boolean; completed: boolean }>`
  width: 40px;
  height: 40px;
  margin: 0 auto 8px;
  border-radius: 50%;
  background: ${props => 
    props.completed ? '#4CAF50' : 
    props.active ? '#FFC107' : 
    '#ffffff40'};
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  transition: all 0.3s ease;
  
  ${props => props.active && `
    animation: pulse 2s infinite;
    @keyframes pulse {
      0% { transform: scale(1); }
      50% { transform: scale(1.1); }
      100% { transform: scale(1); }
    }
  `}
`;

const StageLabel = styled.div`
  font-size: 12px;
  opacity: 0.9;
`;

const ProgressBarContainer = styled.div`
  width: 100%;
  height: 8px;
  background: #ffffff30;
  border-radius: 4px;
  overflow: hidden;
`;

const ProgressFill = styled.div<{ progress: number }>`
  width: ${props => props.progress}%;
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  transition: width 0.5s ease;
  position: relative;
  
  &::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
    background: linear-gradient(
      90deg,
      transparent,
      rgba(255, 255, 255, 0.3),
      transparent
    );
    animation: shimmer 2s infinite;
  }
  
  @keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
  }
`;

const StatusMessage = styled.div`
  margin-top: 10px;
  font-size: 14px;
  opacity: 0.9;
  text-align: center;
`;

const ProgressBar: React.FC<ProgressBarProps> = ({ status }) => {
  const stages = [
    { id: 'analyzing', label: '질의 분석', icon: '🔍' },
    { id: 'planning', label: '계획 수립', icon: '📋' },
    { id: 'executing', label: '실행', icon: '⚡' },
    { id: 'completed', label: '완료', icon: '✅' },
  ];

  const getStageIndex = (stage: string) => {
    return stages.findIndex(s => s.id === stage);
  };

  const currentStageIndex = getStageIndex(status.stage);

  return (
    <Container>
      <Title>처리 진행 상황</Title>
      
      <StagesContainer>
        {stages.map((stage, index) => (
          <Stage
            key={stage.id}
            active={index === currentStageIndex}
            completed={index < currentStageIndex || status.stage === 'completed'}
          >
            <StageIcon
              active={index === currentStageIndex}
              completed={index < currentStageIndex || status.stage === 'completed'}
            >
              {stage.icon}
            </StageIcon>
            <StageLabel>{stage.label}</StageLabel>
          </Stage>
        ))}
      </StagesContainer>

      <ProgressBarContainer>
        <ProgressFill progress={status.progress} />
      </ProgressBarContainer>

      {status.message && (
        <StatusMessage>{status.message}</StatusMessage>
      )}
      
      {status.currentAgent && (
        <StatusMessage>현재 실행 중: {status.currentAgent}</StatusMessage>
      )}
    </Container>
  );
};

export default ProgressBar;