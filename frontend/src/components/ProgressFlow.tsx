import React from 'react';
import styled, { keyframes, css } from 'styled-components';
import { WorkflowStatus } from '../types';

interface ProgressFlowProps {
  status: WorkflowStatus;
  visible: boolean;
  style?: React.CSSProperties;
}

const Container = styled.div<{ visible: boolean }>`
  display: ${props => props.visible ? 'block' : 'none'};
  padding: 20px 15px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 12px;
  margin: 10px 0;
  margin-left: 0;
  max-width: 800px;
  width: 100%;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
`;

const StagesContainer = styled.div`
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
  margin-bottom: 15px;
  
  @media (max-width: 768px) {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }
  
  @media (max-width: 480px) {
    grid-template-columns: 1fr;
    gap: 8px;
  }
`;

const StageSection = styled.div<{ active: boolean; completed: boolean }>`
  display: flex;
  flex-direction: column;
  align-items: center;
  opacity: ${props => props.completed ? 1 : props.active ? 1 : 0.3};
  transition: all 0.5s ease;
`;

const SpinnerContainer = styled.div`
  width: 5rem;
  height: 5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  
  @media (max-width: 768px) {
    width: 4rem;
    height: 4rem;
  }
  
  @media (max-width: 480px) {
    width: 3.5rem;
    height: 3.5rem;
  }
`;

const SpinnerImage = styled.img<{ active: boolean }>`
  width: 5rem;
  height: 5rem;
  opacity: ${props => props.active ? 1 : 0.2};
  filter: ${props => !props.active ? 'grayscale(100%)' : 'none'};
  transition: all 0.3s ease;
  
  @media (max-width: 768px) {
    width: 4rem;
    height: 4rem;
  }
  
  @media (max-width: 480px) {
    width: 3.5rem;
    height: 3.5rem;
  }
`;

const pulse = keyframes`
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
`;

const StageLabel = styled.div<{ active: boolean; completed: boolean }>`
  margin-top: 10px;
  font-size: 0.875rem;
  font-weight: ${props => props.active ? 'bold' : 'normal'};
  color: ${props => 
    props.completed ? '#4CAF50' : 
    props.active ? '#667eea' : 
    '#999'};
  text-align: center;
  ${props => props.active && css`
    animation: ${pulse} 1.5s ease-in-out infinite;
  `}
  
  @media (max-width: 768px) {
    font-size: 0.75rem;
  }
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 6px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 8px;
`;

const ProgressFill = styled.div<{ progress: number }>`
  width: ${props => props.progress}%;
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s ease;
`;

const AgentsContainer = styled.div<{ visible: boolean }>`
  display: ${props => props.visible ? 'grid' : 'none'};
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 8px;
  
  @media (max-width: 480px) {
    grid-template-columns: 1fr;
    gap: 6px;
    padding: 8px;
  }
`;

const AgentCard = styled.div<{ active: boolean; completed: boolean }>`
  padding: 8px;
  border-radius: 6px;
  background: ${props => 
    props.completed ? 'linear-gradient(135deg, #4CAF50, #8BC34A)' :
    props.active ? 'linear-gradient(135deg, #FFC107, #FFD54F)' :
    'linear-gradient(135deg, #e0e0e0, #f5f5f5)'};
  color: ${props => props.completed || props.active ? 'white' : '#666'};
  text-align: center;
  font-size: 0.875rem;
  transition: all 0.3s ease;
  ${props => props.active && css`
    animation: ${pulse} 1s ease-in-out infinite;
  `}
  
  @media (max-width: 768px) {
    font-size: 0.75rem;
    padding: 6px;
  }
`;

const CompletedIcon = styled.div`
  font-size: 60px;
  text-align: center;
`;

const StatusMessage = styled.div`
  text-align: center;
  color: #666;
  font-size: 12px;
  margin-top: 8px;
  font-style: italic;
`;

const ProgressFlow: React.FC<ProgressFlowProps> = ({ status, visible, style }) => {
  const stages = [
    { 
      id: 'analyzing', 
      label: '생각중이냥!',
      gif: '/spinner/thinking_spinner.gif'
    },
    { 
      id: 'planning', 
      label: '계획중이냥!',
      gif: '/spinner/planning_spinner.gif'
    },
    { 
      id: 'executing', 
      label: '작업중이냥!',
      gif: '/spinner/excute_spnnier.gif'
    },
    { 
      id: 'completed', 
      label: '완료했냥!',
      gif: '/spinner/main_spinner.gif'
    }
  ];

  const agents = [
    { id: 'price_search', name: '시세 검색' },
    { id: 'finance', name: '금융 분석' },
    { id: 'legal', name: '법률 검토' }
  ];

  const getStageIndex = (stage: string) => {
    return stages.findIndex(s => s.id === stage);
  };

  const currentStageIndex = getStageIndex(status.stage);

  // Calculate which agent is active during execution
  const getActiveAgent = () => {
    if (status.stage !== 'executing') return -1;
    return Math.floor((status.progress / 100) * agents.length);
  };

  const activeAgentIndex = getActiveAgent();

  return (
    <Container visible={visible} style={style}>
      <StagesContainer>
        {stages.map((stage, index) => {
          const isActive = stage.id === status.stage;
          const isCompleted = index < currentStageIndex || status.stage === 'completed';
          
          return (
            <StageSection 
              key={stage.id}
              active={isActive}
              completed={isCompleted}
            >
              <SpinnerContainer>
                {stage.id === 'completed' && isCompleted ? (
                  <SpinnerImage 
                    src="/character/complete.png"
                    alt="완료"
                    active={true}
                  />
                ) : (
                  <SpinnerImage 
                    src={stage.gif}
                    alt={stage.label}
                    active={isActive}
                  />
                )}
              </SpinnerContainer>
              
              <StageLabel 
                active={isActive}
                completed={isCompleted}
              >
                {stage.label}
              </StageLabel>
              
              {isActive && stage.id !== 'completed' && (
                <ProgressBar>
                  <ProgressFill progress={status.progress} />
                </ProgressBar>
              )}
            </StageSection>
          );
        })}
      </StagesContainer>

      <AgentsContainer visible={status.stage === 'executing'}>
        {agents.map((agent, index) => (
          <AgentCard
            key={agent.id}
            active={index === activeAgentIndex}
            completed={index < activeAgentIndex}
          >
            {agent.name}
            {index < activeAgentIndex && ' ✓'}
            {index === activeAgentIndex && ' 🔄'}
          </AgentCard>
        ))}
      </AgentsContainer>

      {status.message && (
        <StatusMessage>{status.message}</StatusMessage>
      )}
    </Container>
  );
};

export default ProgressFlow;