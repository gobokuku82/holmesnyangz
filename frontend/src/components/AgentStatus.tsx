import React from 'react';
import styled from 'styled-components';
import { AgentStatus as AgentStatusType } from '../types';
import { FiCheckCircle, FiClock, FiAlertCircle, FiLoader } from 'react-icons/fi';

interface AgentStatusProps {
  agents: AgentStatusType[];
}

const Container = styled.div`
  padding: 20px;
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  margin: 20px;
`;

const Title = styled.h3`
  margin: 0 0 20px 0;
  color: #333;
  font-size: 18px;
  font-weight: 600;
`;

const AgentGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
`;

const AgentCard = styled.div<{ status: string }>`
  padding: 15px;
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
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }
`;

const AgentHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
`;

const AgentName = styled.h4`
  margin: 0;
  font-size: 14px;
  font-weight: 600;
`;

const StatusIcon = styled.div<{ status: string }>`
  display: flex;
  align-items: center;
  justify-content: center;
  
  ${props => props.status === 'running' && `
    animation: spin 2s linear infinite;
    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
  `}
`;

const ProgressContainer = styled.div`
  margin-top: 10px;
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
  overflow: hidden;
`;

const ProgressFill = styled.div<{ progress: number }>`
  width: ${props => props.progress}%;
  height: 100%;
  background: rgba(255, 255, 255, 0.8);
  transition: width 0.3s ease;
`;

const ProgressText = styled.div`
  font-size: 11px;
  margin-top: 5px;
  opacity: 0.9;
`;

const StatusMessage = styled.div`
  font-size: 12px;
  margin-top: 8px;
  opacity: 0.9;
  font-style: italic;
`;

const AgentStatus: React.FC<AgentStatusProps> = ({ agents }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <>{<FiCheckCircle size={20} />}</>;
      case 'running':
        return <>{<FiLoader size={20} />}</>;
      case 'error':
        return <>{<FiAlertCircle size={20} />}</>;
      default:
        return <>{<FiClock size={20} />}</>;
    }
  };

  const getAgentDisplayName = (id: string) => {
    const nameMap: { [key: string]: string } = {
      'analyzer_agent': '질의 분석',
      'planner_agent': '계획 수립',
      'price_search_agent': '시세 검색',
      'finance_agent': '금융 분석',
      'location_agent': '입지 분석',
      'legal_agent': '법률 검토',
    };
    return nameMap[id] || id;
  };

  return (
    <Container>
      <Title>에이전트 실행 상태</Title>
      <AgentGrid>
        {agents.map((agent) => (
          <AgentCard key={agent.id} status={agent.status}>
            <AgentHeader>
              <AgentName>{getAgentDisplayName(agent.id)}</AgentName>
              <StatusIcon status={agent.status}>
                {getStatusIcon(agent.status)}
              </StatusIcon>
            </AgentHeader>
            
            {agent.status === 'running' && (
              <ProgressContainer>
                <ProgressBar>
                  <ProgressFill progress={agent.progress} />
                </ProgressBar>
                <ProgressText>{agent.progress}% 완료</ProgressText>
              </ProgressContainer>
            )}
            
            {agent.message && (
              <StatusMessage>{agent.message}</StatusMessage>
            )}
          </AgentCard>
        ))}
      </AgentGrid>
    </Container>
  );
};

export default AgentStatus;