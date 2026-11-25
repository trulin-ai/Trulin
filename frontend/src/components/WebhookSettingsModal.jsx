import React, { useState, useEffect } from 'react';
import {
  Bell,
  CheckCircle2,
  AlertTriangle,
  X,
  Plus,
  Trash2,
  RefreshCw,
  Send,
  ExternalLink,
  Shield,
  Zap,
  Activity,
  Sliders,
  DollarSign,
  Lock,
  Globe
} from 'lucide-react';

export default function WebhookSettingsModal({
  isOpen,
  onClose,
  organizationId,
  showToast
}) {
  const [webhooks, setWebhooks] = useState([]);
  const [dispatchLogs, setDispatchLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeSubTab, setActiveSubTab] = useState('channels'); // 'channels' | 'logs'
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [testingId, setTestingId] = useState(null);
  const [testResult, setTestResult] = useState(null);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    channel_type: 'slack',
    min_liability_threshold_usd: 5000,
    trigger_on_block: true,
    trigger_on_review: true,
    secret_token: ''
  });

  const orgId = organizationId || '11111111-1111-1111-1111-111111111111';

  const fetchWebhooks = async () => {
    try {
      setIsLoading(true);
      const res = await fetch(`/v1/webhooks?organization_id=${orgId}`);
      if (res.ok) {
        const data = await res.json();
        setWebhooks(data);
      }
    } catch (err) {
      console.warn('Failed to fetch webhooks:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchLogs = async () => {
    try {
      const res = await fetch(`/v1/webhooks/logs?organization_id=${orgId}&limit=25`);
      if (res.ok) {
        const data = await res.json();
        setDispatchLogs(data);
      }
    } catch (err) {
      console.warn('Failed to fetch dispatch logs:', err);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchWebhooks();
      fetchLogs();
    }
  }, [isOpen, orgId]);

  const handleCreateWebhook = async (e) => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.url.trim()) {
      showToast?.('Please provide both a label and webhook URL', 'error');
      return;
    }

    try {
      const res = await fetch('/v1/webhooks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_id: orgId,
          name: formData.name.trim(),
          url: formData.url.trim(),
          channel_type: formData.channel_type,
          min_liability_threshold_usd: Number(formData.min_liability_threshold_usd) || 0,
          trigger_on_block: formData.trigger_on_block,
          trigger_on_review: formData.trigger_on_review,
          secret_token: formData.secret_token.trim() || null
        })
      });

      if (res.ok) {
        showToast?.(`Registered ${formData.name} alert channel!`, 'success');
        setIsCreateOpen(false);
        setFormData({
          name: '',
          url: '',
          channel_type: 'slack',
          min_liability_threshold_usd: 5000,
          trigger_on_block: true,
          trigger_on_review: true,
          secret_token: ''
        });
        fetchWebhooks();
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Failed to create webhook', 'error');
      }
    } catch (err) {
      showToast?.('Network error registering webhook', 'error');
    }
  };

  const handleDeleteWebhook = async (webhookId, name) => {
    if (!window.confirm(`Delete webhook destination "${name}"?`)) return;
    try {
      const res = await fetch(`/v1/webhooks/${webhookId}`, { method: 'DELETE' });
      if (res.ok) {
        showToast?.(`Removed webhook "${name}"`, 'success');
        setWebhooks(prev => prev.filter(w => w.id !== webhookId));
      } else {
        showToast?.('Failed to delete webhook', 'error');
      }
    } catch (err) {
      showToast?.('Network error deleting webhook', 'error');
    }
  };

  const handleTestPing = async (webhookId) => {
    setTestingId(webhookId);
    setTestResult(null);
    try {
      const res = await fetch(`/v1/webhooks/${webhookId}/test`, { method: 'POST' });
      const data = await res.json();
      setTestResult({
        webhookId,
        success: data.success,
        statusCode: data.status_code,
        message: data.message
      });
      if (data.success) {
        showToast?.(`✓ Test alert delivered successfully (${data.status_code || 200})`, 'success');
      } else {
        showToast?.(`Test alert delivery failed: ${data.message}`, 'error');
      }
      fetchWebhooks();
      fetchLogs();
    } catch (err) {
      showToast?.('Failed to send test ping', 'error');
    } finally {
      setTestingId(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0, 0, 0, 0.72)',
      backdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div style={{
        background: 'var(--bg-card, #1E293B)',
        border: '1px solid var(--border-subtle, #334155)',
        borderRadius: '12px',
        width: '100%',
        maxWidth: '860px',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--border-subtle, #334155)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'linear-gradient(180deg, rgba(255,255,255,0.03) 0%, transparent 100%)'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <div style={{
                background: 'rgba(239, 68, 68, 0.15)',
                color: '#EF4444',
                padding: '6px',
                borderRadius: '8px'
              }}>
                <Bell size={18} />
              </div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main, #F8FAFC)', margin: 0 }}>
                Real-Time Incident Webhooks & Dispatch
              </h2>
              <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                NIST AI 600-1 MANAGE 2.4
              </span>
            </div>
            <p style={{ color: 'var(--text-muted, #94A3B8)', fontSize: '0.82rem', margin: 0 }}>
              Dispatch instantaneous alerts to Slack, PagerDuty, or Microsoft Teams whenever high-liability rogue agent actions are intercepted.
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted, #94A3B8)',
              cursor: 'pointer',
              padding: '4px'
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Top Summary Metric Strip */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '12px',
          padding: '16px 24px',
          background: 'var(--bg-card-subtle, #0F172A)',
          borderBottom: '1px solid var(--border-subtle, #334155)'
        }}>
          <div style={{ padding: '8px 12px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid var(--border-subtle, #334155)' }}>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted, #94A3B8)', textTransform: 'uppercase', fontWeight: 700 }}>
              Active Channels
            </div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#38BDF8', marginTop: '2px' }}>
              {webhooks.filter(w => w.is_active).length} Configured
            </div>
          </div>
          <div style={{ padding: '8px 12px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid var(--border-subtle, #334155)' }}>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted, #94A3B8)', textTransform: 'uppercase', fontWeight: 700 }}>
              Default Loss Threshold
            </div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#10B981', marginTop: '2px' }}>
              ≥ $5,000 USD
            </div>
          </div>
          <div style={{ padding: '8px 12px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid var(--border-subtle, #334155)' }}>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted, #94A3B8)', textTransform: 'uppercase', fontWeight: 700 }}>
              Dispatch Latency
            </div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#F59E0B', marginTop: '2px' }}>
              &lt; 50ms Async
            </div>
          </div>
          <div style={{ padding: '8px 12px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid var(--border-subtle, #334155)' }}>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted, #94A3B8)', textTransform: 'uppercase', fontWeight: 700 }}>
              Total Interception Dispatches
            </div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#818CF8', marginTop: '2px' }}>
              {dispatchLogs.length} Events
            </div>
          </div>
        </div>

        {/* Tab Selector */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 24px 0 24px',
          borderBottom: '1px solid var(--border-subtle, #334155)'
        }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setActiveSubTab('channels')}
              style={{
                padding: '8px 16px',
                background: 'transparent',
                border: 'none',
                borderBottom: activeSubTab === 'channels' ? '2px solid #38BDF8' : '2px solid transparent',
                color: activeSubTab === 'channels' ? '#38BDF8' : 'var(--text-muted, #94A3B8)',
                fontWeight: activeSubTab === 'channels' ? 700 : 500,
                fontSize: '0.85rem',
                cursor: 'pointer'
              }}
            >
              Alert Channels ({webhooks.length})
            </button>
            <button
              onClick={() => { setActiveSubTab('logs'); fetchLogs(); }}
              style={{
                padding: '8px 16px',
                background: 'transparent',
                border: 'none',
                borderBottom: activeSubTab === 'logs' ? '2px solid #38BDF8' : '2px solid transparent',
                color: activeSubTab === 'logs' ? '#38BDF8' : 'var(--text-muted, #94A3B8)',
                fontWeight: activeSubTab === 'logs' ? 700 : 500,
                fontSize: '0.85rem',
                cursor: 'pointer'
              }}
            >
              Delivery Audit Logs ({dispatchLogs.length})
            </button>
          </div>

          {activeSubTab === 'channels' && !isCreateOpen && (
            <button
              onClick={() => setIsCreateOpen(true)}
              className="btn btn-primary"
              style={{ padding: '6px 14px', fontSize: '0.80rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Plus size={14} />
              <span>Add Webhook Channel</span>
            </button>
          )}
        </div>

        {/* Modal Body */}
        <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1 }}>
          {activeSubTab === 'channels' ? (
            <div>
              {/* Add Webhook Form Accordion */}
              {isCreateOpen && (
                <div style={{
                  background: 'rgba(56, 189, 248, 0.04)',
                  border: '1px solid rgba(56, 189, 248, 0.25)',
                  borderRadius: '10px',
                  padding: '18px 20px',
                  marginBottom: '20px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Send size={16} color="#38BDF8" />
                      <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-main, #F8FAFC)' }}>
                        Register New Incident Destination
                      </h4>
                    </div>
                    <button
                      onClick={() => setIsCreateOpen(false)}
                      style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                    >
                      <X size={16} />
                    </button>
                  </div>

                  <form onSubmit={handleCreateWebhook}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                          CHANNEL LABEL *
                        </label>
                        <input
                          type="text"
                          required
                          value={formData.name}
                          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                          placeholder="e.g. #security-incident-alerts"
                          style={{
                            width: '100%',
                            padding: '8px 10px',
                            background: 'var(--bg-card, #1E293B)',
                            border: '1px solid var(--border-subtle, #334155)',
                            borderRadius: '6px',
                            color: 'var(--text-main, #F8FAFC)',
                            fontSize: '0.82rem'
                          }}
                        />
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                          DESTINATION TYPE *
                        </label>
                        <select
                          value={formData.channel_type}
                          onChange={(e) => setFormData({ ...formData, channel_type: e.target.value })}
                          style={{
                            width: '100%',
                            padding: '8px 10px',
                            background: 'var(--bg-card, #1E293B)',
                            border: '1px solid var(--border-subtle, #334155)',
                            borderRadius: '6px',
                            color: 'var(--text-main, #F8FAFC)',
                            fontSize: '0.82rem'
                          }}
                        >
                          <option value="slack">Slack (Incoming Webhook / Block Kit)</option>
                          <option value="pagerduty">PagerDuty (Events API v2)</option>
                          <option value="teams">Microsoft Teams (Incoming Connector)</option>
                          <option value="generic">Generic HTTPS Webhook (HMAC-SHA256)</option>
                        </select>
                      </div>
                    </div>

                    <div style={{ marginBottom: '12px' }}>
                      <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                        WEBHOOK TARGET URL *
                      </label>
                      <input
                        type="url"
                        required
                        value={formData.url}
                        onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                        placeholder={
                          formData.channel_type === 'slack'
                            ? 'https://hooks.slack.com/services/T00/B00/XXXX'
                            : formData.channel_type === 'pagerduty'
                            ? 'https://events.pagerduty.com/v2/enqueue'
                            : 'https://webhook.site/...'
                        }
                        style={{
                          width: '100%',
                          padding: '8px 10px',
                          background: 'var(--bg-card, #1E293B)',
                          border: '1px solid var(--border-subtle, #334155)',
                          borderRadius: '6px',
                          color: 'var(--text-main, #F8FAFC)',
                          fontSize: '0.82rem'
                        }}
                      />
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '14px' }}>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                          MINIMUM LOSS AVOIDANCE THRESHOLD ($ USD)
                        </label>
                        <input
                          type="number"
                          min="0"
                          step="500"
                          value={formData.min_liability_threshold_usd}
                          onChange={(e) => setFormData({ ...formData, min_liability_threshold_usd: e.target.value })}
                          style={{
                            width: '100%',
                            padding: '8px 10px',
                            background: 'var(--bg-card, #1E293B)',
                            border: '1px solid var(--border-subtle, #334155)',
                            borderRadius: '6px',
                            color: 'var(--text-main, #F8FAFC)',
                            fontSize: '0.82rem'
                          }}
                        />
                        <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '2px', display: 'block' }}>
                          Only fires when prevented liability ≥ this amount (e.g. $5,000 avoids alert fatigue).
                        </span>
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                          SECRET TOKEN / ROUTING KEY (OPTIONAL)
                        </label>
                        <input
                          type="text"
                          value={formData.secret_token}
                          onChange={(e) => setFormData({ ...formData, secret_token: e.target.value })}
                          placeholder="Routing key or HMAC signature secret"
                          style={{
                            width: '100%',
                            padding: '8px 10px',
                            background: 'var(--bg-card, #1E293B)',
                            border: '1px solid var(--border-subtle, #334155)',
                            borderRadius: '6px',
                            color: 'var(--text-main, #F8FAFC)',
                            fontSize: '0.82rem'
                          }}
                        />
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '16px' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.80rem', cursor: 'pointer', color: 'var(--text-main)' }}>
                        <input
                          type="checkbox"
                          checked={formData.trigger_on_block}
                          onChange={(e) => setFormData({ ...formData, trigger_on_block: e.target.checked })}
                        />
                        <span>Trigger on <strong>BLOCK</strong> (Critical Interceptions)</span>
                      </label>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.80rem', cursor: 'pointer', color: 'var(--text-main)' }}>
                        <input
                          type="checkbox"
                          checked={formData.trigger_on_review}
                          onChange={(e) => setFormData({ ...formData, trigger_on_review: e.target.checked })}
                        />
                        <span>Trigger on <strong>REVIEW</strong> (Escalations)</span>
                      </label>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                      <button
                        type="button"
                        onClick={() => setIsCreateOpen(false)}
                        className="btn btn-secondary"
                        style={{ padding: '6px 14px', fontSize: '0.80rem' }}
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="btn btn-primary"
                        style={{ padding: '6px 16px', fontSize: '0.80rem', fontWeight: 700 }}
                      >
                        Save & Activate Channel
                      </button>
                    </div>
                  </form>
                </div>
              )}

              {/* Channels List */}
              {isLoading ? (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 12px auto' }} />
                  <div>Loading active notification channels...</div>
                </div>
              ) : webhooks.length === 0 ? (
                <div style={{
                  textAlign: 'center',
                  padding: '48px 24px',
                  background: 'rgba(255,255,255,0.02)',
                  borderRadius: '10px',
                  border: '1px dashed var(--border-subtle)'
                }}>
                  <Bell size={36} color="var(--text-muted)" style={{ margin: '0 auto 12px auto', opacity: 0.5 }} />
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: '0 0 6px 0', color: 'var(--text-main)' }}>
                    No Webhooks Configured Yet
                  </h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', maxWidth: '420px', margin: '0 auto 16px auto' }}>
                    Connect your SecOps Slack channel, PagerDuty, or Microsoft Teams to receive instant alerts whenever the Decision Gate blocks high-liability rogue actions.
                  </p>
                  <button
                    onClick={() => setIsCreateOpen(true)}
                    className="btn btn-primary"
                    style={{ padding: '8px 18px', fontSize: '0.85rem' }}
                  >
                    + Configure Your First Webhook
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {webhooks.map((wh) => (
                    <div
                      key={wh.id}
                      style={{
                        background: 'var(--bg-card, #1E293B)',
                        border: '1px solid var(--border-subtle, #334155)',
                        borderRadius: '8px',
                        padding: '16px 18px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '16px'
                      }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                          <span style={{
                            fontSize: '0.65rem',
                            fontWeight: 700,
                            padding: '2px 6px',
                            borderRadius: '4px',
                            background:
                              wh.channel_type === 'slack' ? '#4A154B' :
                              wh.channel_type === 'pagerduty' ? '#047857' :
                              wh.channel_type === 'teams' ? '#4F46E5' : '#475569',
                            color: '#FFFFFF',
                            textTransform: 'uppercase'
                          }}>
                            {wh.channel_type}
                          </span>
                          <span style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--text-main)' }}>
                            {wh.name}
                          </span>
                          <span className="badge badge-verified" style={{ fontSize: '0.62rem' }}>
                            Active
                          </span>
                        </div>

                        <div style={{
                          fontSize: '0.74rem',
                          color: 'var(--text-muted)',
                          fontFamily: 'monospace',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          maxWidth: '480px'
                        }}>
                          {wh.url}
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                          <span>
                            Trigger: <strong>≥ ${wh.min_liability_threshold_usd?.toLocaleString() || 5000}</strong> Loss Avoided
                          </span>
                          <span>•</span>
                          <span>
                            Verdicts: {wh.trigger_on_block && 'BLOCK'}{wh.trigger_on_block && wh.trigger_on_review && ', '}{wh.trigger_on_review && 'REVIEW'}
                          </span>
                          <span>•</span>
                          {wh.last_triggered_at ? (
                            <span style={{ color: wh.last_status_code === 200 ? '#10B981' : '#F59E0B' }}>
                              Last Ping: {new Date(wh.last_triggered_at).toLocaleTimeString()} ({wh.last_status_code || 200})
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-muted)' }}>Never triggered</span>
                          )}
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <button
                          onClick={() => handleTestPing(wh.id)}
                          disabled={testingId === wh.id}
                          className="btn btn-secondary"
                          style={{
                            padding: '6px 12px',
                            fontSize: '0.75rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '5px'
                          }}
                          title="Send a sample $45,000 security exploit alert to test connectivity"
                        >
                          {testingId === wh.id ? (
                            <RefreshCw size={13} className="animate-spin" />
                          ) : (
                            <Send size={13} />
                          )}
                          <span>Test Ping</span>
                        </button>

                        <button
                          onClick={() => handleDeleteWebhook(wh.id, wh.name)}
                          style={{
                            background: 'transparent',
                            border: '1px solid rgba(239, 68, 68, 0.3)',
                            color: '#EF4444',
                            borderRadius: '6px',
                            padding: '6px 10px',
                            cursor: 'pointer'
                          }}
                          title="Remove webhook subscription"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* Delivery Audit Logs Tab */
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                  Immutable audit records of real-time alerts dispatched to external incident systems.
                </div>
                <button
                  onClick={fetchLogs}
                  className="btn btn-secondary"
                  style={{ padding: '4px 10px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  <RefreshCw size={12} />
                  <span>Refresh</span>
                </button>
              </div>

              {dispatchLogs.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  No webhook alerts have been triggered yet.
                </div>
              ) : (
                <div style={{ border: '1px solid var(--border-subtle)', borderRadius: '8px', overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                    <thead>
                      <tr style={{ background: 'var(--bg-card-subtle)', borderBottom: '1px solid var(--border-subtle)', textAlign: 'left' }}>
                        <th style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>TIMESTAMP</th>
                        <th style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>EVENT TYPE</th>
                        <th style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>AGENT ACTOR</th>
                        <th style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>VERDICT</th>
                        <th style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>PREVENTED LOSS</th>
                        <th style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>RESPONSE</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dispatchLogs.map((log) => (
                        <tr key={log.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td style={{ padding: '10px 12px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                            {new Date(log.created_at).toLocaleString()}
                          </td>
                          <td style={{ padding: '10px 12px', fontWeight: 600 }}>
                            <code>{log.event_type}</code>
                          </td>
                          <td style={{ padding: '10px 12px' }}>
                            <span className="code-pill">{log.actor_id}</span>
                          </td>
                          <td style={{ padding: '10px 12px' }}>
                            <span style={{
                              fontWeight: 700,
                              color: log.verdict === 'BLOCK' ? '#EF4444' : '#F59E0B'
                            }}>
                              {log.verdict}
                            </span>
                          </td>
                          <td style={{ padding: '10px 12px', fontWeight: 700, color: '#10B981' }}>
                            ${log.liability_prevented_usd?.toLocaleString()}
                          </td>
                          <td style={{ padding: '10px 12px' }}>
                            <span style={{
                              fontSize: '0.68rem',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background: log.response_status && log.response_status < 300 ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                              color: log.response_status && log.response_status < 300 ? '#10B981' : '#EF4444',
                              fontWeight: 700
                            }}>
                              {log.response_status ? `${log.response_status} OK` : 'Failed'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '14px 24px',
          borderTop: '1px solid var(--border-subtle, #334155)',
          background: 'var(--bg-card-subtle, #0F172A)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            🛡️ Automated outbound notifications are signed with HMAC-SHA256 and aligned with <strong>EU AI Act Article 14</strong> human-in-the-loop oversight.
          </div>
          <button
            onClick={onClose}
            className="btn btn-secondary"
            style={{ padding: '6px 16px', fontSize: '0.80rem' }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
