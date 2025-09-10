import React from 'react';
import styled from 'styled-components';
import { SpinnerConfig } from '../types';

interface SpinnerModalProps {
  config: SpinnerConfig | null;
  agentStatuses?: Array<{
    name: string;
    progress: number;
  }>;
}

const Modal = styled.div<{ isOpen: boolean }>`
  display: ${props => props.isOpen ? 'flex' : 'none'};
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  justify-content: center;
  align-items: center;
  z-index: 1000;
`;

const ModalContent = styled.div`
  background: white;
  border-radius: 20px;
  padding: 30px;
  max-width: 500px;
  width: 90%;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
`;

const SpinnerImage = styled.img`
  width: 300px;
  height: 300px;
  object-fit: contain;
  margin-bottom: 20px;
`;

const Message = styled.h3`
  color: #333;
  margin-bottom: 20px;
  text-align: center;
  font-size: 18px;
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 10px;
  background: #e0e0e0;
  border-radius: 5px;
  overflow: hidden;
  margin-bottom: 10px;
`;

const ProgressFill = styled.div<{ progress: number }>`
  width: ${props => props.progress}%;
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  transition: width 0.3s ease;
`;

const ProgressText = styled.div`
  color: #666;
  font-size: 14px;
  margin-bottom: 20px;
`;

const AgentList = styled.div`
  width: 100%;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e0e0e0;
`;

const AgentItem = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 8px;
`;

const AgentName = styled.span`
  font-size: 14px;
  color: #555;
  font-weight: 500;
`;

const AgentProgress = styled.span`
  font-size: 12px;
  color: #888;
  font-weight: bold;
`;

const SpinnerModal: React.FC<SpinnerModalProps> = ({ config, agentStatuses }) => {
  if (!config) return null;

  const getSpinnerPath = (type: string) => {
    switch (type) {
      case 'thinking':
        return '/spinner/thinking_spinner.gif';
      case 'planning':
        return '/spinner/planning_spinner.gif';
      case 'executing':
        return '/spinner/excute_spnnier.gif';
      case 'main':
      default:
        return '/spinner/main_spinner.gif';
    }
  };

  return (
    <Modal isOpen={!!config}>
      <ModalContent>
        <SpinnerImage src={getSpinnerPath(config.type)} alt="Processing" />
        <Message>{config.message}</Message>
        
        {config.progress !== undefined && (
          <>
            <ProgressBar>
              <ProgressFill progress={config.progress} />
            </ProgressBar>
            <ProgressText>{Math.round(config.progress)}% 완료</ProgressText>
          </>
        )}

        {agentStatuses && agentStatuses.length > 0 && (
          <AgentList>
            <h4 style={{ marginBottom: '10px', color: '#333' }}>에이전트 상태</h4>
            {agentStatuses.map((agent, index) => (
              <AgentItem key={index}>
                <AgentName>{agent.name}</AgentName>
                <AgentProgress>{agent.progress}%</AgentProgress>
              </AgentItem>
            ))}
          </AgentList>
        )}
      </ModalContent>
    </Modal>
  );
};

export default SpinnerModal;