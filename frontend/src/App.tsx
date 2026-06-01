import { useState, useRef, useEffect } from 'react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
  evidence?: Evidence[]
  riskFlags?: string[]
  riskSeverity?: string
  intent?: string
  confidence?: number
}

interface Evidence {
  chunk_id: string
  doc_type: string
  title: string
  content: string
  score: number
}

interface ChatResponse {
  message: {
    role: string
    content: string
    timestamp: string
  }
  evidence: Evidence[]
  risk_flags: string[]
  risk_severity: string
  intent: string
  confidence: number
  session_id: string
}

const RISK_LABELS: Record<string, string> = {
  complaint_risk: '投诉风险',
  compensation_risk: '补偿风险',
  legal_risk: '法律风险',
  privacy_risk: '隐私风险',
  account_security_risk: '账户安全风险',
  policy_conflict: '政策冲突',
  insufficient_evidence: '证据不足',
  low_confidence: '置信度低',
}

const RISK_COLORS: Record<string, string> = {
  HIGH: '#dc2626',
  MEDIUM: '#d97706',
  LOW: '#16a34a',
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId] = useState(() => crypto.randomUUID())
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, userMessage].map(m => ({
            role: m.role,
            content: m.content,
          })),
          session_id: sessionId,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data: ChatResponse = await response.json()

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.message.content,
        timestamp: data.message.timestamp,
        evidence: data.evidence,
        riskFlags: data.risk_flags,
        riskSeverity: data.risk_severity,
        intent: data.intent,
        confidence: data.confidence,
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Chat error:', error)
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: '抱歉，处理您的请求时出现了问题。请稍后重试或联系人工客服。',
          timestamp: new Date().toISOString(),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const formatTime = (timestamp?: string) => {
    if (!timestamp) return ''
    return new Date(timestamp).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor: 'var(--background)' }}>
      {/* Sidebar - Evidence Panel */}
      <div
        style={{
          width: '320px',
          backgroundColor: 'var(--surface)',
          borderRight: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            padding: '16px',
            borderBottom: '1px solid var(--border)',
            backgroundColor: '#f1f5f9',
          }}
        >
          <h2 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text)' }}>
            📋 TicketPilot AI 客服 Copilot
          </h2>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            证据驱动的智能客服系统
          </p>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
          {messages.length > 0 && messages[messages.length - 1].role === 'assistant' && (
            <>
              {/* Intent & Confidence */}
              {messages[messages.length - 1].intent && (
                <div style={{ marginBottom: '16px' }}>
                  <h3 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
                    🎯 意图分类
                  </h3>
                  <div
                    style={{
                      padding: '12px',
                      backgroundColor: '#f0f9ff',
                      borderRadius: '8px',
                      border: '1px solid #bae6fd',
                    }}
                  >
                    <div style={{ fontSize: '14px', fontWeight: 500, color: '#0369a1' }}>
                      {messages[messages.length - 1].intent}
                    </div>
                    <div style={{ fontSize: '12px', color: '#0284c7', marginTop: '4px' }}>
                      置信度: {((messages[messages.length - 1].confidence || 0) * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>
              )}

              {/* Risk Flags */}
              {messages[messages.length - 1].riskFlags &&
                messages[messages.length - 1].riskFlags!.length > 0 && (
                  <div style={{ marginBottom: '16px' }}>
                    <h3 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
                      ⚠️ 风险标记
                    </h3>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {messages[messages.length - 1].riskFlags!.map((flag, i) => (
                        <span
                          key={i}
                          style={{
                            padding: '4px 8px',
                            borderRadius: '4px',
                            fontSize: '12px',
                            backgroundColor: `${
                              RISK_COLORS[messages[messages.length - 1].riskSeverity || 'LOW'] || '#64748b'
                            }15`,
                            color:
                              RISK_COLORS[messages[messages.length - 1].riskSeverity || 'LOW'] || '#64748b',
                            border: `1px solid ${
                              RISK_COLORS[messages[messages.length - 1].riskSeverity || 'LOW'] || '#64748b'
                            }30`,
                          }}
                        >
                          {RISK_LABELS[flag] || flag}
                        </span>
                      ))}
                    </div>
                    <div
                      style={{
                        marginTop: '8px',
                        fontSize: '12px',
                        color: RISK_COLORS[messages[messages.length - 1].riskSeverity || 'LOW'],
                        fontWeight: 500,
                      }}
                    >
                      严重程度: {messages[messages.length - 1].riskSeverity}
                    </div>
                  </div>
                )}

              {/* Evidence Panel */}
              {messages[messages.length - 1].evidence &&
                messages[messages.length - 1].evidence!.length > 0 && (
                  <div>
                    <h3 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
                      📚 证据来源
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {messages[messages.length - 1].evidence!.map((ev) => (
                        <div
                          key={ev.chunk_id}
                          style={{
                            padding: '12px',
                            backgroundColor: '#f8fafc',
                            borderRadius: '8px',
                            border: '1px solid var(--border)',
                          }}
                        >
                          <div
                            style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              marginBottom: '6px',
                            }}
                          >
                            <span
                              style={{
                                fontSize: '11px',
                                padding: '2px 6px',
                                borderRadius: '4px',
                                backgroundColor:
                                  ev.doc_type === 'FAQ'
                                    ? '#dbeafe'
                                    : ev.doc_type === 'POLICY'
                                    ? '#fef3c7'
                                    : '#dcfce7',
                                color:
                                  ev.doc_type === 'FAQ'
                                    ? '#1e40af'
                                    : ev.doc_type === 'POLICY'
                                    ? '#92400e'
                                    : '#166534',
                              }}
                            >
                              {ev.doc_type}
                            </span>
                            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                              {(ev.score * 100).toFixed(1)}%
                            </span>
                          </div>
                          {ev.title && (
                            <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text)', marginBottom: '4px' }}>
                              {ev.title}
                            </div>
                          )}
                          <div
                            style={{
                              fontSize: '12px',
                              color: 'var(--text-secondary)',
                              lineHeight: '1.4',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              display: '-webkit-box',
                              WebkitLineClamp: 3,
                              WebkitBoxOrient: 'vertical',
                            }}
                          >
                            {ev.content}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
            </>
          )}

          {messages.length === 0 && (
            <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '32px 16px' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>💬</div>
              <div style={{ fontSize: '14px', fontWeight: 500, marginBottom: '8px' }}>
                开始对话
              </div>
              <div style={{ fontSize: '12px' }}>
                输入您的客服问题，AI 将为您提供证据驱动的回复
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <div
          style={{
            padding: '12px 24px',
            borderBottom: '1px solid var(--border)',
            backgroundColor: 'var(--surface)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div>
            <h1 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text)' }}>
              智能客服对话
            </h1>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              本地演示 · 合成数据 · 人工审核
            </p>
          </div>
          <div
            style={{
              padding: '4px 12px',
              borderRadius: '16px',
              backgroundColor: '#f0fdf4',
              color: '#16a34a',
              fontSize: '12px',
              fontWeight: 500,
            }}
          >
            ✓ 系统就绪
          </div>
        </div>

        {/* Messages */}
        <div
          style={{
            flex: 1,
            overflow: 'auto',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          {messages.map((msg, index) => (
            <div
              key={index}
              className="animate-fade-in"
              style={{
                display: 'flex',
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
              }}
            >
              <div
                style={{
                  maxWidth: '70%',
                  padding: '12px 16px',
                  borderRadius: '12px',
                  backgroundColor: msg.role === 'user' ? 'var(--primary)' : 'var(--surface)',
                  color: msg.role === 'user' ? 'white' : 'var(--text)',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                  border: msg.role === 'assistant' ? '1px solid var(--border)' : 'none',
                }}
              >
                <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>{msg.content}</div>
                <div
                  style={{
                    fontSize: '11px',
                    marginTop: '6px',
                    color: msg.role === 'user' ? 'rgba(255,255,255,0.7)' : 'var(--text-secondary)',
                    textAlign: 'right',
                  }}
                >
                  {formatTime(msg.timestamp)}
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
              <div
                style={{
                  padding: '12px 16px',
                  borderRadius: '12px',
                  backgroundColor: 'var(--surface)',
                  border: '1px solid var(--border)',
                }}
              >
                <div style={{ display: 'flex', gap: '4px' }}>
                  <div
                    className="animate-pulse"
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      backgroundColor: 'var(--primary)',
                    }}
                  />
                  <div
                    className="animate-pulse"
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      backgroundColor: 'var(--primary)',
                      animationDelay: '0.2s',
                    }}
                  />
                  <div
                    className="animate-pulse"
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      backgroundColor: 'var(--primary)',
                      animationDelay: '0.4s',
                    }}
                  />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div
          style={{
            padding: '16px 24px',
            borderTop: '1px solid var(--border)',
            backgroundColor: 'var(--surface)',
          }}
        >
          <div style={{ display: 'flex', gap: '12px' }}>
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入您的客服问题..."
              style={{
                flex: 1,
                padding: '12px 16px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                resize: 'none',
                fontSize: '14px',
                lineHeight: '1.5',
                outline: 'none',
                fontFamily: 'inherit',
                minHeight: '48px',
                maxHeight: '120px',
              }}
              rows={1}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || loading}
              style={{
                padding: '12px 24px',
                borderRadius: '8px',
                backgroundColor: input.trim() && !loading ? 'var(--primary)' : '#94a3b8',
                color: 'white',
                border: 'none',
                cursor: input.trim() && !loading ? 'pointer' : 'not-allowed',
                fontWeight: 500,
                fontSize: '14px',
                transition: 'background-color 0.2s',
              }}
            >
              发送
            </button>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '8px' }}>
            按 Enter 发送 · Shift+Enter 换行 · 本地演示 · No auto-send
          </div>
        </div>
      </div>
    </div>
  )
}

export default App