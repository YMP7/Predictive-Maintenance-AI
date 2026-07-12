import React, { useState, useRef, useEffect, useCallback } from 'react';

interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
}

interface WorkOrder {
  order_id: string;
  machine_id: string;
  action: string;
  urgency: string;
  status: string;
  created_at: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  toolsCalled?: ToolCall[];
  workOrdersCreated?: WorkOrder[];
  llmEnabled?: boolean;
  timestamp: Date;
}

interface AgentChatProps {
  machineId?: string;
  isOpen: boolean;
  onClose: () => void;
}

function TypingIndicator() {
  return (
    <div style={{ display: 'flex', gap: '4px', alignItems: 'center', padding: '8px 0' }}>
      {[0, 1, 2].map(i => (
        <div
          key={i}
          style={{
            width: 8, height: 8, borderRadius: '50%',
            background: 'var(--text-secondary)',
            animation: 'bounce 1.2s ease-in-out infinite',
            animationDelay: `${i * 0.2}s`,
          }}
        />
      ))}
    </div>
  );
}

const HoldToConfirmButton: React.FC<{
  onConfirm: () => void;
  label: string;
  confirmLabel: string;
}> = ({ onConfirm, label, confirmLabel }) => {
  const [holding, setHolding] = useState(false);
  const [progress, setProgress] = useState(0);
  const [confirmed, setConfirmed] = useState(false);
  const timerRef = useRef<number | null>(null);
  const startRef = useRef<number>(0);

  const startHold = () => {
    if (confirmed) return;
    setHolding(true);
    setProgress(0);
    startRef.current = Date.now();
    
    const duration = 1200; // 1.2s hold required for high-stakes safety
    const interval = 20;
    
    timerRef.current = window.setInterval(() => {
      const elapsed = Date.now() - startRef.current;
      const pct = Math.min(100, (elapsed / duration) * 100);
      setProgress(pct);
      
      if (elapsed >= duration) {
        clearInterval(timerRef.current!);
        setHolding(false);
        setConfirmed(true);
        onConfirm();
      }
    }, interval);
  };

  const cancelHold = () => {
    if (confirmed) return;
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    setHolding(false);
    setProgress(0);
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  return (
    <button
      onMouseDown={startHold}
      onMouseUp={cancelHold}
      onMouseLeave={cancelHold}
      onTouchStart={startHold}
      onTouchEnd={cancelHold}
      disabled={confirmed}
      style={{
        position: 'relative',
        marginLeft: 'auto',
        background: confirmed ? 'var(--status-normal)' : 'rgba(255,255,255,0.04)',
        color: confirmed ? 'var(--bg-primary)' : 'var(--text-primary)',
        border: '1px solid var(--border-color)',
        borderRadius: 'var(--radius-sm)',
        padding: '3px 10px',
        fontSize: 10,
        fontWeight: 600,
        cursor: confirmed ? 'default' : 'pointer',
        overflow: 'hidden',
        outline: 'none',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        userSelect: 'none',
        height: '22px'
      }}
    >
      {holding && (
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: `${progress}%`,
            background: 'var(--status-warning)',
            opacity: 0.3,
            pointerEvents: 'none',
            transition: 'width 0.05s linear'
          }}
        />
      )}
      <span style={{ position: 'relative', zIndex: 1 }}>
        {confirmed ? confirmLabel : holding ? 'Holding...' : label}
      </span>
    </button>
  );
};

/** Escape HTML entities to prevent XSS before markdown substitution. */
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** Render minimal markdown (bold, italic, code, newlines) safely. */
function renderMarkdownSafe(raw: string): string {
  return escapeHtml(raw)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br/>');
}

export default function AgentChat({ machineId, isOpen, onClose }: AgentChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'agent',
      content: machineId
        ? `I'm your AI Maintenance Agent. I have live access to telemetry, alerts, and maintenance history for **${machineId}**. Ask me anything about this machine.`
        : `I'm your AI Maintenance Agent. I have live access to telemetry, alerts, and maintenance records for all machines (M001–M004). Ask me anything — I'll query the data and reason over it.`,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    if (isOpen) inputRef.current?.focus();
  }, [isOpen]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('/api/agent/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Request': 'true',
        },
        credentials: 'include',
        body: JSON.stringify({ message: text, machine_id: machineId ?? null }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const agentMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'agent',
        content: data.response,
        toolsCalled: data.tools_called ?? [],
        workOrdersCreated: data.work_orders_created ?? [],
        llmEnabled: data.llm_enabled ?? false,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, agentMsg]);
    } catch (err) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 2).toString(),
        role: 'agent',
        content: `⚠️ Failed to reach the agent: ${err instanceof Error ? err.message : 'Unknown error'}`,
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, machineId]);

  const handleApprove = async (orderId: string) => {
    try {
      const res = await fetch(`/api/work-orders/${orderId}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Request': 'true',
        },
        credentials: 'include',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      setMessages(prev => prev.map(msg => {
        if (!msg.workOrdersCreated) return msg;
        return {
          ...msg,
          workOrdersCreated: msg.workOrdersCreated.map(wo => 
            wo.order_id === orderId ? { ...wo, status: 'Open' } : wo
          )
        };
      }));
    } catch (err) {
      console.error('Failed to approve work order:', err);
      alert('Failed to approve work order. You might not have permission.');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const suggestedQuestions = machineId
    ? [`Why is ${machineId} showing an alert?`, `What's the maintenance history for ${machineId}?`, `Create a work order for ${machineId}`]
    : ['Which machine needs attention most urgently?', 'Show me recent alerts across all machines', 'What maintenance is overdue?'];

  if (!isOpen) return null;

  return (
    <>
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0.7); opacity: 0.5; }
          40% { transform: scale(1); opacity: 1; }
        }
        @keyframes fadeIn {
          from { opacity: 0; backdrop-filter: blur(0px); }
          to { opacity: 1; backdrop-filter: blur(2px); }
        }
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0.9; }
          to { transform: translateX(0); opacity: 1; }
        }
        .agent-chat-backdrop {
          animation: fadeIn 0.25s var(--ease-out) forwards;
        }
        .agent-chat-panel {
          animation: slideIn 0.35s var(--ease-drawer) forwards;
        }
        .msg-user { 
          background: var(--accent-primary); 
          color: white; 
        }
        .msg-agent { 
          background: rgba(255, 255, 255, 0.03); 
          border: 1px solid var(--border-color); 
          color: var(--text-primary); 
        }
        .tool-chip {
          display: inline-block; 
          font-size: 10px; 
          padding: 2px 8px;
          border-radius: 99px; 
          background: var(--accent-glow);
          border: 1px solid var(--border-color); 
          color: var(--accent-primary); 
          margin: 2px;
        }
        .send-btn:hover { 
          background: var(--accent-primary) !important;
          opacity: 0.9;
        }
        .send-btn:active {
          transform: scale(0.97) !important;
        }
        .send-btn:disabled { 
          opacity: 0.4; 
          cursor: not-allowed; 
        }
        .quick-q:hover { 
          background: rgba(255, 255, 255, 0.08) !important; 
          border-color: rgba(255, 255, 255, 0.16) !important; 
          transform: translateY(-1px);
        }
        .quick-q:active {
          transform: scale(0.98);
        }
        .msg-content p { 
          margin: 0 0 8px; 
        }
        .msg-content p:last-child { 
          margin: 0; 
        }
        .msg-content strong { 
          color: var(--accent-primary); 
        }
        .msg-content code {
          background: rgba(0, 0, 0, 0.25); 
          padding: 1px 5px;
          border-radius: 4px; 
          font-size: 12px; 
          color: var(--accent-primary);
        }
        .agent-chat-messages::-webkit-scrollbar {
          width: 5px;
        }
        .agent-chat-messages::-webkit-scrollbar-track {
          background: transparent;
        }
        .agent-chat-messages::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.08);
          border-radius: var(--radius-sm);
        }
        .agent-chat-messages::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.15);
        }
      `}</style>

      {/* Backdrop */}
      <div
        className="agent-chat-backdrop"
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 1000,
          background: 'rgba(0, 0, 0, 0.4)',
        }}
      />

      {/* Panel */}
      <div
        className="agent-chat-panel"
        style={{
          position: 'fixed', top: 0, right: 0, bottom: 0,
          width: '420px', zIndex: 1001,
          background: 'var(--bg-primary)',
          borderLeft: '1px solid var(--border-color)',
          display: 'flex', flexDirection: 'column',
          boxShadow: '-8px 0 40px rgba(0, 0, 0, 0.4)',
        }}
      >
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--border-color)',
          background: 'rgba(255, 255, 255, 0.01)',
          display: 'flex', alignItems: 'center', gap: 12,
        }}>
          <div style={{
            width: 40, height: 40, borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--accent-primary), #1d4ed8)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 18, boxShadow: '0 0 16px var(--accent-glow)',
          }}>🤖</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: 14 }}>AI Maintenance Agent</div>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
              {machineId ? `Focused on ${machineId}` : 'Fleet-wide analysis'} · Gemini 2.0 Flash
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-sm)', color: 'var(--text-secondary)', cursor: 'pointer',
              padding: '6px 10px', fontSize: 14,
              transition: 'transform 0.15s var(--ease-out), background-color 0.15s var(--ease-out)',
            }}
          >✕</button>
        </div>

        {/* Messages */}
        <div 
          className="agent-chat-messages"
          style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: 12 }}
        >
          {messages.map(msg => (
            <div key={msg.id} style={{ display: 'flex', flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
              <div
                className={msg.role === 'user' ? 'msg-user' : 'msg-agent'}
                style={{
                  maxWidth: '88%', padding: '10px 14px', borderRadius: msg.role === 'user' ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
                  fontSize: 13, lineHeight: 1.5,
                }}
              >
                <div
                  className="msg-content"
                  dangerouslySetInnerHTML={{ __html: renderMarkdownSafe(msg.content) }}
                />
              </div>

              {/* Tool calls disclosure */}
              {msg.toolsCalled && msg.toolsCalled.length > 0 && (
                <div style={{ marginTop: 4, maxWidth: '88%', paddingLeft: msg.role === 'user' ? 0 : '4px' }}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 3 }}>Tools used:</div>
                  {msg.toolsCalled.map((tc, i) => (
                    <span key={i} className="tool-chip">
                      🔧 {tc.tool}
                      {tc.args.machine_id ? ` (${tc.args.machine_id})` : ''}
                    </span>
                  ))}
                </div>
              )}

              {/* Work orders created */}
              {msg.workOrdersCreated && msg.workOrdersCreated.length > 0 && (
                <div style={{ marginTop: 6, maxWidth: '88%', paddingLeft: msg.role === 'user' ? 0 : '4px' }}>
                  {msg.workOrdersCreated.map(wo => (
                    <div key={wo.order_id} style={{
                      background: 'rgba(0,0,0,0.15)', border: `1px solid var(--status-${wo.urgency.toLowerCase()})33`,
                      borderRadius: 'var(--radius-sm)', padding: '8px 12px', fontSize: 12,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                        <span>📋</span>
                        <strong style={{ color: 'var(--text-primary)' }}>Work Order Created</strong>
                        <span style={{
                          fontSize: 10, padding: '1px 6px', borderRadius: 99,
                          background: `var(--status-${wo.urgency.toLowerCase()}-glow)`,
                          color: `var(--status-${wo.urgency.toLowerCase()})`,
                          border: `1px solid var(--status-${wo.urgency.toLowerCase()})22`,
                        }}>{wo.urgency}</span>
                        {wo.status === 'Pending Approval' ? (
                          <HoldToConfirmButton 
                            onConfirm={() => handleApprove(wo.order_id)} 
                            label="Hold to Approve" 
                            confirmLabel="Approved" 
                          />
                        ) : (
                          <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-secondary)' }}>
                            {wo.status}
                          </span>
                        )}
                      </div>
                      <div style={{ color: 'var(--text-secondary)' }}>{wo.machine_id}: {wo.action}</div>
                    </div>
                  ))}
                </div>
              )}

              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3, padding: '0 4px' }}>
                {msg.timestamp.toLocaleTimeString()}
              </div>
            </div>
          ))}

          {isLoading && (
            <div style={{ display: 'flex', alignItems: 'flex-start' }}>
              <div className="msg-agent" style={{ padding: '10px 14px', borderRadius: '12px 12px 12px 4px' }}>
                <TypingIndicator />
                <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 4 }}>Querying sensors and reasoning…</div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Suggested questions (shown when no user messages yet) */}
        {messages.filter(m => m.role === 'user').length === 0 && (
          <div style={{ padding: '0 16px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>Suggested:</div>
            {suggestedQuestions.map((q, i) => (
              <button
                key={i}
                className="quick-q"
                onClick={() => { setInput(q); inputRef.current?.focus(); }}
                style={{
                  background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-sm)', padding: '7px 12px', color: 'var(--text-secondary)', cursor: 'pointer',
                  textAlign: 'left', fontSize: 12, 
                  transition: 'transform 0.15s var(--ease-out), background-color 0.15s var(--ease-out), border-color 0.15s var(--ease-out)',
                }}
              >{q}</button>
            ))}
          </div>
        )}

        {/* Input */}
        <div style={{
          padding: '12px 16px 16px',
          borderTop: '1px solid var(--border-color)',
          display: 'flex', gap: 8,
        }}>
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about any machine…"
            disabled={isLoading}
            style={{
              flex: 1, background: 'rgba(255,255,255,0.03)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-sm)', padding: '10px 14px',
              color: 'var(--text-primary)', fontSize: 13, outline: 'none',
              transition: 'border-color 0.15s var(--ease-out)',
            }}
            onFocus={e => { e.target.style.borderColor = 'rgba(59, 130, 246, 0.4)'; }}
            onBlur={e => { e.target.style.borderColor = 'var(--border-color)'; }}
          />
          <button
            className="send-btn"
            onClick={sendMessage}
            disabled={isLoading || !input.trim()}
            style={{
              background: 'var(--accent-primary)', border: 'none',
              borderRadius: 'var(--radius-sm)', padding: '10px 16px',
              color: 'white', cursor: 'pointer', fontSize: 16,
              transition: 'transform 0.15s var(--ease-out), background-color 0.15s var(--ease-out)',
            }}
          >→</button>
        </div>
      </div>
    </>
  );
}
