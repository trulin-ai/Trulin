import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  CheckCircle2,
  Clock,
  ArrowRight,
  X,
  Building2,
  ShieldAlert,
  ChevronRight
} from 'lucide-react';

export default function OrganizationSetupChecklistBanner({
  activeOrg,
  onLaunchWizard,
  refreshTrigger = 0
}) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  useEffect(() => {
    if (!activeOrg?.id) return;

    // Check if dismissed in this session for this org
    const dismissedKey = `ctl_dismiss_setup_${activeOrg.id}`;
    if (sessionStorage.getItem(dismissedKey) === 'true') {
      setIsDismissed(true);
    } else {
      setIsDismissed(false);
    }

    async function fetchStatus() {
      try {
        setLoading(true);
        const res = await fetch(`/v1/organizations/${activeOrg.id}/setup-status`);
        if (res.ok) {
          const data = await res.json();
          setStatus(data);
        }
      } catch (err) {
        console.warn('Failed to load setup status:', err);
      } finally {
        setLoading(false);
      }
    }

    fetchStatus();
  }, [activeOrg?.id, refreshTrigger]);

  if (!status || isDismissed) return null;

  // Don't show if 100% completed
  if (status.setup_completed || status.completion_percentage === 100) {
    return null;
  }

  const handleDismiss = () => {
    setIsDismissed(true);
    if (activeOrg?.id) {
      sessionStorage.setItem(`ctl_dismiss_setup_${activeOrg.id}`, 'true');
    }
  };

  const pendingStep = status.steps?.find(s => !s.completed);

  return (
    <div style={{
      marginBottom: '20px',
      padding: '14px 18px',
      background: 'linear-gradient(90deg, rgba(255, 171, 74, 0.12) 0%, rgba(255, 237, 213, 0.35) 100%)',
      border: '1.5px solid rgba(255, 171, 74, 0.45)',
      borderRadius: '10px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '16px',
      flexWrap: 'wrap',
      boxShadow: '0 2px 10px rgba(255, 171, 74, 0.08)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flex: 1, minWidth: '300px' }}>
        <div style={{
          width: '38px',
          height: '38px',
          borderRadius: '8px',
          background: 'linear-gradient(135deg, #FFAB4A 0%, #EA580C 100%)',
          color: '#1A1207',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          boxShadow: '0 2px 8px rgba(255, 171, 74, 0.3)'
        }}>
          <Building2 size={18} />
        </div>

        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.88rem', fontWeight: 800, color: 'var(--text-main)' }}>
              Setup in Progress: '{status.organization_name}' ({status.completion_percentage}% Ready)
            </span>
            <span className="badge" style={{
              fontSize: '0.65rem',
              padding: '1px 6px',
              background: '#FFF3E0',
              color: '#B45309',
              border: '1px solid rgba(255, 171, 74, 0.4)'
            }}>
              {status.completed_steps_count} of {status.total_steps_count} Steps Done
            </span>
          </div>

          {/* Progress Bar */}
          <div style={{
            width: '100%',
            maxWidth: '420px',
            height: '6px',
            background: 'rgba(0, 0, 0, 0.08)',
            borderRadius: '999px',
            marginTop: '6px',
            overflow: 'hidden'
          }}>
            <div style={{
              width: `${status.completion_percentage}%`,
              height: '100%',
              background: 'linear-gradient(90deg, #FFAB4A 0%, #EA580C 100%)',
              borderRadius: '999px',
              transition: 'width 0.4s ease'
            }} />
          </div>

          {/* Pending Step Hint */}
          {pendingStep && (
            <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '5px' }}>
              Next Recommended Step: <strong>{pendingStep.title}</strong> — {pendingStep.description}
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          onClick={() => onLaunchWizard && onLaunchWizard(status.next_recommended_step)}
          className="btn btn-primary"
          style={{
            fontSize: '0.78rem',
            padding: '7px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <span>Resume Setup Wizard</span>
          <ArrowRight size={14} />
        </button>

        <button
          onClick={handleDismiss}
          title="Dismiss banner"
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '6px',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          onMouseEnter={e => e.currentTarget.style.color = 'var(--text-main)'}
          onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
        >
          <X size={16} />
        </button>
      </div>
    </div>
  );
}
