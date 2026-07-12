import React from 'react';
import { AlertTriangle, ShieldCheck, ShieldAlert, Cpu } from 'lucide-react';
import type { MachineStatus } from '../hooks/useDashboardData';

interface MachineCardProps {
  machine: MachineStatus;
  isSelected: boolean;
  onClick: () => void;
}

export const MachineCard: React.FC<MachineCardProps> = ({ machine, isSelected, onClick }) => {
  const getStatusClass = (status: string) => {
    switch (status) {
      case 'Critical':
        return 'card-critical';
      case 'Warning':
        return 'card-warning';
      default:
        return 'card-normal';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'Critical':
        return <ShieldAlert size={18} style={{ color: 'var(--status-critical)' }} />;
      case 'Warning':
        return <AlertTriangle size={18} style={{ color: 'var(--status-warning)' }} />;
      default:
        return <ShieldCheck size={18} style={{ color: 'var(--status-normal)' }} />;
    }
  };

  return (
    <div 
      className={`bezel-outer ${getStatusClass(machine.status)} ${isSelected ? 'selected' : ''}`}
      style={{
        cursor: 'pointer',
        transform: isSelected ? 'translateY(-2px)' : undefined,
      }}
      onClick={onClick}
    >
      <div className="bezel-inner" style={{ gap: '12px', padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu size={16} style={{ color: 'var(--text-secondary)' }} />
            <h3 style={{ fontSize: '15px', fontWeight: 600 }}>{machine.machine_info.name}</h3>
          </div>
          {getStatusIcon(machine.status)}
        </div>

        <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          <div>ID: <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{machine.machine_id}</span></div>
          <div>Location: {machine.machine_info.location}</div>
          <div style={{ marginTop: '8px', fontSize: '12px' }}>
            Type: <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{machine.machine_info.type}</span>
          </div>
        </div>

        <div style={{ 
          marginTop: 'auto',
          paddingTop: '12px',
          borderTop: '1px solid var(--border-color)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline'
        }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>RUL Estimate:</span>
          <span style={{ 
            fontSize: '16px', 
            fontWeight: 700, 
            fontFamily: 'var(--font-mono)',
            color: machine.rul_days && machine.rul_days < 7 ? 'var(--status-critical)' : 'var(--text-primary)'
          }}>
            {machine.rul_days !== null ? `${machine.rul_days} Days` : 'N/A'}
          </span>
        </div>
      </div>
    </div>
  );
};
