import React, { useState, useEffect, useRef } from 'react';
import { 
  MessageSquare, Plus, MoreHorizontal, Search, Trash2, 
  CheckCircle2, Clock, ShieldCheck, Sparkles, AlertTriangle, 
  Copy, Check, ChevronDown, ChevronRight, BookOpen, Layers, Shield,
  ExternalLink, ShieldAlert, ArrowUpRight, Mic, ArrowUp, FileText, X,
  PanelLeftClose, PanelLeftOpen, Pencil, Share2, Scale, Info, Hash,
  UploadCloud, GitCompare, HelpCircle, Pin, PinOff, ClipboardCheck
} from 'lucide-react';

const PROCESS_STEPS = [
  {
    action: "Searching indexed policy claims & vector embeddings",
    tag: "Retrieval",
    icon: "🔍"
  },
  {
    action: "Evaluating freshness decay & temporal validity",
    tag: "Decay Engine",
    icon: "⏳"
  },
  {
    action: "Auditing cross-source contradictions & policy disputes",
    tag: "Zero-Trust Gate",
    icon: "🛡️"
  },
  {
    action: "Evaluating governance thresholds & synthesizing answer",
    tag: "Context Gate",
    icon: "✨"
  }
];

// Modern Transparent Single-Spot Text Morphing Process Indicator
function ChatProcessingPipeline({ activeWorkspace }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      setElapsedMs(elapsed);
      const stepIdx = Math.min(Math.floor(elapsed / 750), PROCESS_STEPS.length - 1);
      setCurrentStep(stepIdx);
    }, 100);

    return () => clearInterval(interval);
  }, []);

  const step = PROCESS_STEPS[currentStep] || PROCESS_STEPS[0];

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '8px 4px',
        margin: '4px 0',
        background: 'transparent',
        border: 'none',
        boxShadow: 'none',
        width: '100%',
        minHeight: '36px'
      }}
    >
      {/* Sleek Gradient Rotating Spinner */}
      <div className="chat-process-spinner" />

      {/* Single-Spot Morphing Text with Smooth Keyframe Transition */}
      <div
        key={currentStep}
        className="chat-process-text-active"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexWrap: 'wrap',
          color: '#1E293B',
          fontSize: '0.84rem'
        }}
      >
        <span style={{ fontSize: '0.9rem' }}>{step.icon}</span>
        <span style={{ fontWeight: 600, color: '#334155' }}>
          {step.action}
        </span>
        <span className="chat-bouncing-dots">
          <span />
          <span />
          <span />
        </span>
        {activeWorkspace && activeWorkspace.id !== 'all' && (
          <span style={{
            fontSize: '0.68rem',
            padding: '1px 6px',
            borderRadius: '10px',
            background: 'rgba(255, 171, 74, 0.15)',
            color: '#C2410C',
            fontWeight: 700
          }}>
            {activeWorkspace.name.split(' ')[0]}
          </span>
        )}
      </div>

      {/* Elapsed Counter */}
      <div style={{
        marginLeft: 'auto',
        fontSize: '0.72rem',
        color: '#94A3B8',
        fontWeight: 600,
        fontFamily: 'monospace'
      }}>
        {(elapsedMs / 1000).toFixed(1)}s
      </div>
    </div>
  );
}

// Smart Title Synthesis for Chat Sessions like ChatGPT / Claude / Copilot
export function generateSmartTitle(query) {
  if (!query || typeof query !== 'string') return 'New Conversation';

  let cleaned = query.trim();
  cleaned = cleaned.replace(/\[Attached Document:[^\]]+\]/gi, '');
  cleaned = cleaned.replace(/```[\s\S]*?```/g, '');
  cleaned = cleaned.trim();

  const prefixes = [
    /^(?:can\s+(?:you|we|i)\s+(?:please\s+)?(?:tell\s+me\s+about|explain|check|verify|give\s+me|show\s+me|help\s+me\s+with))\s+/i,
    /^(?:could\s+(?:you|we|i)\s+(?:please\s+)?(?:tell\s+me\s+about|explain|check|verify|give\s+me|show\s+me))\s+/i,
    /^(?:what\s+(?:is|are|does|do)\s+(?:the|our|your)?\s*(?:policy|rules?|guidelines?|standard|requirements?|procedure)\s+(?:for|about|on|regarding)?)\s+/i,
    /^(?:what\s+(?:is|are|does|do)\s+(?:the|our|your)?)\s+/i,
    /^(?:tell\s+me\s+(?:about|regarding))\s+/i,
    /^(?:explain\s+(?:the|our|how)?)\s+/i,
    /^(?:how\s+(?:do|can|does|should)\s+(?:we|i|a\s+user)?)\s+/i,
    /^(?:is\s+it\s+(?:allowed|permitted|possible)\s+to)\s+/i,
    /^(?:am\s+i\s+(?:allowed|permitted)\s+to)\s+/i,
    /^(?:can\s+(?:i|we|an\s+agent)\s+)\s*/i,
    /^(?:please\s+)\s*/i,
    /^(?:i\s+(?:want|need|would\s+like)\s+to\s+(?:know|check|understand)\s+(?:about)?)\s+/i,
  ];

  for (const regex of prefixes) {
    cleaned = cleaned.replace(regex, '').trim();
  }

  cleaned = cleaned.replace(/^[^\w]+/, '').replace(/[?!.,;:"']+$/, '').trim();

  if (!cleaned) {
    cleaned = query.slice(0, 35).trim();
  }

  const words = cleaned.split(/\s+/).filter(Boolean);
  const truncatedWords = words.slice(0, 6);

  const minorWords = new Set(['a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 'on', 'at', 'to', 'by', 'in', 'of']);
  const titled = truncatedWords.map((word, idx) => {
    const lower = word.toLowerCase();
    if (idx === 0 || idx === truncatedWords.length - 1 || !minorWords.has(lower)) {
      return word.charAt(0).toUpperCase() + word.slice(1);
    }
    return lower;
  }).join(' ');

  if (titled.length > 48) {
    return titled.slice(0, 45).trim() + '...';
  }
  return titled || 'New Conversation';
}

// Rich Formatted Content Renderer for Catchy & Scannable Answers with Interactive Citations
function RichAnswerContent({ content, onCitationClick, onCitationHover }) {
  if (!content) return null;

  // Split into paragraphs / lines
  const rawLines = content.split('\n');
  const elements = [];
  let currentBulletList = [];

  const flushBulletList = () => {
    if (currentBulletList.length > 0) {
      elements.push(
        <div key={`bullets-${elements.length}`} style={{ margin: '6px 0', display: 'flex', flexDirection: 'column', gap: '5px' }}>
          {currentBulletList.map((item, bIdx) => (
            <div key={bIdx} style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span style={{ color: '#78716C', fontSize: '0.85rem' }}>•</span>
              <div style={{ flex: 1, color: '#292524', fontSize: '0.95rem', lineHeight: 1.65 }}>
                {renderInlineFormatted(item)}
              </div>
            </div>
          ))}
        </div>
      );
      currentBulletList = [];
    }
  };

  const renderInlineFormatted = (text) => {
    // Parse bold text **text**, inline backticks `code`, and [Source X] references
    const parts = text.split(/(\*\*.*?\*\*|`.*?`|\[(?:Source\s*)?\d+\])/gi);
    return parts.map((part, pIdx) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        const inner = part.slice(2, -2);
        return (
          <strong key={pIdx} style={{ fontWeight: 600, color: '#1C1917' }}>
            {inner}
          </strong>
        );
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        const inner = part.slice(1, -1);
        return (
          <code key={pIdx} style={{
            background: 'rgba(0,0,0,0.05)',
            padding: '2px 5px',
            borderRadius: '4px',
            fontSize: '0.86em',
            color: '#1C1917',
            fontFamily: 'monospace'
          }}>
            {inner}
          </code>
        );
      }
      if (part.match(/^\[(?:Source\s*)?\d+\]$/i)) {
        const num = part.replace(/[^\d]/g, '');
        return (
          <button
            key={pIdx}
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              if (onCitationClick) onCitationClick(parseInt(num, 10));
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#DBEAFE';
              e.currentTarget.style.color = '#1D4ED8';
              e.currentTarget.style.borderColor = '#3B82F6';
              if (onCitationHover) onCitationHover(parseInt(num, 10));
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#EFF6FF';
              e.currentTarget.style.color = '#1D4ED8';
              e.currentTarget.style.borderColor = '#BFDBFE';
              if (onCitationHover) onCitationHover(null);
            }}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: '#EFF6FF',
              border: '1px solid #BFDBFE',
              borderRadius: '4px',
              color: '#1D4ED8',
              fontWeight: 700,
              fontSize: '0.70rem',
              padding: '1px 6px',
              margin: '0 2px',
              cursor: 'pointer',
              verticalAlign: 'baseline',
              fontFamily: 'monospace',
              transition: 'all 0.15s ease'
            }}
            title={`View Supporting Evidence for Source ${num}`}
          >
            Source {num}
          </button>
        );
      }
      return part;
    });
  };

  for (let i = 0; i < rawLines.length; i++) {
    let line = rawLines[i].trim();
    if (!line) {
      flushBulletList();
      continue;
    }

    // Strip legacy robotic template headers
    if (line.match(/^\*\*Direct Answer:\*\*\s*$/i) || line.match(/^Direct Answer:\s*$/i)) {
      continue;
    }
    if (line.match(/^(\*\*Direct Answer:\*\*|Direct Answer:)\s*(.+)$/i)) {
      line = line.replace(/^(\*\*Direct Answer:\*\*|Direct Answer:)\s*/i, '');
    }
    if (line.includes('🔒 Provenance:') || line.includes('🔒 **Provenance:**')) {
      continue;
    }
    if (line.startsWith('📌 Policy Boundary Notice:') || line.startsWith('📌 **Policy Boundary Notice:**')) {
      flushBulletList();
      const cleanNote = line.replace(/^📌\s*(\*\*Policy Boundary Notice:\*\*|Policy Boundary Notice:)\s*/i, '');
      elements.push(
        <div key={`boundary-${i}`} style={{
          margin: '10px 0',
          padding: '8px 12px',
          background: 'rgba(0,0,0,0.02)',
          borderLeft: '3px solid #D97706',
          borderRadius: '0 6px 6px 0',
          fontSize: '0.88rem',
          lineHeight: 1.55,
          color: '#57534E'
        }}>
          <strong style={{ color: '#92400E', fontWeight: 600 }}>Policy boundary: </strong>
          {renderInlineFormatted(cleanNote)}
        </div>
      );
      continue;
    }
    if (line.startsWith('👉 Recommended Next Step:') || line.startsWith('👉 **Recommended Next Step:**')) {
      flushBulletList();
      const cleanStep = line.replace(/^👉\s*(\*\*Recommended Next Step:\*\*|Recommended Next Step:)\s*/i, '');
      elements.push(
        <p key={`step-${i}`} style={{ margin: '8px 0', lineHeight: 1.65, fontSize: '0.95rem', color: '#292524' }}>
          <strong style={{ color: '#1C1917' }}>Recommended next step: </strong>
          {renderInlineFormatted(cleanStep)}
        </p>
      );
      continue;
    }

    // Handle blockquotes: `> ` including `> [!NOTE]`
    if (line.startsWith('>')) {
      const blockquoteLines = [];
      while (i < rawLines.length && rawLines[i].trim().startsWith('>')) {
        const bLine = rawLines[i].trim().replace(/^>\s*/, '');
        blockquoteLines.push(bLine);
        i++;
      }
      i--; // adjust loop counter
      const isNote = blockquoteLines.some(l => l.includes('[!NOTE]') || l.includes('Section Context'));
      elements.push(
        <div key={`callout-${i}`} style={{
          margin: '10px 0',
          padding: '10px 14px',
          background: isNote ? '#F8FAFC' : '#F5F5F4',
          borderLeft: isNote ? '3px solid #3B82F6' : '3px solid #78716C',
          borderRadius: '0 8px 8px 0',
          fontSize: '0.86rem',
          lineHeight: 1.55,
          color: '#475569'
        }}>
          {isNote && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px', fontWeight: 600, color: '#1E40AF', fontSize: '0.78rem' }}>
              <span>📖 Explanatory Context (Non-Normative)</span>
            </div>
          )}
          {blockquoteLines.map((bl, blIdx) => {
            if (bl.startsWith('[!NOTE]')) return null;
            return <div key={blIdx} style={{ fontStyle: bl.startsWith('"') ? 'italic' : 'normal', marginTop: blIdx > 0 ? '3px' : 0 }}>{renderInlineFormatted(bl)}</div>;
          })}
        </div>
      );
      continue;
    }

    // Handle Verification Status Footer
    if (line.startsWith('🔒 **Verification Status:**') || line.startsWith('🔒 Verification Status:')) {
      flushBulletList();
      elements.push(
        <div key={`verif-bar-${i}`} style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginTop: '14px',
          padding: '6px 10px',
          borderRadius: '6px',
          background: 'rgba(0, 0, 0, 0.03)',
          border: '1px solid rgba(0, 0, 0, 0.06)',
          fontSize: '0.74rem',
          color: '#57534E',
          fontWeight: 500
        }}>
          <Shield size={12} color="#059669" />
          <div>{renderInlineFormatted(line.replace(/^🔒\s*/, ''))}</div>
        </div>
      );
      continue;
    }

    // Check for bullet items: `- `, `* `, `• `, `1. `
    const bulletMatch = line.match(/^([-*•]|\d+\.)\s+(.+)$/);
    if (bulletMatch) {
      currentBulletList.push(bulletMatch[2]);
      continue;
    }

    flushBulletList();

    // Clean Markdown Headers `### `, `## ` or standalone `**Heading:**`
    if (line.startsWith('### ') || line.startsWith('## ')) {
      const headerText = line.replace(/^#+\s*/, '');
      const isBottomLine = headerText.toLowerCase().includes('bottom-line');
      const isCond = headerText.toLowerCase().includes('conditions');
      const isClaims = headerText.toLowerCase().includes('verified operative') || headerText.toLowerCase().includes('verified claims');
      const isPathways = headerText.toLowerCase().includes('policy pathways') || headerText.toLowerCase().includes('conflict audit');
      const isContext = headerText.toLowerCase().includes('supporting context');

      elements.push(
        <div key={`header-${i}`} style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          margin: isBottomLine ? '6px 0 6px 0' : '14px 0 6px 0',
          fontSize: '0.84rem',
          fontWeight: 700,
          color: isBottomLine ? '#0F766E' : isCond ? '#B45309' : isPathways ? '#B91C1C' : isContext ? '#2563EB' : '#1C1917',
          textTransform: 'uppercase',
          letterSpacing: '0.04em'
        }}>
          {isBottomLine && <ShieldCheck size={14} color="#0F766E" />}
          {isPathways && <AlertTriangle size={14} color="#B91C1C" />}
          <span>{renderInlineFormatted(headerText)}</span>
        </div>
      );
      continue;
    }

    if (line.startsWith('**') && line.endsWith('**') && !line.includes('\n')) {
      const headerText = line.slice(2, -2);
      elements.push(
        <h4 key={`header-bold-${i}`} style={{
          fontSize: '0.96rem',
          fontWeight: 600,
          color: '#1C1917',
          margin: '14px 0 6px 0'
        }}>
          {headerText}
        </h4>
      );
      continue;
    }

    // Regular paragraph
    elements.push(
      <p key={`p-${i}`} style={{ margin: '8px 0', lineHeight: 1.65, fontSize: '0.95rem', color: '#292524' }}>
        {renderInlineFormatted(line)}
      </p>
    );
  }

  flushBulletList();
  return <div style={{ display: 'flex', flexDirection: 'column' }}>{elements}</div>;
}


// Microsoft Copilot-style Signature Gradient Ribbon Emblem
function CopilotEmblem({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ flexShrink: 0 }}>
      <defs>
        <linearGradient id="cp-ribbon-left" x1="0" y1="20" x2="16" y2="4" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#00C7FF" />
          <stop offset="30%" stopColor="#2563EB" />
          <stop offset="65%" stopColor="#7C3AED" />
          <stop offset="100%" stopColor="#D946EF" />
        </linearGradient>
        <linearGradient id="cp-ribbon-right" x1="24" y1="4" x2="8" y2="20" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#FF6B4A" />
          <stop offset="35%" stopColor="#FFA629" />
          <stop offset="70%" stopColor="#F43F5E" />
          <stop offset="100%" stopColor="#8B5CF6" />
        </linearGradient>
      </defs>
      {/* Ribbon Loop Left */}
      <path
        d="M4.8 15.6C3.5 14.1 3.2 11.8 4.1 9.7C5 7.6 7 6.3 9.3 6.4C11.4 6.5 13.1 7.8 14 9.7C14.5 10.7 14.6 11.8 14.4 12.9L4.8 15.6Z"
        fill="url(#cp-ribbon-left)"
      />
      {/* Ribbon Loop Right */}
      <path
        d="M19.2 8.4C20.5 9.9 20.8 12.2 19.9 14.3C19 16.4 17 17.7 14.7 17.6C12.6 17.5 10.9 16.2 10 14.3C9.5 13.3 9.4 12.2 9.6 11.1L19.2 8.4Z"
        fill="url(#cp-ribbon-right)"
        opacity="0.95"
      />
      <circle cx="12" cy="12" r="2.2" fill="#FFFFFF" opacity="0.35" />
    </svg>
  );
}

const COPILOT_MODES = [
  { id: 'quick', label: 'Quick response', icon: '⚡', desc: 'Direct bottom-line answer with synthesized takeaways' },
  { id: 'policy', label: 'Policy Governance', icon: '🛡️', desc: 'Deep contextual audit with freshness decay & verified citations' },
  { id: 'decision', label: 'Action Gatekeeper', icon: '⚖️', desc: 'Evaluates policy thresholds and ALLOW / BLOCK gates' },
  { id: 'audit', label: 'Contradiction Audit', icon: '⚠️', desc: 'Scans cross-source policy conflicts and disputed claims' }
];

const COPILOT_PILLS_BY_WORKSPACE = {
  all: [
    { label: "Enterprise refund window", query: "What is our company refund window for enterprise annual contracts?" },
    { label: "Remote work Wi-Fi security", query: "Can remote employees work from public Wi-Fi without VPN?" },
    { label: "Production ingress authority", query: "Who is authorized to approve production ingress firewall exceptions?" },
    { label: "Disputed policies review", query: "Are there any conflicting refund rules between Slack and Confluence?" },
    { label: "Approve $75 refund exception", query: "Can I approve a $75 refund exception for an enterprise customer?" },
    { label: "Emergency Sev-1 bypass", query: "Can emergency hotfixes bypass automated compliance verification during Sev-1 incidents?" },
    { label: "Data retention & SLA", query: "What are our data retention guidelines and customer deletion SLAs?" },
    { label: "Customer contract overrides", query: "How are custom contract terms and SLA overrides handled versus standard policies?" }
  ],
  finance: [
    { label: "Enterprise refund window", query: "What is our company refund window for enterprise annual contracts?" },
    { label: "Invoice dispute arbitration", query: "What are the financial approval thresholds and dispute arbitration rules for billing?" },
    { label: "Mid-cycle proration rules", query: "How is billing proration calculated when enterprise accounts change contract tiers?" },
    { label: "Billing vs Slack conflict", query: "Are there any conflicting refund statements in sales channels versus the billing handbook?" },
    { label: "Approve $75 refund exception", query: "Can I approve a $75 refund exception for a customer without manager sign-off?" },
    { label: "Annual contract renewals", query: "What are the early termination fees and renewal notification windows for enterprise accounts?" },
    { label: "Payment gateway failover", query: "What is our financial policy for fallback payment processing during gateway outages?" },
    { label: "Travel meal expense limit", query: "What is the maximum single meal reimbursement permitted under corporate travel policy?" }
  ],
  secops: [
    { label: "Production ingress firewall", query: "Who is authorized to approve production ingress firewall exceptions?" },
    { label: "Zero-trust token expiry", query: "What is the mandatory session timeout and mTLS certificate renewal rule for core services?" },
    { label: "Emergency Sev-1 bypass", query: "Can emergency hotfixes bypass automated compliance verification during Sev-1 incidents?" },
    { label: "KMS key rotation policy", query: "What are the cryptographic key rotation intervals enforced by our SecOps baseline?" },
    { label: "Port 22 SSH exceptions", query: "Can a senior DevOps engineer open public port 22 access without SecOps approval?" },
    { label: "Incident escalation matrix", query: "When does an unconfirmed security intrusion trigger an executive bridge call?" },
    { label: "VPN Public Wi-Fi mandate", query: "Are remote employees permitted to connect to corporate GitHub from hotel Wi-Fi without VPN?" },
    { label: "Critical CVE patching SLA", query: "What is the mandated remediation SLA for critical CVEs in production containers?" }
  ],
  hr: [
    { label: "Remote work Wi-Fi security", query: "Can remote employees work from public Wi-Fi without VPN?" },
    { label: "International leave policy", query: "What are the mandatory leave guidelines and annual holiday allowances for remote team members?" },
    { label: "Home office stipend", query: "What is the reimbursement policy and expense allowance for home workstation equipment?" },
    { label: "Contractor compliance checks", query: "Are background checks and security sign-offs mandatory for external contractors?" },
    { label: "Equipment return window", query: "What is the policy window for departing staff to return enterprise laptops and tokens?" },
    { label: "Paid parental leave", query: "What is the paid parental leave allowance for primary and secondary caregivers?" },
    { label: "Travel meal allowance", query: "What is the maximum reimbursement for international business travel meals?" },
    { label: "Conflict resolution steps", query: "What is the formal grievance procedure for workplace disputes?" }
  ],
  support: [
    { label: "Enterprise SLA targets", query: "What is the guaranteed response time SLA for Tier-0 critical client incidents?" },
    { label: "Customer escalation hierarchy", query: "When does an unresolved customer ticket get escalated to Engineering and Executive leadership?" },
    { label: "Goodwill credit limits", query: "What is the maximum billing credit a frontline support lead can grant directly?" },
    { label: "SSO login incident playbook", query: "What is the standard procedure when a customer tenant experiences SAML SSO auth failure?" },
    { label: "Approve $75 refund exception", query: "Can Tier-1 support approve a $75 refund without escalation?" },
    { label: "Maintenance downtime notice", query: "How many hours in advance must customer tenants be notified of scheduled maintenance?" },
    { label: "Severity 1 SLA breach", query: "What financial penalties or service credits apply when Tier-0 uptime SLAs are missed?" },
    { label: "Feature request routing", query: "How are enterprise client product requests prioritized and tracked in Jira?" }
  ],
  staging: [
    { label: "Sandbox test claims", query: "What sandbox policy claims are currently staged for upcoming policy release?" },
    { label: "Mock ingestion rules", query: "How are synthetic ingestion events validated against staging confidence gates?" },
    { label: "Staging rollback matrix", query: "What are the staging rollback criteria when policy confidence drops below 80%?" },
    { label: "Synthetic dispute verification", query: "How do synthetic disputes trigger automated zero-trust gate alerts?" }
  ]
};

const STARTER_PROMPTS_BY_WORKSPACE = COPILOT_PILLS_BY_WORKSPACE;

// Helper Subcomponents for Progressive-Disclosure Response UI
function ModalityPill({ modality = 'MUST' }) {
  const mod = (modality || 'MUST').toUpperCase();
  let bg = '#EFF6FF';
  let color = '#1D4ED8';
  let border = 'rgba(29, 78, 216, 0.2)';

  if (mod === 'SHOULD') {
    bg = '#FEF3C7';
    color = '#92400E';
    border = 'rgba(146, 64, 14, 0.2)';
  } else if (mod === 'MAY') {
    bg = '#ECFDF5';
    color = '#047857';
    border = 'rgba(4, 120, 87, 0.2)';
  } else if (mod === 'CANNOT' || mod === 'MUST NOT' || mod === 'PROHIBITED') {
    bg = '#FEF2F2';
    color = '#991B1B';
    border = 'rgba(153, 27, 27, 0.2)';
  }

  return (
    <span style={{
      fontSize: '0.66rem',
      fontWeight: 700,
      padding: '1px 6px',
      borderRadius: '4px',
      background: bg,
      color: color,
      border: `1px solid ${border}`,
      fontFamily: 'monospace',
      letterSpacing: '0.02em',
      display: 'inline-flex',
      alignItems: 'center'
    }}>
      {mod}
    </span>
  );
}

function AccordionSection({ title, count, defaultOpen = false, icon: Icon, children }) {
  return (
    <details
      open={defaultOpen}
      style={{
        marginTop: '8px',
        background: '#FAFAFA',
        border: '1px solid #E5E5E5',
        borderRadius: '8px',
        overflow: 'hidden',
        fontSize: '0.78rem'
      }}
    >
      <summary
        style={{
          cursor: 'pointer',
          padding: '8px 12px',
          fontWeight: 600,
          color: '#3F3F46',
          userSelect: 'none',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          listStyle: 'none',
          outline: 'none',
          background: '#F9FAFB'
        }}
      >
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
          {Icon && <Icon size={13} color="#71717A" />}
          <span>{title}</span>
          {typeof count === 'number' && (
            <span style={{
              fontSize: '0.68rem',
              fontWeight: 700,
              padding: '1px 6px',
              borderRadius: '10px',
              background: '#E4E4E7',
              color: '#52525B'
            }}>
              {count}
            </span>
          )}
        </span>
      </summary>
      <div style={{ padding: '10px 12px', borderTop: '1px solid #E5E5E5', background: '#FFFFFF' }}>
        {children}
      </div>
    </details>
  );
}

function extractCleanBottomLine(msg, structured) {
  if (structured?.bottom_line_answer) {
    return structured.bottom_line_answer;
  }
  if (!msg || !msg.content) return '';

  const content = msg.content;
  // If markdown has "### 🛡️ Bottom-Line Answer\n..."
  const match = content.match(/###\s*[^\n]*Bottom-Line Answer\s*\n([\s\S]*?)(?=\n###|\n🔒|$)/i);
  if (match) {
    return match[1].trim();
  }
  return content;
}


// Canonical Document Explorer Deep Link Builder with Graceful Fallback
export function buildExplorerUrl(citation, activeWorkspace) {
  const params = new URLSearchParams();
  const wsId = citation?.workspace_id || (activeWorkspace?.id && activeWorkspace.id !== 'all' ? activeWorkspace.id : null);
  if (wsId) params.set('workspace', wsId);
  if (citation?.document_id) params.set('doc', citation.document_id);
  if (citation?.claim_id) params.set('claimId', citation.claim_id);
  if (citation?.page) params.set('page', citation.page);
  params.set('view', 'folders');
  return `/documents?${params.toString()}`;
}

// Why This Answer Modal: Primary Trust & Governance Lineage Inspector
function WhyThisAnswerModal({ data, onClose, activeWorkspace }) {
  if (!data) return null;
  const { citation, claim, structured, meta } = data;

  const subject = claim?.subject || citation?.subject || 'Enterprise Policy';
  const predicate = claim?.predicate || citation?.predicate || 'governs';
  const object = claim?.object || citation?.object || 'operative requirement';
  const modality = (claim?.modality || citation?.modality || 'MUST').toUpperCase();
  const verbatimQuote = citation?.verbatim_evidence || citation?.evidence_span || claim?.verbatim_evidence || claim?.claim_text || '';
  const docTitle = citation?.source_title || citation?.document_title || claim?.document_title || 'Enterprise Policy Document';
  const section = citation?.section || claim?.section || null;
  const page = citation?.page || claim?.page || null;
  const conditions = structured?.conditions || [];
  const exceptions = structured?.exceptions || [];
  const auditId = meta?.audit_id || 'AUD-GOV-POLICY';
  const groundingScore = structured?.grounding_score ?? meta?.verification?.grounding_score ?? 1.0;

  const explorerUrl = buildExplorerUrl(citation || claim, activeWorkspace);

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(3px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          background: '#FFFFFF',
          borderRadius: '12px',
          width: '100%',
          maxWidth: '680px',
          maxHeight: '88vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 40px -10px rgba(15, 23, 42, 0.25)',
          border: '1px solid #E2E8F0',
          overflow: 'hidden'
        }}
      >
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid #E2E8F0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: '#F8FAFC'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: '#EFF6FF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid #BFDBFE'
            }}>
              <ShieldCheck size={18} color="#2563EB" />
            </div>
            <div>
              <div style={{ fontSize: '0.96rem', fontWeight: 700, color: '#0F172A' }}>
                Why This Answer? — Policy Lineage Inspector
              </div>
              <div style={{ fontSize: '0.74rem', color: '#64748B' }}>
                Certified grounded rule entailment and cryptographic audit trail
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', padding: '4px' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div style={{ padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Card 1: Certified Atomic Claim */}
          <div style={{
            background: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderRadius: '8px',
            padding: '14px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.74rem', fontWeight: 700, textTransform: 'uppercase', color: '#475569', letterSpacing: '0.04em' }}>
                Certified Atomic Claim (S-P-O Triple)
              </span>
              <ModalityPill modality={modality} />
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              flexWrap: 'wrap',
              fontSize: '0.84rem',
              fontWeight: 600,
              padding: '8px 10px',
              background: '#FFFFFF',
              borderRadius: '6px',
              border: '1px solid #E2E8F0'
            }}>
              <span style={{ color: '#0369A1', background: '#F0F9FF', padding: '2px 8px', borderRadius: '4px' }}>
                {subject}
              </span>
              <span style={{ color: '#94A3B8' }}>→</span>
              <span style={{ color: '#7C3AED', background: '#FAF5FF', padding: '2px 8px', borderRadius: '4px' }}>
                {predicate}
              </span>
              <span style={{ color: '#94A3B8' }}>→</span>
              <span style={{ color: '#059669', background: '#ECFDF5', padding: '2px 8px', borderRadius: '4px' }}>
                {object}
              </span>
            </div>
          </div>

          {/* Card 2: Supporting Verbatim Evidence */}
          <div style={{
            background: '#FFFFFF',
            border: '1px solid #E2E8F0',
            borderRadius: '8px',
            padding: '14px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.74rem', fontWeight: 700, textTransform: 'uppercase', color: '#475569', letterSpacing: '0.04em' }}>
                Supporting Verbatim Quote
              </span>
              <span style={{ fontSize: '0.74rem', color: '#64748B', fontWeight: 600 }}>
                {docTitle}{section ? ` · §${section}` : ''}{page ? ` · Page ${page}` : ''}
              </span>
            </div>
            <div style={{
              borderLeft: '3px solid #3B82F6',
              background: '#F8FAFC',
              padding: '10px 14px',
              borderRadius: '0 6px 6px 0',
              fontSize: '0.86rem',
              lineHeight: 1.6,
              color: '#334155',
              fontStyle: 'italic'
            }}>
              “{verbatimQuote || 'Direct supporting evidence verified in policy document.'}”
            </div>
          </div>

          {/* Card 3: Conditions Preserved */}
          <div style={{
            background: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderRadius: '8px',
            padding: '14px'
          }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 700, textTransform: 'uppercase', color: '#475569', letterSpacing: '0.04em', display: 'block', marginBottom: '8px' }}>
              Preserved Conditions & Exceptions
            </span>
            {(conditions.length > 0 || exceptions.length > 0) ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {conditions.map((c, ci) => (
                  <div key={`cond-${ci}`} style={{ fontSize: '0.80rem', color: '#334155', display: 'flex', gap: '6px' }}>
                    <span style={{ color: '#0284C7', fontWeight: 700 }}>• Condition:</span>
                    <span>{c}</span>
                  </div>
                ))}
                {exceptions.map((e, ei) => (
                  <div key={`exc-${ei}`} style={{ fontSize: '0.80rem', color: '#334155', display: 'flex', gap: '6px' }}>
                    <span style={{ color: '#D97706', fontWeight: 700 }}>• Exception:</span>
                    <span>{e}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: '0.80rem', color: '#64748B', fontStyle: 'italic' }}>
                Operative rule applies unconditionally across designated enterprise scope.
              </div>
            )}
          </div>

          {/* Card 4: Multi-Gate Verification Checklist */}
          <div style={{
            background: '#FFFFFF',
            border: '1px solid #E2E8F0',
            borderRadius: '8px',
            padding: '14px'
          }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 700, textTransform: 'uppercase', color: '#475569', letterSpacing: '0.04em', display: 'block', marginBottom: '10px' }}>
              Multi-Gate Verification Checklist
            </span>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.78rem', color: '#334155' }}>
                <CheckCircle2 size={14} color="#16A34A" />
                <span><strong>Grounding Status:</strong> Grounded in Verified Claims ({(groundingScore * 100).toFixed(0)}% Entailment)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.78rem', color: '#334155' }}>
                <CheckCircle2 size={14} color={meta?.has_conflicts || structured?.conflict_analysis?.is_conflicted ? "#D97706" : "#16A34A"} />
                <span><strong>Conflict Gate:</strong> {meta?.has_conflicts || structured?.conflict_analysis?.is_conflicted ? "Disputed: Conflict pathways detected" : "No conflicts detected in evaluated scope"}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.78rem', color: '#334155' }}>
                <CheckCircle2 size={14} color="#16A34A" />
                <span><strong>Temporal Validity:</strong> {citation?.validity ? `Verified Active (${citation.validity})` : (structured?.answer_scope?.temporal_validity ? `Validity: ${structured.answer_scope.temporal_validity}` : 'Validity: Not established in metadata')}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.78rem', color: '#334155' }}>
                <CheckCircle2 size={14} color="#16A34A" />
                <span><strong>Certification Tier:</strong> {citation?.certification_tier || claim?.certification_tier || 'AUTOMATED_CERTIFIED'}</span>
              </div>
            </div>
          </div>

          {/* Card 5: Cryptographic Provenance Receipt */}
          <div style={{
            background: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderRadius: '8px',
            padding: '12px 14px',
            fontSize: '0.74rem',
            color: '#64748B',
            display: 'flex',
            flexDirection: 'column',
            gap: '5px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Audit ID:</span>
              <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#334155' }}>{auditId}</span>
            </div>
            {citation?.document_id && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Document ID:</span>
                <span style={{ fontFamily: 'monospace', color: '#334155' }}>{citation.document_id}</span>
              </div>
            )}
            {citation?.claim_id && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Claim ID:</span>
                <span style={{ fontFamily: 'monospace', color: '#334155' }}>{citation.claim_id}</span>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div style={{
          padding: '12px 20px',
          borderTop: '1px solid #E2E8F0',
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: 'center',
          gap: '10px',
          background: '#F8FAFC'
        }}>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '6px 14px',
              fontSize: '0.78rem',
              fontWeight: 600,
              borderRadius: '6px',
              background: '#FFFFFF',
              border: '1px solid #CBD5E1',
              color: '#475569',
              cursor: 'pointer'
            }}
          >
            Close
          </button>
          <button
            type="button"
            onClick={() => {
              window.open(explorerUrl, '_blank', 'noopener,noreferrer');
            }}
            style={{
              padding: '6px 14px',
              fontSize: '0.78rem',
              fontWeight: 600,
              borderRadius: '6px',
              background: '#2563EB',
              border: 'none',
              color: '#FFFFFF',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 1px 2px rgba(37,99,235,0.2)'
            }}
          >
            <span>Open in Document Explorer</span>
            <ExternalLink size={13} color="#FFFFFF" />
          </button>
        </div>
      </div>
    </div>
  );
}

// Controlled Pilot Evaluation Review Modal
function PilotReviewModal({ data, onClose, onFeedbackSubmitted, showToast }) {
  if (!data) return null;
  const { message, sessionId } = data;
  const meta = message?.metadata_json || {};
  const plan = meta?.response_plan || {};
  const wording = meta?.wording_outcome || {};
  const featureFlags = meta?.feature_flags || {};

  const [verdict, setVerdict] = useState('PASS');
  const [issueCategory, setIssueCategory] = useState('DEPTH_QUALITY');
  const [checklist, setChecklist] = useState({
    scope_identified: true,
    answers_inquiry: true,
    grounded_evidence: true,
    conditions_surfaced: true,
    conflicts_flagged: true,
    depth_appropriate: true,
    navigation_works: true,
    tone_and_safety: true,
  });
  const [reviewerName, setReviewerName] = useState(() => {
    try {
      return localStorage.getItem('trulin_pilot_reviewer_name') || 'Policy Reviewer';
    } catch {
      return 'Policy Reviewer';
    }
  });
  const [reviewerRole, setReviewerRole] = useState(() => {
    try {
      return localStorage.getItem('trulin_pilot_reviewer_role') || 'Legal & Policy QA';
    } catch {
      return 'Legal & Policy QA';
    }
  });
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const toggleChecklistItem = (key) => {
    setChecklist(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const checklistItems = [
    { key: 'scope_identified', label: '1. Scope Identified', desc: 'Governing document, version, role, and business scope are explicitly established.' },
    { key: 'answers_inquiry', label: '2. Answers Inquiry', desc: 'Directly answers the user question without deflection or generic evasion.' },
    { key: 'grounded_evidence', label: '3. Grounded Evidence', desc: 'Supported strictly by cited operative clauses; no phantom citations or unverified assertions.' },
    { key: 'conditions_surfaced', label: '4. Conditions & Exceptions', desc: 'Key prerequisites, notice periods, thresholds, and carve-outs are clearly surfaced.' },
    { key: 'conflicts_flagged', label: '5. Conflict Separation', desc: 'Contradictory or divergent rules are surfaced as separate pathways rather than blended.' },
    { key: 'depth_appropriate', label: '6. Depth Quality', desc: 'Explanation volume and detail match user expectation (Brief vs Standard vs Detailed).' },
    { key: 'navigation_works', label: '7. Explorer Navigation', desc: 'Deep-link citations open Document Explorer to the exact source and claim.' },
    { key: 'tone_and_safety', label: '8. Safety & Advisory Tone', desc: 'Advisory boundaries are respected; no unverified actions or phantom authority authorized.' },
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      localStorage.setItem('trulin_pilot_reviewer_name', reviewerName);
      localStorage.setItem('trulin_pilot_reviewer_role', reviewerRole);

      const payload = {
        message_id: message.id,
        session_id: sessionId,
        reviewer_name: reviewerName || 'Reviewer',
        reviewer_role: reviewerRole || 'Legal & Policy QA',
        verdict: verdict,
        issue_category: verdict !== 'PASS' ? issueCategory : null,
        checklist: checklist,
        notes: notes || null,
        latency_ms: meta?.latency_ms ?? null,
        feature_flags: featureFlags,
        wording_outcome: wording,
        question_type: plan?.question_type ?? null,
        depth: plan?.resolved_depth ?? null,
      };

      const res = await fetch(`/v1/chat/sessions/${sessionId}/messages/${message.id}/pilot-feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        if (showToast) showToast(`Pilot review submitted: ${verdict}`);
        if (onFeedbackSubmitted) onFeedbackSubmitted(message.id, payload);
        onClose();
      } else {
        const err = await res.json().catch(() => ({}));
        if (showToast) showToast(`Failed to submit review: ${err.detail || 'Server error'}`);
      }
    } catch (err) {
      console.error('Pilot review submission error', err);
      if (showToast) showToast('Network error submitting review');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(3px)',
        zIndex: 10000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px'
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          background: '#FFFFFF',
          borderRadius: '12px',
          width: '100%',
          maxWidth: '740px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 25px 50px -12px rgba(15, 23, 42, 0.35)',
          border: '1px solid #E2E8F0',
          overflow: 'hidden'
        }}
      >
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid #E2E8F0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: '#F8FAFC'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: '#EEF2FF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid #C7D2FE'
            }}>
              <ClipboardCheck size={18} color="#4F46E5" />
            </div>
            <div>
              <div style={{ fontSize: '0.96rem', fontWeight: 700, color: '#0F172A' }}>
                Controlled Internal Pilot — Response Review
              </div>
              <div style={{ fontSize: '0.74rem', color: '#64748B' }}>
                Evaluating answer quality, response experience, and governance integrity
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', padding: '4px' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Scrollable Body */}
        <div style={{ padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Metadata Bar */}
          <div style={{
            background: '#F8FAFC',
            borderRadius: '8px',
            border: '1px solid #E2E8F0',
            padding: '10px 14px',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '16px',
            fontSize: '0.74rem'
          }}>
            <div>
              <span style={{ color: '#64748B' }}>Response ID: </span>
              <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#0F172A' }}>
                {message?.id ? String(message.id).slice(0, 8) : 'N/A'}
              </span>
            </div>
            {meta?.latency_ms !== undefined && (
              <div>
                <span style={{ color: '#64748B' }}>Latency: </span>
                <span style={{ fontWeight: 600, color: '#0F172A' }}>{meta.latency_ms} ms</span>
              </div>
            )}
            {plan?.question_type && (
              <div>
                <span style={{ color: '#64748B' }}>Type: </span>
                <span style={{ fontWeight: 600, color: '#2563EB', textTransform: 'capitalize' }}>
                  {plan.question_type}
                </span>
              </div>
            )}
            {plan?.resolved_depth && (
              <div>
                <span style={{ color: '#64748B' }}>Depth: </span>
                <span style={{ fontWeight: 600, color: '#7C3AED', textTransform: 'capitalize' }}>
                  {plan.resolved_depth}
                </span>
              </div>
            )}
            <div>
              <span style={{ color: '#64748B' }}>Flags: </span>
              <span style={{ fontWeight: 600, color: '#047857' }}>
                adaptive:{featureFlags.enable_adaptive_composition !== false ? 'on' : 'off'} · wording:{featureFlags.enable_llm_wording_refinement !== false ? 'on' : 'off'}
              </span>
            </div>
            {wording && (
              <div>
                <span style={{ color: '#64748B' }}>Wording: </span>
                <span style={{
                  fontWeight: 600,
                  color: wording.applied ? '#16A34A' : (wording.requested ? '#D97706' : '#64748B')
                }}>
                  {wording.applied ? `polished (${wording.statements_polished || 1} stmts)` : (wording.requested ? 'fallback' : 'deterministic')}
                </span>
              </div>
            )}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Verdict Selection */}
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '8px' }}>
                Overall Verdict <span style={{ color: '#DC2626' }}>*</span>
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setVerdict('PASS')}
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    border: `2px solid ${verdict === 'PASS' ? '#16A34A' : '#E2E8F0'}`,
                    background: verdict === 'PASS' ? '#F0FDF4' : '#FFFFFF',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '4px',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <CheckCircle2 size={20} color="#16A34A" />
                  <span style={{ fontSize: '0.84rem', fontWeight: 700, color: verdict === 'PASS' ? '#166534' : '#334155' }}>
                    PASS
                  </span>
                  <span style={{ fontSize: '0.68rem', color: '#64748B', textAlign: 'center' }}>
                    Meets enterprise rigor & accuracy
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setVerdict('NEEDS_IMPROVEMENT')}
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    border: `2px solid ${verdict === 'NEEDS_IMPROVEMENT' ? '#D97706' : '#E2E8F0'}`,
                    background: verdict === 'NEEDS_IMPROVEMENT' ? '#FFFBEB' : '#FFFFFF',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '4px',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <AlertTriangle size={20} color="#D97706" />
                  <span style={{ fontSize: '0.84rem', fontWeight: 700, color: verdict === 'NEEDS_IMPROVEMENT' ? '#92400E' : '#334155' }}>
                    NEEDS IMPROVEMENT
                  </span>
                  <span style={{ fontSize: '0.68rem', color: '#64748B', textAlign: 'center' }}>
                    Minor gaps, depth or formatting flaw
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setVerdict('UNSAFE')}
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    border: `2px solid ${verdict === 'UNSAFE' ? '#DC2626' : '#E2E8F0'}`,
                    background: verdict === 'UNSAFE' ? '#FEF2F2' : '#FFFFFF',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '4px',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <ShieldAlert size={20} color="#DC2626" />
                  <span style={{ fontSize: '0.84rem', fontWeight: 700, color: verdict === 'UNSAFE' ? '#991B1B' : '#334155' }}>
                    UNSAFE
                  </span>
                  <span style={{ fontSize: '0.68rem', color: '#64748B', textAlign: 'center' }}>
                    Material mutation, hallucination, or breach
                  </span>
                </button>
              </div>
            </div>

            {/* Issue Category (if not PASS) */}
            {verdict !== 'PASS' && (
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                  Primary Failure Category <span style={{ color: '#DC2626' }}>*</span>
                </label>
                <select
                  value={issueCategory}
                  onChange={(e) => setIssueCategory(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #CBD5E1',
                    fontSize: '0.82rem',
                    color: '#0F172A',
                    background: '#FFFFFF'
                  }}
                >
                  <option value="SCOPE_FAILURE">SCOPE_FAILURE (Incorrect document version, role, or temporal scope)</option>
                  <option value="MATERIAL_MUTATION">MATERIAL_MUTATION (Numbers dropped, negation flipped, modality weakened)</option>
                  <option value="EVIDENCE_MAPPING_ERROR">EVIDENCE_MAPPING_ERROR (Uncited statements or disconnected evidence)</option>
                  <option value="MISSING_CONDITION">MISSING_CONDITION (Omitted essential prerequisite or carve-out)</option>
                  <option value="SILENT_CONFLICT">SILENT_CONFLICT (Merged contradictory rules into false harmony)</option>
                  <option value="DEPTH_QUALITY">DEPTH_QUALITY (Brief is too verbose, or Detailed lacks depth)</option>
                  <option value="NAVIGATION_FAILURE">NAVIGATION_FAILURE (Explorer link broken or points to wrong claim)</option>
                  <option value="OTHER">OTHER (Formatting, wording, or general usability issue)</option>
                </select>
              </div>
            )}

            {/* 8-Point Pilot Checklist */}
            <div>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '8px' }}>
                Pilot Evaluation Criteria Checklist
              </div>
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '8px',
                background: '#F8FAFC',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid #E2E8F0'
              }}>
                {checklistItems.map(item => (
                  <label
                    key={item.key}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '8px',
                      cursor: 'pointer',
                      fontSize: '0.76rem',
                      padding: '4px'
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={checklist[item.key]}
                      onChange={() => toggleChecklistItem(item.key)}
                      style={{ marginTop: '2px' }}
                    />
                    <div>
                      <div style={{ fontWeight: 600, color: checklist[item.key] ? '#0F172A' : '#DC2626' }}>
                        {item.label}
                      </div>
                      <div style={{ fontSize: '0.68rem', color: '#64748B', lineHeight: '1.25' }}>
                        {item.desc}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Reviewer Name and Role */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                  Reviewer Name
                </label>
                <input
                  type="text"
                  value={reviewerName}
                  onChange={(e) => setReviewerName(e.target.value)}
                  placeholder="e.g. Sarah Jenkins (Legal)"
                  style={{
                    width: '100%',
                    padding: '7px 10px',
                    borderRadius: '6px',
                    border: '1px solid #CBD5E1',
                    fontSize: '0.8rem'
                  }}
                  required
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                  Reviewer Role / Department
                </label>
                <input
                  type="text"
                  value={reviewerRole}
                  onChange={(e) => setReviewerRole(e.target.value)}
                  placeholder="e.g. Legal Counsel / Policy Steward"
                  style={{
                    width: '100%',
                    padding: '7px 10px',
                    borderRadius: '6px',
                    border: '1px solid #CBD5E1',
                    fontSize: '0.8rem'
                  }}
                />
              </div>
            </div>

            {/* Review Notes */}
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                Evaluator Notes & Observations
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Detail any observed edge cases, missing caveats, or suggestions..."
                rows={3}
                style={{
                  width: '100%',
                  padding: '8px 10px',
                  borderRadius: '6px',
                  border: '1px solid #CBD5E1',
                  fontSize: '0.8rem',
                  resize: 'vertical'
                }}
              />
            </div>

            {/* Actions */}
            <div style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '10px',
              paddingTop: '12px',
              borderTop: '1px solid #E2E8F0'
            }}>
              <button
                type="button"
                onClick={onClose}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  border: '1px solid #CBD5E1',
                  background: '#FFFFFF',
                  color: '#475569',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                style={{
                  padding: '8px 18px',
                  borderRadius: '6px',
                  border: 'none',
                  background: verdict === 'PASS' ? '#16A34A' : (verdict === 'UNSAFE' ? '#DC2626' : '#D97706'),
                  color: '#FFFFFF',
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  cursor: isSubmitting ? 'not-allowed' : 'pointer',
                  opacity: isSubmitting ? 0.7 : 1
                }}
              >
                {isSubmitting ? 'Submitting...' : `Submit Evaluation (${verdict})`}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// Executive Evidence Source Card with Micro-Interactions
function EvidenceSourceCard({
  citation,
  sourceIndex,
  msgId,
  isHighlighted,
  activeWorkspace,
  onOpenWhyThis,
  onCopy,
  isCopied
}) {
  if (!citation) return null;

  const docTitle = citation.source_title || citation.document_title || 'Enterprise Policy Document';
  const section = citation.section || null;
  const page = citation.page || null;
  const verbatimQuote = citation.verbatim_evidence || citation.evidence_span || citation.claim_text || 'Verbatim policy evidence span verified in governing document.';
  const explorerUrl = buildExplorerUrl(citation, activeWorkspace);

  return (
    <div
      id={`citation-${msgId}-${sourceIndex}`}
      style={{
        background: '#FFFFFF',
        border: isHighlighted ? '2px solid #2563EB' : '1px solid #E2E8F0',
        boxShadow: isHighlighted ? '0 0 0 3px rgba(37, 99, 235, 0.15)' : '0 1px 3px rgba(0,0,0,0.03)',
        borderRadius: '8px',
        padding: '12px 14px',
        marginBottom: '10px',
        transition: 'all 0.2s ease'
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span style={{
            background: '#EFF6FF',
            color: '#1D4ED8',
            fontWeight: 700,
            fontSize: '0.70rem',
            padding: '2px 7px',
            borderRadius: '6px',
            fontFamily: 'monospace'
          }}>
            Source {sourceIndex}
          </span>
          <span style={{ fontSize: '0.80rem', fontWeight: 600, color: '#0F172A' }}>
            {docTitle}
          </span>
          {section && (
            <span style={{ fontSize: '0.74rem', color: '#64748B' }}>
              · Section {section}
            </span>
          )}
          {page && (
            <span style={{ fontSize: '0.74rem', color: '#64748B' }}>
              · Page {page}
            </span>
          )}
        </div>
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          fontSize: '0.68rem',
          color: '#059669',
          fontWeight: 600,
          background: '#ECFDF5',
          padding: '1px 6px',
          borderRadius: '4px',
          border: '1px solid #A7F3D0'
        }}>
          <Check size={11} color="#059669" />
          <span>Verified Rule</span>
        </span>
      </div>

      {/* Verbatim Quote */}
      <div style={{
        borderLeft: '3px solid #3B82F6',
        background: '#F8FAFC',
        padding: '8px 12px',
        borderRadius: '0 6px 6px 0',
        fontSize: '0.82rem',
        color: '#334155',
        lineHeight: 1.55,
        fontStyle: 'italic',
        marginBottom: '10px'
      }}>
        “{verbatimQuote}”
      </div>

      {/* Micro-Action Row */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '8px',
        paddingTop: '6px',
        borderTop: '1px solid #F1F5F9'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {/* Why this answer? modal trigger */}
          <button
            type="button"
            onClick={onOpenWhyThis}
            style={{
              background: '#FFFFFF',
              border: '1px solid #CBD5E1',
              borderRadius: '5px',
              padding: '3px 8px',
              fontSize: '0.72rem',
              fontWeight: 600,
              color: '#334155',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#F1F5F9'; e.currentTarget.style.borderColor = '#94A3B8'; }}
            onMouseLeave={e => { e.currentTarget.style.background = '#FFFFFF'; e.currentTarget.style.borderColor = '#CBD5E1'; }}
            title="Inspect atomic claims, trust score, and governance receipt"
          >
            <Info size={12} color="#2563EB" />
            <span>Why this answer?</span>
          </button>

          {/* Copy evidence button */}
          <button
            type="button"
            onClick={onCopy}
            style={{
              background: '#FFFFFF',
              border: '1px solid #CBD5E1',
              borderRadius: '5px',
              padding: '3px 8px',
              fontSize: '0.72rem',
              fontWeight: 500,
              color: isCopied ? '#16A34A' : '#475569',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#F8FAFC'; }}
            onMouseLeave={e => { e.currentTarget.style.background = '#FFFFFF'; }}
            title="Copy verbatim quote and citation to clipboard"
          >
            {isCopied ? <Check size={12} color="#16A34A" /> : <Copy size={12} />}
            <span>{isCopied ? "Copied" : "Copy evidence"}</span>
          </button>
        </div>

        {/* Open in Document Explorer in a NEW TAB */}
        <button
          type="button"
          onClick={() => {
            window.open(explorerUrl, '_blank', 'noopener,noreferrer');
          }}
          style={{
            background: '#EFF6FF',
            border: '1px solid #BFDBFE',
            borderRadius: '5px',
            padding: '3px 9px',
            fontSize: '0.72rem',
            fontWeight: 600,
            color: '#1D4ED8',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            transition: 'all 0.15s ease'
          }}
          onMouseEnter={e => { e.currentTarget.style.background = '#DBEAFE'; }}
          onMouseLeave={e => { e.currentTarget.style.background = '#EFF6FF'; }}
          title="Open exact folder and document preview in a new tab"
        >
          <span>Open in Document Explorer</span>
          <ExternalLink size={12} color="#1D4ED8" />
        </button>
      </div>
    </div>
  );
}

export default function AgentChatPlayground({
  activeOrg,
  activePersona,
  activeWorkspace,
  workspaces,
  showToast,
  selectedSessionId,
  onSessionChange,
  onOpenHitlModal,
  onInspectDocument
}) {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(selectedSessionId || null);
  const [activeSession, setActiveSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [inputPrompt, setInputPrompt] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [showPlusMenu, setShowPlusMenu] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [expandedCitations, setExpandedCitations] = useState({});
  const [activeCitationHighlight, setActiveCitationHighlight] = useState({});
  const [messageDepth, setMessageDepth] = useState({});
  const [copiedMsgId, setCopiedMsgId] = useState(null);
  const [whyThisAnswerModalData, setWhyThisAnswerModalData] = useState(null);
  const [pilotReviewModalData, setPilotReviewModalData] = useState(null);
  const [pilotReviewsByMsgId, setPilotReviewsByMsgId] = useState({});
  const [copiedEvidenceKey, setCopiedEvidenceKey] = useState(null);

  const handleCitationHover = (msgId, sourceNum) => {
    setActiveCitationHighlight(prev => ({ ...prev, [msgId]: sourceNum }));
  };

  // ChatGPT-style Collapsible Chat History State
  const [isHistoryOpen, setIsHistoryOpen] = useState(() => {
    try {
      const saved = localStorage.getItem('copilot_history_open');
      return saved !== null ? saved === 'true' : true;
    } catch {
      return true;
    }
  });
  const [historySearchQuery, setHistorySearchQuery] = useState('');
  const [openMenuSessionId, setOpenMenuSessionId] = useState(null);
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [pinnedSessionIds, setPinnedSessionIds] = useState(() => {
    try {
      const saved = localStorage.getItem('trulin_pinned_chat_sessions');
      return saved ? new Set(JSON.parse(saved)) : new Set();
    } catch {
      return new Set();
    }
  });
  const renameInputRef = useRef(null);

  const toggleHistoryOpen = () => {
    setIsHistoryOpen(prev => {
      const next = !prev;
      try {
        localStorage.setItem('copilot_history_open', String(next));
      } catch (e) {}
      return next;
    });
  };

  useEffect(() => {
    if (editingSessionId && renameInputRef.current) {
      renameInputRef.current.focus();
      renameInputRef.current.select();
    }
  }, [editingSessionId]);

  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (!e.target.closest('.copilot-history-item-actions')) {
        setOpenMenuSessionId(null);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  const handleCitationClick = (msgId, sourceNum) => {
    setExpandedCitations(prev => ({ ...prev, [msgId]: true }));
    setActiveCitationHighlight(prev => ({ ...prev, [msgId]: sourceNum }));
    setTimeout(() => {
      const el = document.getElementById(`citation-${msgId}-${sourceNum}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }, 60);
  };

  useEffect(() => {
    if (selectedSessionId && selectedSessionId !== activeSessionId) {
      setActiveSessionId(selectedSessionId);
      loadSessionDetails(selectedSessionId);
    }
  }, [selectedSessionId]);

  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  const bottomInputRef = useRef(null);
  const fileInputRef = useRef(null);
  const plusMenuRef = useRef(null);
  const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
  const userId = activePersona?.id || null;

  // Copilot Response Mode & Mic Dictation State
  const [selectedMode, setSelectedMode] = useState('quick');
  const [showModeMenu, setShowModeMenu] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const modeMenuRef = useRef(null);
  const recognitionRef = useRef(null);

  const activeModeObj = COPILOT_MODES.find(m => m.id === selectedMode) || COPILOT_MODES[0];

  const firstName = activePersona?.name && activePersona.name !== 'User' && activePersona.name !== 'Anonymous'
    ? activePersona.name.split(' ')[0].charAt(0).toUpperCase() + activePersona.name.split(' ')[0].slice(1).toLowerCase()
    : '';

  // Close plus and mode menu on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (plusMenuRef.current && !plusMenuRef.current.contains(e.target)) {
        setShowPlusMenu(false);
      }
      if (modeMenuRef.current && !modeMenuRef.current.contains(e.target)) {
        setShowModeMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Voice dictation using browser SpeechRecognition if available
  const handleMicClick = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      if (showToast) showToast("Voice input not supported in this browser. Please type your query.");
      return;
    }
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsListening(true);
        if (showToast) showToast("🎙️ Listening... Speak your policy question");
      };

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          setInputPrompt(prev => prev ? `${prev} ${transcript}` : transcript);
        }
      };

      recognition.onerror = () => {
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (e) {
      setIsListening(false);
      if (showToast) showToast("Microphone access could not be initialized");
    }
  };


  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result || '';
      setAttachedFile({
        name: file.name,
        size: file.size,
        content: String(content)
      });
      if (showToast) showToast(`Attached document: ${file.name}`);
      setShowPlusMenu(false);
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  // Load chat sessions for active user/persona & workspace
  const loadSessions = async (selectFirst = true) => {
    setIsLoadingSessions(true);
    try {
      let url = userId
        ? `/v1/chat/sessions?organization_id=${orgId}&user_id=${userId}`
        : `/v1/chat/sessions?organization_id=${orgId}`;
      if (activeWorkspace && activeWorkspace.id !== 'all') {
        url += `&workspace_id=${activeWorkspace.id}`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        const normalized = data.map(s => ({
          ...s,
          title: (s.title || 'Untitled Conversation').replace(/^\[.*?\]\s*/, '')
        }));
        setSessions(normalized);
        if (selectFirst && normalized.length > 0) {
          loadSessionDetails(normalized[0].id);
        } else if (normalized.length === 0) {
          setActiveSessionId(null);
          setActiveSession(null);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error("Failed to load chat sessions", err);
    } finally {
      setIsLoadingSessions(false);
    }
  };

  // Reload sessions whenever active workspace or org changes
  useEffect(() => {
    loadSessions(true);
  }, [activeWorkspace?.id, orgId, userId]);

  // Load a single session details & messages
  const loadSessionDetails = async (sessionId) => {
    try {
      const res = await fetch(`/v1/chat/sessions/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        setActiveSessionId(data.id);
        setActiveSession(data);
        setMessages(data.messages || []);
        if (onSessionChange) onSessionChange(data.id);

        try {
          const pRes = await fetch(`/v1/chat/telemetry/pilot-feedback?session_id=${data.id}`);
          if (pRes.ok) {
            const pData = await pRes.json();
            const map = {};
            (pData.evaluations || []).forEach(ev => {
              if (ev.message_id) map[ev.message_id] = ev;
            });
            setPilotReviewsByMsgId(map);
          }
        } catch {
          // ignore telemetry failure
        }
      }
    } catch (err) {
      console.error("Failed to load session details", err);
    }
  };

  // Create new session tagged with active departmental workspace
  const handleCreateNewChat = async (initialTitle = "New Conversation") => {
    // If the active session is already empty, just focus and reuse it rather than creating empty duplicates
    if (messages.length === 0 && activeSession && (!activeSession.message_count || activeSession.message_count === 0)) {
      bottomInputRef.current?.focus();
      return activeSession.id;
    }

    try {
      const finalTitle = initialTitle;
      const res = await fetch('/v1/chat/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_id: orgId,
          user_id: userId,
          user_name: activePersona?.name || 'Anonymous',
          user_role: activePersona?.role || 'developer',
          title: finalTitle,
          workspace_id: activeWorkspace?.id || 'all',
          domain: activeWorkspace?.domain || 'global',
        }),
      });
      if (res.ok) {
        const newSession = await res.json();
        setSessions(prev => [newSession, ...prev]);
        setActiveSessionId(newSession.id);
        setActiveSession(newSession);
        setMessages([]);
        if (showToast) showToast(`Started new chat in ${activeWorkspace?.name || 'workspace'}`);
        return newSession.id;
      }
    } catch (err) {
      console.error("Failed to create new chat session", err);
    }
    return null;
  };

  // Delete session
  const handleDeleteSession = async (e, sessionId) => {
    if (e) e.stopPropagation();
    setOpenMenuSessionId(null);
    try {
      const res = await fetch(`/v1/chat/sessions/${sessionId}`, { method: 'DELETE' });
      if (res.ok) {
        setSessions(prev => prev.filter(s => s.id !== sessionId));
        setPinnedSessionIds(prev => {
          if (prev.has(sessionId)) {
            const next = new Set(prev);
            next.delete(sessionId);
            try {
              localStorage.setItem('trulin_pinned_chat_sessions', JSON.stringify(Array.from(next)));
            } catch (err) {}
            return next;
          }
          return prev;
        });
        if (activeSessionId === sessionId) {
          const remaining = sessions.filter(s => s.id !== sessionId);
          if (remaining.length > 0) {
            loadSessionDetails(remaining[0].id);
          } else {
            setActiveSessionId(null);
            setActiveSession(null);
            setMessages([]);
          }
        }
        if (showToast) showToast("Chat session deleted");
      }
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  };

  // Toggle Pin chat session
  const handleTogglePin = (sessionId, e) => {
    if (e) e.stopPropagation();
    setPinnedSessionIds(prev => {
      const next = new Set(prev);
      const isNowPinned = !next.has(sessionId);
      if (next.has(sessionId)) {
        next.delete(sessionId);
      } else {
        next.add(sessionId);
      }
      try {
        localStorage.setItem('trulin_pinned_chat_sessions', JSON.stringify(Array.from(next)));
      } catch (err) {}
      if (showToast) showToast(isNowPinned ? "Chat pinned to top" : "Chat unpinned");
      return next;
    });
    setOpenMenuSessionId(null);
  };

  // Start inline rename
  const handleStartRename = (session, e) => {
    if (e) e.stopPropagation();
    setEditingSessionId(session.id);
    setEditingTitle(session.title || '');
    setOpenMenuSessionId(null);
  };

  // Commit session rename to backend
  const handleSaveRename = async (sessionId, e) => {
    if (e) e.stopPropagation();
    const trimmed = editingTitle.trim();
    if (!trimmed) {
      setEditingSessionId(null);
      return;
    }
    try {
      const res = await fetch(`/v1/chat/sessions/${sessionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: trimmed })
      });
      if (res.ok) {
        setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, title: trimmed } : s));
        if (activeSession && activeSession.id === sessionId) {
          setActiveSession(prev => prev ? { ...prev, title: trimmed } : null);
        }
        if (showToast) showToast('Conversation renamed');
      } else {
        if (showToast) showToast('Failed to rename conversation');
      }
    } catch (err) {
      console.error('Rename failed', err);
      if (showToast) showToast('Failed to rename conversation');
    } finally {
      setEditingSessionId(null);
    }
  };

  // Copy chat title to clipboard
  const handleCopyTitle = (session, e) => {
    if (e) e.stopPropagation();
    navigator.clipboard.writeText(session.title || 'Conversation');
    if (showToast) showToast('Chat title copied to clipboard');
    setOpenMenuSessionId(null);
  };

  // Group chat sessions chronologically like ChatGPT, with Pinned at top
  const groupSessionsByDate = (sessionList) => {
    const pinned = [];
    const unpinned = [];

    sessionList.forEach(session => {
      if (pinnedSessionIds.has(session.id)) {
        pinned.push(session);
      } else {
        unpinned.push(session);
      }
    });

    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const startOfYesterday = startOfToday - 86400000;
    const sevenDaysAgo = startOfToday - 7 * 86400000;
    const thirtyDaysAgo = startOfToday - 30 * 86400000;

    const groups = {
      today: [],
      yesterday: [],
      previous7Days: [],
      previous30Days: [],
      older: []
    };

    unpinned.forEach(session => {
      const date = session.created_at ? new Date(session.created_at).getTime() : 0;
      if (date >= startOfToday) {
        groups.today.push(session);
      } else if (date >= startOfYesterday) {
        groups.yesterday.push(session);
      } else if (date >= sevenDaysAgo) {
        groups.previous7Days.push(session);
      } else if (date >= thirtyDaysAgo) {
        groups.previous30Days.push(session);
      } else {
        groups.older.push(session);
      }
    });

    const result = [];
    if (pinned.length > 0) {
      result.push({ label: 'Pinned', items: pinned });
    }
    const standardGroups = [
      { label: 'Today', items: groups.today },
      { label: 'Yesterday', items: groups.yesterday },
      { label: 'Previous 7 Days', items: groups.previous7Days },
      { label: 'Previous 30 Days', items: groups.previous30Days },
      { label: 'Older', items: groups.older },
    ].filter(g => g.items.length > 0);

    return [...result, ...standardGroups];
  };

  // Send message
  const handleSendMessage = async (customPrompt = null) => {
    let textToSend = (customPrompt || inputPrompt).trim();
    if ((!textToSend && !attachedFile) || isSending) return;

    if (attachedFile) {
      textToSend = `${textToSend ? textToSend + '\n\n' : ''}[Attached Document: ${attachedFile.name}]\n${attachedFile.content.slice(0, 3000)}`;
      setAttachedFile(null);
    }

    let currentSid = activeSessionId;
    if (!currentSid) {
      currentSid = await handleCreateNewChat(textToSend.slice(0, 50));
      if (!currentSid) return;
    }

    // Optimistically append user message
    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: textToSend,
      metadata_json: { author: activePersona?.name || 'User', role: activePersona?.role || 'developer' },
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);
    setInputPrompt('');
    setIsSending(true);

    try {
      const res = await fetch(`/v1/chat/sessions/${currentSid}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_id: orgId,
          content: textToSend,
          user_id: userId,
          user_name: activePersona?.name || 'User',
          user_role: activePersona?.role || 'developer',
          workspace_id: activeWorkspace?.id || 'all',
          domain: activeWorkspace?.domain || 'global',
          requested_depth: 'auto',
        }),
      });

      if (res.ok) {
        const result = await res.json();
        // Replace with persisted messages
        setMessages(prev => [
          ...prev.filter(m => m.id !== tempUserMsg.id),
          result.user_message,
          result.assistant_message
        ]);

        // Auto-assign smart, distinct title based on first query like professional copilots
        const assignedTitle = result.session_title || generateSmartTitle(textToSend);
        const currentTitle = (activeSession?.title || '').trim();
        const isGeneric = !currentTitle ||
          currentTitle === 'New Conversation' ||
          currentTitle === 'Untitled Conversation' ||
          currentTitle.endsWith('New Conversation') ||
          currentTitle.startsWith('[');

        if (isGeneric && assignedTitle && assignedTitle !== 'New Conversation') {
          setActiveSession(prev => prev ? { ...prev, title: assignedTitle } : null);
          setSessions(prev => prev.map(s => s.id === currentSid ? { ...s, title: assignedTitle } : s));
          if (!result.session_title) {
            fetch(`/v1/chat/sessions/${currentSid}`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ title: assignedTitle })
            }).catch(e => console.error('Failed to sync smart title', e));
          }
        } else {
          loadSessions(false);
        }
      } else {
        if (showToast) showToast("Failed to process message with Context Gate");
      }
    } catch (err) {
      console.error("Failed to send message", err);
    } finally {
      setIsSending(false);
    }
  };

  // Scroll to bottom on new messages inside the chat container ONLY (prevents page/window from scrolling)
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, isSending]);

  // Keep focus in bottom input bar after message sent
  useEffect(() => {
    if (messages.length > 0 && !isSending) {
      bottomInputRef.current?.focus();
    }
  }, [messages.length, isSending]);

  // Reload sessions when user persona or org changes
  useEffect(() => {
    loadSessions(true);
  }, [orgId, userId]);

  const filteredSessions = sessions.filter(s => {
    if (!historySearchQuery.trim()) return true;
    return (s.title || '').toLowerCase().includes(historySearchQuery.toLowerCase());
  });

  const sessionGroups = historySearchQuery.trim()
    ? [{ label: `Search Results (${filteredSessions.length})`, items: filteredSessions }]
    : groupSessionsByDate(filteredSessions);

  return (
    <div
      className="copilot-canvas"
      style={{
        background: '#FAF8F5',
        border: 'none',
        borderRadius: 0,
        overflow: 'hidden',
        width: '100%',
        height: '100%',
        flex: 1,
        minHeight: 0,
        display: 'flex',
        flexDirection: 'row'
      }}
    >
      {/* 1. LEFT SIDE: CHATGPT-STYLE COLLAPSIBLE CHAT HISTORY PANEL */}
      <aside
        className={`copilot-history-sidebar ${!isHistoryOpen ? 'copilot-history-sidebar-closed' : ''}`}
        aria-label="Chat History"
      >
        {/* Panel Header */}
        <div className="copilot-history-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
            <span style={{
              fontSize: '0.86rem',
              fontWeight: 700,
              color: '#1C1917',
              letterSpacing: '-0.01em',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}>
              Chats
            </span>
            <span style={{
              background: '#EFECE6',
              color: '#78716C',
              padding: '1px 6px',
              borderRadius: '10px',
              fontSize: '0.68rem',
              fontWeight: 600
            }}>
              {filteredSessions.length}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <button
              type="button"
              className="copilot-history-icon-btn"
              onClick={() => handleCreateNewChat()}
              title="New Chat"
            >
              <Plus size={16} strokeWidth={2.2} />
            </button>
            <button
              type="button"
              className="copilot-history-icon-btn"
              onClick={toggleHistoryOpen}
              title="Close chat history"
            >
              <PanelLeftClose size={16} strokeWidth={1.8} />
            </button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="copilot-history-search-wrapper">
          <Search size={13} color="#A8A29E" style={{ flexShrink: 0 }} />
          <input
            type="text"
            className="copilot-history-search-input"
            placeholder="Search chats..."
            value={historySearchQuery}
            onChange={e => setHistorySearchQuery(e.target.value)}
          />
          {historySearchQuery && (
            <button
              type="button"
              onClick={() => setHistorySearchQuery('')}
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex' }}
            >
              <X size={12} color="#78716C" />
            </button>
          )}
        </div>

        {/* Scrollable Grouped History List */}
        <div className="copilot-history-scroll">
          {sessionGroups.length === 0 ? (
            <div style={{
              padding: '24px 12px',
              textAlign: 'center',
              color: '#A8A29E',
              fontSize: '0.80rem'
            }}>
              {historySearchQuery ? 'No matching conversations' : 'No previous chats yet.'}
            </div>
          ) : (
            sessionGroups.map(group => (
              <div key={group.label} style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
                <div className="copilot-history-group-title">
                  {group.label}
                </div>
                {group.items.map(session => {
                  const isCurrent = activeSessionId === session.id;
                  const isEditing = editingSessionId === session.id;
                  const isMenuOpen = openMenuSessionId === session.id;
                  const isPinned = pinnedSessionIds.has(session.id);

                  return (
                    <div
                      key={session.id}
                      className={`copilot-history-item ${isCurrent ? 'copilot-history-item-active' : ''}`}
                      onClick={() => {
                        if (!isEditing) {
                          setActiveSessionId(session.id);
                          loadSessionDetails(session.id);
                        }
                      }}
                      title={(session.title || 'Untitled Conversation').replace(/^\[.*?\]\s*/, '')}
                    >

                      {isEditing ? (
                        <div
                          style={{ display: 'flex', alignItems: 'center', gap: '4px', flex: 1, minWidth: 0 }}
                          onClick={e => e.stopPropagation()}
                        >
                          <input
                            ref={renameInputRef}
                            type="text"
                            className="copilot-history-rename-input"
                            value={editingTitle}
                            onChange={e => setEditingTitle(e.target.value)}
                            onKeyDown={e => {
                              if (e.key === 'Enter') handleSaveRename(session.id, e);
                              if (e.key === 'Escape') setEditingSessionId(null);
                            }}
                          />
                          <button
                            type="button"
                            onClick={e => handleSaveRename(session.id, e)}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '2px', display: 'flex' }}
                            title="Save"
                          >
                            <Check size={13} color="#16A34A" />
                          </button>
                          <button
                            type="button"
                            onClick={e => { e.stopPropagation(); setEditingSessionId(null); }}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '2px', display: 'flex' }}
                            title="Cancel"
                          >
                            <X size={13} color="#78716C" />
                          </button>
                        </div>
                      ) : (
                        <>
                          <span className="copilot-history-item-title" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                            {isPinned && (
                              <Pin size={11} color="#D97706" style={{ flexShrink: 0, transform: 'rotate(45deg)' }} />
                            )}
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {(session.title || 'Untitled Conversation').replace(/^\[.*?\]\s*/, '')}
                            </span>
                          </span>

                          {/* 3-Dots Action Button & Dropdown Menu */}
                          <div
                            className={`copilot-history-item-actions ${(isMenuOpen || isCurrent) ? 'copilot-history-item-actions-visible' : ''}`}
                            onClick={e => e.stopPropagation()}
                          >
                            <button
                              type="button"
                              className="copilot-history-more-btn"
                              title="Chat options"
                              onClick={e => {
                                e.stopPropagation();
                                setOpenMenuSessionId(prev => prev === session.id ? null : session.id);
                              }}
                              style={{
                                opacity: (isCurrent || isMenuOpen) ? 1 : undefined,
                                color: isCurrent ? '#44403C' : undefined
                              }}
                            >
                              <MoreHorizontal size={14} />
                            </button>

                            {/* Floating Dropdown Menu */}
                            {isMenuOpen && (
                              <div className="copilot-history-dropdown-menu">
                                <button
                                  type="button"
                                  className="copilot-history-dropdown-item"
                                  onClick={e => handleTogglePin(session.id, e)}
                                >
                                  {isPinned ? <PinOff size={13} color="#D97706" /> : <Pin size={13} color="#57534E" />}
                                  <span>{isPinned ? "Unpin Chat" : "Pin Chat"}</span>
                                </button>
                                <button
                                  type="button"
                                  className="copilot-history-dropdown-item"
                                  onClick={e => handleStartRename(session, e)}
                                >
                                  <Pencil size={13} color="#57534E" />
                                  <span>Rename</span>
                                </button>
                                <button
                                  type="button"
                                  className="copilot-history-dropdown-item"
                                  onClick={e => handleCopyTitle(session, e)}
                                >
                                  <Copy size={13} color="#57534E" />
                                  <span>Copy Title</span>
                                </button>
                                <div style={{ height: '1px', background: '#E8E3DC', margin: '2px 0' }} />
                                <button
                                  type="button"
                                  className="copilot-history-dropdown-item copilot-history-dropdown-item-danger"
                                  onClick={e => handleDeleteSession(e, session.id)}
                                >
                                  <Trash2 size={13} />
                                  <span>Delete Chat</span>
                                </button>
                              </div>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            ))
          )}
        </div>
      </aside>

      {/* 2. RIGHT SIDE: MAIN COPILOT WORKSPACE */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          flex: 1,
          minWidth: 0,
          background: '#FAF8F5',
          overflow: 'hidden',
          position: 'relative'
        }}
      >
        {/* Top Header Bar for Right Side */}
        <header className="copilot-top-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
            {!isHistoryOpen && (
              <button
                type="button"
                className="copilot-topbar-toggle-btn"
                onClick={toggleHistoryOpen}
                title="Open chat history sidebar"
              >
                <PanelLeftOpen size={15} strokeWidth={2} />
                <span>History</span>
              </button>
            )}

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
              <span style={{
                fontSize: '0.86rem',
                fontWeight: 600,
                color: '#1C1917',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                maxWidth: '420px'
              }}>
                {(activeSession?.title || 'New Conversation').replace(/^\[.*?\]\s*/, '')}
              </span>
            </div>
          </div>
        </header>

        {/* Conversation Stream & Bottom Floating Bar */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            flex: 1,
            minHeight: 0,
            padding: '0',
            overflow: 'hidden',
            background: 'transparent'
          }}
        >
          {/* Messages Scroll Area */}
          <div
            id="chat-messages-container"
            ref={chatContainerRef}
            style={{
              flex: 1,
              minHeight: 0,
              overflowY: messages.length === 0 ? 'hidden' : 'auto',
              overflowX: 'hidden',
              overscrollBehavior: 'contain',
              padding: messages.length === 0 ? '24px 20px' : '16px 20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
              justifyContent: messages.length === 0 ? 'center' : 'flex-start'
            }}
          >

            {/* Empty State: Copilot Warm Minimalist Aesthetic (Image 1 Parity) */}
            {messages.length === 0 && (
              <div style={{
                margin: 'auto',
                width: '100%',
                maxWidth: '720px',
                textAlign: 'center',
                padding: '16px 12px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center'
              }}>
                {/* Hero Greeting */}
                <h1 className="copilot-hero-title">
                  Hey{firstName ? ` ${firstName}` : ''}, what’s on your mind today?
                </h1>

                {/* Floating Rounded Pill-Card */}
                <div className="copilot-card">
                  {/* Attached Document Preview if any */}
                  {attachedFile && (
                    <div style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      background: '#F4F4F5',
                      border: '1px solid #E4E4E7',
                      borderRadius: '12px',
                      padding: '3px 10px',
                      fontSize: '0.74rem',
                      color: '#27272A',
                      marginBottom: '8px'
                    }}>
                      <FileText size={13} color="#52525B" />
                      <span>{attachedFile.name}</span>
                      <button
                        type="button"
                        onClick={() => setAttachedFile(null)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0 2px', display: 'flex' }}
                      >
                        <X size={12} color="#71717A" />
                      </button>
                    </div>
                  )}

                  {/* Top Textarea */}
                  <textarea
                    className="copilot-textarea"
                    rows={2}
                    value={inputPrompt}
                    onChange={e => setInputPrompt(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage();
                      }
                    }}
                    placeholder={
                      activeWorkspace && activeWorkspace.id !== 'all'
                        ? `Message Copilot in ${activeWorkspace.name}...`
                        : "Message Copilot"
                    }
                    disabled={isSending}
                  />

                  {/* Bottom Row inside card */}
                  <div className="copilot-bottom-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                    {/* Right: Mic Button, Send Button */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <button
                        type="button"
                        className={`copilot-action-icon-btn ${isListening ? 'copilot-mic-listening' : ''}`}
                        title={isListening ? "Listening... click to stop" : "Voice dictation"}
                        onClick={handleMicClick}
                      >
                        <Mic size={18} />
                      </button>

                      <button
                        type="button"
                        className="copilot-send-btn"
                        disabled={(!inputPrompt.trim() && !attachedFile) || isSending}
                        onClick={() => handleSendMessage()}
                        title="Send question"
                      >
                        <ArrowUp size={16} strokeWidth={2.5} />
                      </button>
                    </div>
                  </div>
                </div>

                {/* 2 Centered Rows of Capsule Suggestion Pills (Image 1 Parity) */}
                <div className="copilot-pill-row">
                  {(COPILOT_PILLS_BY_WORKSPACE[activeWorkspace?.id || 'all'] || COPILOT_PILLS_BY_WORKSPACE.all).map((pill, i) => (
                    <button
                      key={i}
                      type="button"
                      className="copilot-pill"
                      onClick={() => handleSendMessage(pill.query)}
                      title={`Ask: "${pill.query}"`}
                    >
                      {pill.label}
                    </button>
                  ))}
                </div>
              </div>
            )}


            {/* Timeline divider matching Microsoft Copilot ("Today ────────────") */}
            {messages.length > 0 && (
              <div style={{
                width: '100%',
                maxWidth: '740px',
                margin: '8px auto 16px auto',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                color: '#78716C',
                fontSize: '0.82rem',
                fontWeight: 500
              }}>
                <span style={{ color: '#57534E', fontWeight: 600 }}>Today</span>
                <div style={{ flex: 1, height: '1px', background: '#E7E5E4' }} />
              </div>
            )}

            {/* Message Stream */}
            {messages.map((msg, idx) => {
              const isUser = msg.role === 'user';
              const meta = msg.metadata_json || {};
              const decision = meta.decision;
              const citations = meta.citations || [];
              const warnings = meta.warnings || [];
              const isCopied = copiedMsgId === msg.id;

              return (
                <div
                  key={msg.id || idx}
                  style={{
                    width: '100%',
                    maxWidth: '740px',
                    margin: '0 auto',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: isUser ? 'flex-end' : 'flex-start',
                    gap: '4px'
                  }}
                >
                  {isUser ? (
                    <div
                      style={{
                        maxWidth: '82%',
                        background: '#FBE9D9',
                        color: '#292524',
                        padding: '10px 18px',
                        borderRadius: '18px',
                        fontSize: '0.94rem',
                        lineHeight: 1.55,
                        fontWeight: 450,
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        boxShadow: 'none',
                        border: 'none',
                        fontFamily: 'inherit'
                      }}
                    >
                      {msg.content}
                    </div>
                  ) : (
                    <div
                      style={{
                        width: '100%',
                        maxWidth: '100%',
                        background: 'transparent',
                        border: 'none',
                        borderRadius: '0',
                        boxShadow: 'none',
                        padding: '2px 0 14px 0',
                        color: '#292524'
                      }}
                    >
                      {/* Understood Context Query if multi-turn rewrite */}
                      {meta.resolved_query && (
                        <div style={{
                          fontSize: '0.74rem',
                          color: '#78716C',
                          fontStyle: 'italic',
                          marginBottom: '8px'
                        }}>
                          Context query: "{meta.resolved_query}"
                        </div>
                      )}

                      {(() => {
                        const structured = meta.structured_answer || null;
                        const isActionEvaluation = meta.mode === 'action_evaluation' || meta.answer_status === 'EVALUATED' || !!meta.action_evaluation;
                        const isConflict = meta.answer_status === 'DISPUTED' || meta.has_conflicts || !!structured?.conflict_analysis?.is_conflicted;
                        const isNoVerifiedRule = meta.answer_status === 'NO_VERIFIED_RULE';

                        // -----------------------------------------------------------
                        // STATE 4: ADVISORY ACTION EVALUATION (Mode B Decision Brief)
                        // -----------------------------------------------------------
                        if (isActionEvaluation) {
                          const actionEval = meta.action_evaluation || {};
                          const verdict = actionEval.verdict || decision || 'REVIEW';
                          const riskLevel = actionEval.risk_level || meta.risk_level || 'MEDIUM';
                          const auditId = actionEval.audit_id || meta.audit_id || 'AUD-GOV-ACTION';
                          const reasons = (actionEval.reason ? [actionEval.reason] : (actionEval.missing_requirements || []));
                          const matchedClaims = actionEval.matched_claims || [];
                          const suggestedAction = actionEval.suggested_action || null;

                          return (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                              {/* Header Pill: Decision Governance Verdict */}
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <span style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '5px',
                                    fontSize: '0.74rem',
                                    fontWeight: 700,
                                    padding: '3px 10px',
                                    borderRadius: '12px',
                                    background: verdict === 'ALLOW' ? '#DCFCE7' : verdict === 'BLOCK' ? '#FEE2E2' : '#FEF3C7',
                                    color: verdict === 'ALLOW' ? '#15803D' : verdict === 'BLOCK' ? '#B91C1C' : '#B45309',
                                    border: `1px solid ${verdict === 'ALLOW' ? '#86EFAC' : verdict === 'BLOCK' ? '#FCA5A5' : '#FDE68A'}`
                                  }}>
                                    {verdict === 'ALLOW' ? <ShieldCheck size={13} color="#15803D" /> : verdict === 'BLOCK' ? <AlertTriangle size={13} color="#B91C1C" /> : <Scale size={13} color="#B45309" />}
                                    <span>DECISION GOVERNANCE — {verdict}</span>
                                  </span>
                                  <span style={{
                                    fontSize: '0.68rem',
                                    fontWeight: 700,
                                    padding: '2px 8px',
                                    borderRadius: '6px',
                                    background: riskLevel === 'HIGH' ? '#FEF2F2' : riskLevel === 'MEDIUM' ? '#FFFBEB' : '#F0FDF4',
                                    color: riskLevel === 'HIGH' ? '#991B1B' : riskLevel === 'MEDIUM' ? '#92400E' : '#166534',
                                    border: `1px solid ${riskLevel === 'HIGH' ? '#FECACA' : riskLevel === 'MEDIUM' ? '#FDE68A' : '#BBF7D0'}`
                                  }}>
                                    Risk: {riskLevel}
                                  </span>
                                </div>
                                <span style={{ fontSize: '0.70rem', color: '#64748B', fontFamily: 'monospace' }}>
                                  {auditId}
                                </span>
                              </div>

                              {/* Decision Status Dual Badge */}
                              <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '12px',
                                padding: '8px 12px',
                                background: '#F8FAFC',
                                border: '1px solid #E2E8F0',
                                borderRadius: '6px',
                                fontSize: '0.78rem'
                              }}>
                                <div>
                                  <span style={{ color: '#64748B' }}>Policy Verdict: </span>
                                  <strong style={{ color: verdict === 'ALLOW' ? '#15803D' : verdict === 'BLOCK' ? '#DC2626' : '#D97706' }}>
                                    {verdict}
                                  </strong>
                                </div>
                                <span style={{ color: '#CBD5E1' }}>|</span>
                                <div>
                                  <span style={{ color: '#64748B' }}>Execution Status: </span>
                                  <strong style={{ color: '#0F172A' }}>Not executed</strong>
                                </div>
                              </div>

                              {/* Evaluated Action & Policy Findings */}
                              <div style={{
                                background: '#FFFFFF',
                                border: `1px solid ${verdict === 'BLOCK' ? '#FECACA' : '#E2E8F0'}`,
                                borderRadius: '8px',
                                padding: '14px',
                                boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
                              }}>
                                <div style={{ fontSize: '0.80rem', fontWeight: 700, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '8px' }}>
                                  Policy Findings & Entitlements:
                                </div>
                                {reasons.length > 0 ? (
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                    {reasons.map((r, ri) => (
                                      <div key={ri} style={{ display: 'flex', alignItems: 'baseline', gap: '8px', fontSize: '0.88rem', color: '#1E293B', lineHeight: 1.55 }}>
                                        <span style={{ color: verdict === 'ALLOW' ? '#15803D' : '#DC2626', fontWeight: 700 }}>•</span>
                                        <span>{r}</span>
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <div style={{ fontSize: '0.88rem', color: '#1E293B', lineHeight: 1.55 }}>
                                    <RichAnswerContent
                                      content={msg.content}
                                      onCitationClick={(srcNum) => handleCitationClick(msg.id, srcNum)}
                                      onCitationHover={(srcNum) => handleCitationHover(msg.id, srcNum)}
                                    />
                                  </div>
                                )}

                                {suggestedAction && (
                                  <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid #F1F5F9', fontSize: '0.82rem', color: '#334155' }}>
                                    <strong style={{ color: '#0F172A' }}>Recommended Next Action: </strong>
                                    <span>{suggestedAction}</span>
                                  </div>
                                )}
                              </div>

                              {/* Mandatory Fixed Non-Collapsible Advisory Warning Banner */}
                              <div style={{
                                background: '#EFF6FF',
                                border: '1px solid #BFDBFE',
                                borderRadius: '8px',
                                padding: '12px 14px',
                                display: 'flex',
                                alignItems: 'flex-start',
                                gap: '10px'
                              }}>
                                <Shield size={16} color="#2563EB" style={{ marginTop: '2px', flexShrink: 0 }} />
                                <div style={{ fontSize: '0.78rem', color: '#1E40AF', lineHeight: 1.5 }}>
                                  <strong style={{ display: 'block', marginBottom: '2px' }}>
                                    Advisory evaluation only — no external action executed.
                                  </strong>
                                  Trulin operates in read-only governance mode. Banking rails, payment gateways, and directory mutations were not invoked.
                                </div>
                              </div>

                              {/* Collapsible Accordions for Action Evaluation */}
                              {matchedClaims.length > 0 && (
                                <AccordionSection title="Matched Policy Obligations" count={matchedClaims.length} icon={Layers}>
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                    {matchedClaims.map((claim, cIdx) => (
                                      <div key={cIdx} style={{ fontSize: '0.76rem', color: '#334155', padding: '6px 8px', background: '#F8FAFC', borderRadius: '4px', border: '1px solid #E2E8F0' }}>
                                        • {claim}
                                      </div>
                                    ))}
                                  </div>
                                </AccordionSection>
                              )}

                              <AccordionSection title="Actor Authority & Governance Audit" icon={Hash}>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.74rem', color: '#475569' }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span>Audit ID:</span>
                                    <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{auditId}</span>
                                  </div>
                                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span>Risk Assessment:</span>
                                    <span style={{ fontWeight: 600, color: riskLevel === 'HIGH' ? '#DC2626' : riskLevel === 'MEDIUM' ? '#D97706' : '#16A34A' }}>
                                      {riskLevel}
                                    </span>
                                  </div>
                                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span>Execution Gate:</span>
                                    <span style={{ color: '#047857', fontWeight: 600 }}>Fail-Safe Advisory Pipeline (Read-Only)</span>
                                  </div>
                                </div>
                              </AccordionSection>
                            </div>
                          );
                        }

                        // -----------------------------------------------------------
                        // STATE 2: POLICY DISPUTE / CONFLICT (Context-Dependent or Contradiction)
                        // -----------------------------------------------------------
                        if (isConflict) {
                          const conflictAnalysis = structured?.conflict_analysis || null;
                          const rawConflictType = conflictAnalysis?.conflict_type || (meta.conflicts?.[0]?.conflict_type) || 'CONTEXT_DEPENDENT';
                          const conflictType = rawConflictType.toUpperCase();

                          // Precise Legal Language
                          const conflictSummary = (() => {
                            if (conflictType === 'CONTEXT_DEPENDENT' || conflictType.includes('CONTEXT')) {
                              return "The sources specify different outcomes depending on the applicable product, customer type, or cancellation pathway. Trulin cannot determine the governing rule without additional scope information.";
                            }
                            if (conflictType === 'DIRECT_CONTRADICTION' || conflictType.includes('CONTRADICT')) {
                              return "These sources provide conflicting rules for the same scope. Human adjudication is required before either rule is treated as operative.";
                            }
                            return conflictAnalysis?.conflict_summary || extractCleanBottomLine(msg, structured) || "These policy sources specify different outcomes. Human adjudication is required to reconcile the operative rule.";
                          })();

                          const pathways = conflictAnalysis?.pathways && conflictAnalysis.pathways.length > 0
                            ? conflictAnalysis.pathways
                            : (meta.conflicts && meta.conflicts.length > 0
                                ? meta.conflicts.flatMap((c) => [
                                    {
                                      path_label: `Path A: ${c.claim_1_source || 'Agreement A'}`,
                                      source_title: c.claim_1_source || 'Source A',
                                      section: c.claim_1_section || null,
                                      rule_summary: c.claim_1_text || 'Rule A',
                                      verbatim_quote: c.claim_1_evidence || '',
                                      document_id: c.claim_1_document_id || null,
                                      claim_id: c.claim_1_id || null
                                    },
                                    {
                                      path_label: `Path B: ${c.claim_2_source || 'Agreement B'}`,
                                      source_title: c.claim_2_source || 'Source B',
                                      section: c.claim_2_section || null,
                                      rule_summary: c.claim_2_text || 'Rule B',
                                      verbatim_quote: c.claim_2_evidence || '',
                                      document_id: c.claim_2_document_id || null,
                                      claim_id: c.claim_2_id || null
                                    }
                                  ])
                                : []);

                          return (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                              {/* Header Badge */}
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                                <span style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '5px',
                                  fontSize: '0.72rem',
                                  fontWeight: 700,
                                  padding: '3px 10px',
                                  borderRadius: '12px',
                                  background: 'rgba(239, 68, 68, 0.08)',
                                  color: '#B91C1C',
                                  border: '1px solid rgba(239, 68, 68, 0.25)'
                                }}>
                                  <AlertTriangle size={13} color="#DC2626" />
                                  <span>⚠️ POLICY DISPUTE — SOURCES DISAGREE</span>
                                </span>
                                <span style={{
                                  fontSize: '0.68rem',
                                  fontWeight: 700,
                                  padding: '2px 8px',
                                  borderRadius: '6px',
                                  background: '#FEF2F2',
                                  color: '#991B1B',
                                  border: '1px solid #FECACA',
                                  fontFamily: 'monospace'
                                }}>
                                  {conflictType === 'CONTEXT_DEPENDENT' ? 'Context-Dependent' : 'Direct Contradiction'}
                                </span>
                              </div>

                              {/* Direct Precise Conflict Summary */}
                              <div style={{
                                fontSize: '0.94rem',
                                lineHeight: 1.6,
                                color: '#1C1917',
                                fontWeight: 450
                              }}>
                                <RichAnswerContent
                                  content={conflictSummary}
                                  onCitationClick={(srcNum) => handleCitationClick(msg.id, srcNum)}
                                  onCitationHover={(srcNum) => handleCitationHover(msg.id, srcNum)}
                                />
                              </div>

                              {/* Dual Pathway Grid (Side-by-Side on Desktop, Never Merged or Averaged) */}
                              {pathways.length > 0 && (
                                <div style={{
                                  display: 'grid',
                                  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                                  gap: '12px',
                                  margin: '4px 0'
                                }}>
                                  {pathways.map((pw, pwi) => {
                                    const pExplorerUrl = buildExplorerUrl({
                                      document_id: pw.document_id,
                                      claim_id: pw.claim_id
                                    }, activeWorkspace);

                                    return (
                                      <div key={pwi} style={{
                                        background: '#FFFFFF',
                                        border: '1px solid #FCA5A5',
                                        borderRadius: '8px',
                                        padding: '12px 14px',
                                        boxShadow: '0 1px 3px rgba(239, 68, 68, 0.04)',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        gap: '8px'
                                      }}>
                                        <div style={{
                                          display: 'inline-block',
                                          fontSize: '0.72rem',
                                          fontWeight: 700,
                                          color: '#991B1B',
                                          background: '#FEE2E2',
                                          padding: '2px 8px',
                                          borderRadius: '6px',
                                          alignSelf: 'flex-start'
                                        }}>
                                          {pw.path_label || `Pathway ${pwi === 0 ? 'A' : 'B'}`}
                                        </div>
                                        <div style={{ fontSize: '0.76rem', color: '#64748B' }}>
                                          <strong>Source: </strong>{pw.source_title}{pw.section ? ` · §${pw.section}` : ''}
                                        </div>
                                        <div style={{ fontSize: '0.84rem', color: '#1E293B', lineHeight: 1.5, fontWeight: 500 }}>
                                          {pw.rule_summary}
                                        </div>
                                        {pw.verbatim_quote && (
                                          <div style={{
                                            borderLeft: '3px solid #EF4444',
                                            background: '#FEF2F2',
                                            padding: '6px 10px',
                                            borderRadius: '0 4px 4px 0',
                                            fontSize: '0.78rem',
                                            color: '#7F1D1D',
                                            fontStyle: 'italic',
                                            lineHeight: 1.45
                                          }}>
                                            “{pw.verbatim_quote}”
                                          </div>
                                        )}
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-start', marginTop: 'auto', paddingTop: '4px' }}>
                                          <button
                                            type="button"
                                            onClick={() => {
                                              window.open(pExplorerUrl, '_blank', 'noopener,noreferrer');
                                            }}
                                            style={{
                                              background: '#EFF6FF',
                                              border: '1px solid #BFDBFE',
                                              borderRadius: '5px',
                                              padding: '3px 8px',
                                              fontSize: '0.70rem',
                                              fontWeight: 600,
                                              color: '#1D4ED8',
                                              cursor: 'pointer',
                                              display: 'inline-flex',
                                              alignItems: 'center',
                                              gap: '4px',
                                              transition: 'all 0.15s ease'
                                            }}
                                            title="Open pathway document in Document Explorer (new tab)"
                                          >
                                            <span>Open in Document Explorer</span>
                                            <ExternalLink size={11} color="#1D4ED8" />
                                          </button>
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              )}

                              {/* Escalate to Data Steward Action Banner */}
                              <div style={{
                                background: '#FEF2F2',
                                border: '1px solid #FECACA',
                                borderRadius: '8px',
                                padding: '12px 14px',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                flexWrap: 'wrap',
                                gap: '10px'
                              }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <ShieldAlert size={16} color="#DC2626" />
                                  <span style={{ fontSize: '0.80rem', color: '#991B1B', fontWeight: 500 }}>
                                    This contradiction requires human data steward adjudication to reconcile operative policy.
                                  </span>
                                </div>
                                <button
                                  type="button"
                                  onClick={() => {
                                    if (onOpenHitlModal) onOpenHitlModal();
                                    else window.dispatchEvent(new CustomEvent('open-hitl-modal', { detail: { messageId: msg.id } }));
                                    if (showToast) showToast('Escalated dispute directly to Human Data Steward review queue.');
                                  }}
                                  style={{
                                    background: '#DC2626',
                                    color: '#FFFFFF',
                                    border: 'none',
                                    borderRadius: '6px',
                                    padding: '6px 12px',
                                    fontSize: '0.74rem',
                                    fontWeight: 700,
                                    cursor: 'pointer',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '5px',
                                    boxShadow: '0 1px 2px rgba(220,38,38,0.2)'
                                  }}
                                  title="Escalate this dispute directly to human data steward queue"
                                >
                                  <ShieldAlert size={13} color="#FFFFFF" />
                                  <span>Escalate to Data Steward</span>
                                </button>
                              </div>

                              {/* Collapsible Conflict Analysis Details */}
                              <AccordionSection title="Conflict Analysis & Telemetry Details" icon={GitCompare}>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.74rem', color: '#475569' }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span>Classification:</span>
                                    <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{conflictType}</span>
                                  </div>
                                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span>Severity Level:</span>
                                    <span style={{ fontWeight: 600, color: '#DC2626' }}>
                                      {conflictAnalysis?.severity || 'HIGH'}
                                    </span>
                                  </div>
                                  {conflictAnalysis?.recommended_action && (
                                    <div style={{ marginTop: '4px', paddingTop: '4px', borderTop: '1px solid #F1F5F9' }}>
                                      <strong>Recommended Action: </strong>{conflictAnalysis.recommended_action}
                                    </div>
                                  )}
                                  {conflictAnalysis?.affected_claim_ids && conflictAnalysis.affected_claim_ids.length > 0 && (
                                    <div style={{ marginTop: '4px' }}>
                                      <span style={{ color: '#64748B' }}>Affected Claims: </span>
                                      {conflictAnalysis.affected_claim_ids.map((id, idi) => (
                                        <span key={idi} style={{ fontFamily: 'monospace', fontSize: '0.70rem', background: '#F1F5F9', padding: '1px 5px', borderRadius: '3px', margin: '0 2px' }}>
                                          {id.slice(0, 8)}...
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              </AccordionSection>
                            </div>
                          );
                        }

                        // -----------------------------------------------------------
                        // STATE 3: NO VERIFIED RULE FOUND (Fail-Closed Abstention)
                        // -----------------------------------------------------------
                        if (isNoVerifiedRule) {
                          const abstentionText = structured?.bottom_line_answer || extractCleanBottomLine(msg, structured) || "No verified rule matching this question was found in the approved enterprise policy set.";

                          return (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                              {/* Header Badge */}
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '5px',
                                  fontSize: '0.72rem',
                                  fontWeight: 600,
                                  padding: '3px 10px',
                                  borderRadius: '12px',
                                  background: 'rgba(120, 113, 108, 0.08)',
                                  color: '#57534E',
                                  border: '1px solid rgba(120, 113, 108, 0.25)'
                                }}>
                                  <Clock size={12} color="#78716C" />
                                  <span>○ NO VERIFIED RULE FOUND · Policy Boundary</span>
                                </span>
                              </div>

                              {/* Plain-Language Abstention */}
                              <div style={{
                                fontSize: '0.96rem',
                                lineHeight: 1.6,
                                color: '#1C1917',
                                fontWeight: 450
                              }}>
                                <RichAnswerContent content={abstentionText} />
                              </div>

                              {/* Governance Boundary Scope Explainer */}
                              <div style={{
                                background: '#F8FAFC',
                                border: '1px solid #E2E8F0',
                                borderRadius: '8px',
                                padding: '12px 14px',
                                fontSize: '0.82rem',
                                color: '#475569',
                                lineHeight: 1.55
                              }}>
                                <div style={{ fontWeight: 600, color: '#1E293B', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                  <Shield size={13} color="#64748B" />
                                  <span>Fail-Closed Governance Boundary</span>
                                </div>
                                <div>
                                  Checked across governing enterprise policy documents. Unverified, candidate, and draft content was excluded under fail-closed governance.
                                </div>
                              </div>

                              {/* What Would Make This Answerable? Callout */}
                              <div style={{
                                background: '#FFFFFF',
                                border: '1px solid #E2E8F0',
                                borderRadius: '8px',
                                padding: '12px 14px'
                              }}>
                                <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }}>
                                  What would make this answerable?
                                </div>
                                <div style={{ fontSize: '0.82rem', color: '#475569', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                                    <span style={{ color: '#0284C7', fontWeight: 700 }}>•</span>
                                    <span>Approved operative policy governing this specific inquiry or threshold.</span>
                                  </div>
                                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                                    <span style={{ color: '#0284C7', fontWeight: 700 }}>•</span>
                                    <span>Explicit numerical timeframe, dollar limit, or governing stakeholder criteria.</span>
                                  </div>
                                </div>
                              </div>

                              {/* Direct Action Buttons */}
                              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginTop: '2px' }}>
                                <button
                                  type="button"
                                  onClick={() => {
                                    window.open('/documents?view=ingest', '_blank', 'noopener,noreferrer');
                                  }}
                                  style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    fontSize: '0.76rem',
                                    fontWeight: 600,
                                    padding: '6px 12px',
                                    borderRadius: '6px',
                                    background: '#FFFFFF',
                                    border: '1px solid #CBD5E1',
                                    color: '#334155',
                                    cursor: 'pointer',
                                    transition: 'all 0.15s ease'
                                  }}
                                  onMouseEnter={e => { e.currentTarget.style.background = '#F1F5F9'; }}
                                  onMouseLeave={e => { e.currentTarget.style.background = '#FFFFFF'; }}
                                >
                                  <UploadCloud size={13} color="#64748B" />
                                  <span>Upload Governing Document ↗</span>
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    window.open('/curator/approvals', '_blank', 'noopener,noreferrer');
                                  }}
                                  style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    fontSize: '0.76rem',
                                    fontWeight: 600,
                                    padding: '6px 12px',
                                    borderRadius: '6px',
                                    background: '#FFFFFF',
                                    border: '1px solid #CBD5E1',
                                    color: '#334155',
                                    cursor: 'pointer',
                                    transition: 'all 0.15s ease'
                                  }}
                                  onMouseEnter={e => { e.currentTarget.style.background = '#F1F5F9'; }}
                                  onMouseLeave={e => { e.currentTarget.style.background = '#FFFFFF'; }}
                                >
                                  <Search size={13} color="#64748B" />
                                  <span>Inspect Candidate Queue in Curator ↗</span>
                                </button>
                              </div>
                            </div>
                          );
                        }

                        // -----------------------------------------------------------
                        // STATE 1: SUPPORTED RULE (Verified Policy Q&A Default)
                        // -----------------------------------------------------------
                        const bottomLine = extractCleanBottomLine(msg, structured);
                        const conditions = structured?.conditions || [];
                        const exceptions = structured?.exceptions || [];
                        const claims = (structured?.verified_claims_used && structured.verified_claims_used.length > 0)
                          ? structured.verified_claims_used
                          : citations;
                        const primaryCitation = (citations.length > 0)
                          ? citations[0]
                          : (claims.length > 0 ? claims[0] : null);
                        const secondaryCitations = citations.length > 1 ? citations.slice(1) : [];
                        const sectionContext = structured?.section_context || [];
                        const groundingScore = structured?.grounding_score ?? meta.verification?.grounding_score ?? 1.0;
                        const scopeSummary = structured?.scope_summary || meta?.scope_summary;
                        const responsePlan = structured?.response_plan || meta?.response_plan;
                        const explanationBlocks = structured?.explanation_blocks || [];
                        const currentDepth = messageDepth[msg.id] || responsePlan?.resolved_depth || 'standard';

                        // Multi-document coverage: identify secondary citation from distinct document
                        const distinctSecondaryCitation = secondaryCitations.find(c =>
                          c.source_title && c.source_title !== primaryCitation?.source_title
                        );

                        const primarySrcIdx = primaryCitation?.source_index || 1;
                        const isPrimaryHighlighted = activeCitationHighlight[msg.id] === primarySrcIdx;

                        const handleCopyEvidence = (citation, key) => {
                          const quote = citation?.verbatim_evidence || citation?.evidence_span || citation?.claim_text || '';
                          const title = citation?.source_title || citation?.document_title || 'Policy Document';
                          const sec = citation?.section ? `, Section ${citation.section}` : '';
                          const text = `“${quote}” — ${title}${sec}`;
                          navigator.clipboard.writeText(text);
                          setCopiedEvidenceKey(key);
                          if (showToast) showToast("Evidence copied to clipboard");
                          setTimeout(() => setCopiedEvidenceKey(null), 2000);
                        };

                        return (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {/* Header: Status Badge on left, Adaptive Depth Controls [Brief | Standard | Detailed] on right */}
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '2px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '5px',
                                  fontSize: '0.72rem',
                                  fontWeight: 700,
                                  padding: '3px 10px',
                                  borderRadius: '12px',
                                  background: 'rgba(16, 185, 129, 0.08)',
                                  color: '#047857',
                                  border: '1px solid rgba(16, 185, 129, 0.25)'
                                }}>
                                  <ShieldCheck size={12} color="#059669" />
                                  <span>✓ SUPPORTED BY VERIFIED RULES</span>
                                </span>
                                <span style={{ fontSize: '0.70rem', color: '#64748B', fontWeight: 600 }}>
                                  Policy Q&A
                                </span>
                              </div>

                              {/* Depth Selector Pills: Brief | Standard | Detailed */}
                              <div style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                background: '#F1F5F9',
                                padding: '2px',
                                borderRadius: '6px',
                                border: '1px solid #E2E8F0',
                                gap: '2px'
                              }}>
                                {['brief', 'standard', 'detailed'].map((depthOption) => {
                                  const isActive = currentDepth === depthOption;
                                  return (
                                    <button
                                      key={depthOption}
                                      type="button"
                                      onClick={() => setMessageDepth(prev => ({ ...prev, [msg.id]: depthOption }))}
                                      style={{
                                        border: 'none',
                                        background: isActive ? '#FFFFFF' : 'transparent',
                                        color: isActive ? '#0F172A' : '#64748B',
                                        fontWeight: isActive ? 700 : 500,
                                        fontSize: '0.68rem',
                                        padding: '2px 8px',
                                        borderRadius: '4px',
                                        cursor: 'pointer',
                                        boxShadow: isActive ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                                        textTransform: 'capitalize',
                                        transition: 'all 0.12s ease'
                                      }}
                                    >
                                      {depthOption}
                                    </button>
                                  );
                                })}
                              </div>
                            </div>

                            {/* Explicit Scope Summary Line */}
                            {scopeSummary?.label && (
                              <div style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '6px',
                                fontSize: '0.72rem',
                                color: '#475569',
                                background: '#F8FAFC',
                                padding: '3px 9px',
                                borderRadius: '5px',
                                border: '1px solid #E2E8F0',
                                marginBottom: '2px',
                                width: 'fit-content'
                              }}>
                                <FileText size={11} color="#64748B" />
                                <span><strong>Scope:</strong> {scopeSummary.label}</span>
                              </div>
                            )}

                            {/* Bottom-Line Answer (Crisp, High-Contrast Typography) */}
                            <div style={{
                              fontSize: '0.96rem',
                              lineHeight: 1.65,
                              color: '#1C1917',
                              fontWeight: 450,
                              marginBottom: (conditions.length > 0 || exceptions.length > 0 || explanationBlocks.length > 0) ? '4px' : '8px'
                            }}>
                              <RichAnswerContent
                                content={bottomLine}
                                onCitationClick={(srcNum) => handleCitationClick(msg.id, srcNum)}
                                onCitationHover={(srcNum) => handleCitationHover(msg.id, srcNum)}
                              />
                            </div>

                            {/* Adaptive Explanation Blocks (Rendered for Standard and Detailed modes) */}
                            {currentDepth !== 'brief' && explanationBlocks.length > 0 && (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '4px' }}>
                                {explanationBlocks.filter(b => b.id !== 'block-conditions').map((block) => (
                                  <div key={block.id} style={{
                                    background: block.block_type === 'checklist' ? '#F8FAFC' : (block.block_type === 'table' ? '#FFFFFF' : 'transparent'),
                                    border: (block.block_type === 'checklist' || block.block_type === 'table') ? '1px solid #E2E8F0' : 'none',
                                    borderRadius: '8px',
                                    padding: (block.block_type === 'checklist' || block.block_type === 'table') ? '10px 14px' : '4px 0',
                                  }}>
                                    {block.heading && (
                                      <div style={{
                                        fontSize: '0.75rem',
                                        fontWeight: 700,
                                        color: '#334155',
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.04em',
                                        marginBottom: '6px'
                                      }}>
                                        {block.heading}
                                      </div>
                                    )}
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                                      {block.statements.map((stmt, stmtIdx) => (
                                        <div key={stmt.id} style={{ display: 'flex', alignItems: 'baseline', gap: '8px', fontSize: '0.86rem', color: '#1E293B', lineHeight: 1.55 }}>
                                          {block.block_type === 'checklist' ? (
                                            <span style={{
                                              display: 'inline-flex',
                                              alignItems: 'center',
                                              justifyContent: 'center',
                                              width: '18px',
                                              height: '18px',
                                              borderRadius: '50%',
                                              background: '#EFF6FF',
                                              color: '#2563EB',
                                              fontSize: '0.68rem',
                                              fontWeight: 700,
                                              border: '1px solid #BFDBFE',
                                              flexShrink: 0
                                            }}>
                                              {stmtIdx + 1}
                                            </span>
                                          ) : (
                                            <span style={{ color: '#0284C7', fontWeight: 700 }}>•</span>
                                          )}
                                          <div>
                                            <RichAnswerContent
                                              content={stmt.text}
                                              onCitationClick={(srcNum) => handleCitationClick(msg.id, srcNum)}
                                              onCitationHover={(srcNum) => handleCitationHover(msg.id, srcNum)}
                                            />
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Conditions & Exceptions Block */}
                            {(conditions.length > 0 || exceptions.length > 0) && (
                              <div style={{
                                background: '#F8FAFC',
                                border: '1px solid #E2E8F0',
                                borderRadius: '8px',
                                padding: '10px 14px',
                                marginBottom: '8px'
                              }}>
                                <div style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '6px',
                                  fontSize: '0.74rem',
                                  fontWeight: 700,
                                  color: '#475569',
                                  textTransform: 'uppercase',
                                  letterSpacing: '0.04em',
                                  marginBottom: '6px'
                                }}>
                                  <Scale size={13} color="#64748B" />
                                  <span>Conditions & Exceptions</span>
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                                  {conditions.map((cond, ci) => (
                                    <div key={`c-${ci}`} style={{ display: 'flex', alignItems: 'baseline', gap: '7px', fontSize: '0.84rem', color: '#334155', lineHeight: 1.5 }}>
                                      <span style={{ color: '#0284C7', fontWeight: 700 }}>•</span>
                                      <div>
                                        <strong style={{ color: '#0369A1', fontWeight: 600 }}>Condition: </strong>
                                        <span>{cond}</span>
                                      </div>
                                    </div>
                                  ))}
                                  {exceptions.map((exc, ei) => (
                                    <div key={`e-${ei}`} style={{ display: 'flex', alignItems: 'baseline', gap: '7px', fontSize: '0.84rem', color: '#334155', lineHeight: 1.5 }}>
                                      <span style={{ color: '#D97706', fontWeight: 700 }}>•</span>
                                      <div>
                                        <strong style={{ color: '#B45309', fontWeight: 600 }}>Exception: </strong>
                                        <span>{exc}</span>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Evidence Coverage & Accounting Banner */}
                            {citations.length > 0 && (
                              <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                fontSize: '0.72rem',
                                color: '#475569',
                                background: '#F8FAFC',
                                border: '1px solid #E2E8F0',
                                borderRadius: '6px',
                                padding: '5px 10px',
                                marginBottom: '4px'
                              }}>
                                <span>
                                  <strong>Evidence Accounting:</strong> {(currentDepth !== 'brief' && distinctSecondaryCitation) ? '2 primary sources displayed' : '1 primary source displayed'}
                                  {Math.max(0, citations.length - ((currentDepth !== 'brief' && distinctSecondaryCitation) ? 2 : 1)) > 0 &&
                                    ` · ${Math.max(0, citations.length - ((currentDepth !== 'brief' && distinctSecondaryCitation) ? 2 : 1))} additional verified sources in Supporting Claims`}
                                </span>
                                <span style={{ fontSize: '0.68rem', color: '#94A3B8' }}>Individual statement citations</span>
                              </div>
                            )}

                            {/* Flagship Primary Evidence Source Card (Desktop Open by Default) */}
                            {primaryCitation && (
                              <EvidenceSourceCard
                                citation={primaryCitation}
                                sourceIndex={primarySrcIdx}
                                msgId={msg.id}
                                isHighlighted={isPrimaryHighlighted}
                                activeWorkspace={activeWorkspace}
                                onOpenWhyThis={() => {
                                  setWhyThisAnswerModalData({
                                    citation: primaryCitation,
                                    claim: claims[0] || primaryCitation,
                                    structured,
                                    meta
                                  });
                                }}
                                onCopy={() => handleCopyEvidence(primaryCitation, `primary-${msg.id}`)}
                                isCopied={copiedEvidenceKey === `primary-${msg.id}`}
                              />
                            )}

                            {/* Coverage-based Secondary Evidence Card (Exposed when multi-document scope applies and depth is Standard or Detailed) */}
                            {currentDepth !== 'brief' && distinctSecondaryCitation && (
                              <EvidenceSourceCard
                                citation={distinctSecondaryCitation}
                                sourceIndex={distinctSecondaryCitation.source_index || 2}
                                msgId={msg.id}
                                isHighlighted={activeCitationHighlight[msg.id] === (distinctSecondaryCitation.source_index || 2)}
                                activeWorkspace={activeWorkspace}
                                onOpenWhyThis={() => {
                                  setWhyThisAnswerModalData({
                                    citation: distinctSecondaryCitation,
                                    claim: distinctSecondaryCitation,
                                    structured,
                                    meta
                                  });
                                }}
                                onCopy={() => handleCopyEvidence(distinctSecondaryCitation, `secondary-${msg.id}`)}
                                isCopied={copiedEvidenceKey === `secondary-${msg.id}`}
                              />
                            )}

                            {/* Progressive Disclosure Accordions: Technical metadata collapsed by default */}
                            {claims.length > 0 && (
                              <AccordionSection title="Supporting Claims" count={claims.length} icon={Layers}>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                  {claims.map((c, ci) => (
                                    <div key={ci} style={{
                                      padding: '8px 10px',
                                      background: '#F8FAFC',
                                      border: '1px solid #E2E8F0',
                                      borderRadius: '6px',
                                      fontSize: '0.76rem',
                                      color: '#334155'
                                    }}>
                                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px', marginBottom: '4px', flexWrap: 'wrap' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                          <span style={{ fontWeight: 700, color: '#D97706', fontFamily: 'monospace' }}>
                                            [{c.source_index || ci + 1}]
                                          </span>
                                          <ModalityPill modality={c.modality || 'MUST'} />
                                          <span style={{ fontWeight: 600, color: '#1E293B' }}>
                                            {c.document_title || c.source_title || 'Policy Document'}
                                            {c.section ? ` · §${c.section}` : ''}
                                          </span>
                                        </div>
                                        {c.claim_id && (
                                          <span style={{ fontSize: '0.66rem', color: '#94A3B8', fontFamily: 'monospace' }}>
                                            ID: {c.claim_id.slice(0, 8)}...
                                          </span>
                                        )}
                                      </div>
                                      {c.subject && c.predicate && c.object ? (
                                        <div style={{ fontSize: '0.74rem', color: '#475569', marginBottom: '4px' }}>
                                          <span style={{ color: '#0369A1', fontWeight: 600 }}>{c.subject}</span>
                                          {' → '}
                                          <span style={{ color: '#7C3AED', fontWeight: 600 }}>{c.predicate}</span>
                                          {' → '}
                                          <span style={{ color: '#059669', fontWeight: 600 }}>{c.object}</span>
                                        </div>
                                      ) : (
                                        <div style={{ fontSize: '0.74rem', color: '#475569', marginBottom: '4px' }}>
                                          {c.claim_text || c.verbatim_evidence}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </AccordionSection>
                            )}

                            {/* Related Context — Not an operative rule (Explicit Non-Normative Decoupling) */}
                            {sectionContext.length > 0 && (
                              <AccordionSection title="Related Context — not an operative rule" count={sectionContext.length} icon={Info}>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                  <div style={{
                                    fontSize: '0.72rem',
                                    color: '#64748B',
                                    fontStyle: 'italic',
                                    padding: '4px 8px',
                                    background: '#F1F5F9',
                                    borderRadius: '4px',
                                    borderLeft: '3px solid #94A3B8',
                                    marginBottom: '4px'
                                  }}>
                                    ℹ️ Explanatory background only; does not establish an independent rule or obligation.
                                  </div>
                                  {sectionContext.map((sc, sci) => (
                                    <div key={sci} style={{
                                      padding: '8px 10px',
                                      background: '#F8FAFC',
                                      border: '1px solid #E2E8F0',
                                      borderRadius: '6px',
                                      fontSize: '0.76rem',
                                      color: '#475569',
                                      lineHeight: 1.5
                                    }}>
                                      <div style={{ fontWeight: 600, color: '#334155', marginBottom: '2px' }}>
                                        {sc.document_title || 'Document'}{sc.section_title || sc.section ? ` · §${sc.section_title || sc.section}` : ''}
                                      </div>
                                      <div style={{ fontStyle: 'italic' }}>
                                        “{sc.context_text || sc.text}”
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </AccordionSection>
                            )}

                            {/* Verification & Provenance Telemetry */}
                            <AccordionSection title="Verification & Provenance" icon={Shield}>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.74rem', color: '#475569' }}>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                  <span style={{ color: '#64748B' }}>Answer Verifier:</span>
                                  <span style={{ fontWeight: 600, color: '#059669' }}>✓ PASS: Grounded in Verified Policy Claims</span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                  <span style={{ color: '#64748B' }}>Grounding Score:</span>
                                  <span style={{ fontWeight: 600, color: '#1E293B', fontFamily: 'monospace' }}>
                                    {(groundingScore * 100).toFixed(0)}%
                                  </span>
                                </div>
                                {meta.audit_id && (
                                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <span style={{ color: '#64748B' }}>Audit ID:</span>
                                    <span style={{ fontFamily: 'monospace', color: '#64748B' }}>{meta.audit_id}</span>
                                  </div>
                                )}
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                  <span style={{ color: '#64748B' }}>Governance Boundary:</span>
                                  <span style={{ color: '#047857', fontWeight: 500 }}>Fail-Closed Tier (Verified Operative Policy)</span>
                                </div>
                              </div>
                            </AccordionSection>

                            {/* Additional Sources (Sources 2..N) */}
                            {secondaryCitations.length > 0 && (
                              <AccordionSection title="Additional Sources" count={secondaryCitations.length} icon={BookOpen}>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                  {secondaryCitations.map((c, ci) => {
                                    const srcIdx = c.source_index || (ci + 2);
                                    return (
                                      <EvidenceSourceCard
                                        key={ci}
                                        citation={c}
                                        sourceIndex={srcIdx}
                                        msgId={msg.id}
                                        isHighlighted={activeCitationHighlight[msg.id] === srcIdx}
                                        activeWorkspace={activeWorkspace}
                                        onOpenWhyThis={() => {
                                          setWhyThisAnswerModalData({
                                            citation: c,
                                            claim: claims[ci + 1] || c,
                                            structured,
                                            meta
                                          });
                                        }}
                                        onCopy={() => handleCopyEvidence(c, `sec-${msg.id}-${srcIdx}`)}
                                        isCopied={copiedEvidenceKey === `sec-${msg.id}-${srcIdx}`}
                                      />
                                    );
                                  })}
                                </div>
                              </AccordionSection>
                            )}
                          </div>
                        );
                      })()}

                      {/* Minimal Bottom Action Row: Copy button, latency badge, and Pilot Review button */}
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginTop: '12px',
                        paddingTop: '6px',
                        fontSize: '0.74rem',
                        color: '#78716C',
                        borderTop: '1px solid #F8FAFC'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <button
                            type="button"
                            onClick={() => {
                              const copyText = meta.structured_answer?.bottom_line_answer || msg.content;
                              navigator.clipboard.writeText(copyText);
                              setCopiedMsgId(msg.id);
                              if (showToast) showToast("Copied to clipboard");
                              setTimeout(() => setCopiedMsgId(null), 2000);
                            }}
                            style={{
                              background: 'none',
                              border: 'none',
                              cursor: 'pointer',
                              padding: '2px 0',
                              color: isCopied ? '#16A34A' : '#78716C',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              fontSize: '0.74rem',
                              fontWeight: 500
                            }}
                            title="Copy Answer"
                          >
                            {isCopied ? <Check size={13} color="#16A34A" /> : <Copy size={13} />}
                            <span>{isCopied ? "Copied" : "Copy"}</span>
                          </button>

                          {meta?.latency_ms !== undefined && (
                            <span style={{ fontSize: '0.70rem', color: '#94A3B8' }}>
                              ⚡ {meta.latency_ms}ms
                            </span>
                          )}
                        </div>

                        {/* Pilot Review Modal Trigger */}
                        {(() => {
                          const reviewed = pilotReviewsByMsgId[msg.id];
                          return (
                            <button
                              type="button"
                              onClick={() => {
                                setPilotReviewModalData({
                                  message: msg,
                                  sessionId: activeSessionId
                                });
                              }}
                              style={{
                                background: reviewed ? (reviewed.verdict === 'PASS' ? '#F0FDF4' : (reviewed.verdict === 'UNSAFE' ? '#FEF2F2' : '#FFFBEB')) : '#FFFFFF',
                                border: `1px solid ${reviewed ? (reviewed.verdict === 'PASS' ? '#86EFAC' : (reviewed.verdict === 'UNSAFE' ? '#FCA5A5' : '#FDE68A')) : '#CBD5E1'}`,
                                borderRadius: '5px',
                                padding: '2px 8px',
                                cursor: 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                                fontSize: '0.72rem',
                                fontWeight: 600,
                                color: reviewed ? (reviewed.verdict === 'PASS' ? '#166534' : (reviewed.verdict === 'UNSAFE' ? '#991B1B' : '#92400E')) : '#475569',
                                transition: 'all 0.15s ease'
                              }}
                              title="Submit formal pilot acceptance review (verdict, criteria checklist, and notes)"
                            >
                              <ClipboardCheck size={12} color={reviewed ? (reviewed.verdict === 'PASS' ? '#16A34A' : (reviewed.verdict === 'UNSAFE' ? '#DC2626' : '#D97706')) : '#4F46E5'} />
                              <span>{reviewed ? `Pilot: ${reviewed.verdict}` : "Pilot Review"}</span>
                            </button>
                          );
                        })()}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}

            {/* Dynamic Multi-Step Process Pipeline Animation */}
            {isSending && (
              <ChatProcessingPipeline activeWorkspace={activeWorkspace} />
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Bottom Floating Copilot Bar - Active Conversation State */}
          {messages.length > 0 && (
            <div style={{
              padding: '6px 20px 12px 20px',
              background: 'transparent',
              flexShrink: 0,
              display: 'flex',
              justifyContent: 'center',
              position: 'relative'
            }}>
              <div
                className="copilot-compact-bar"
                style={{
                  position: 'relative',
                  width: '100%',
                  maxWidth: '740px'
                }}
              >
                {/* Floating Attached Document Preview if any */}
                {attachedFile && (
                  <div style={{
                    position: 'absolute',
                    bottom: 'calc(100% + 6px)',
                    left: '12px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    background: '#FFFFFF',
                    border: '1px solid #E4E4E7',
                    borderRadius: '12px',
                    padding: '3px 10px',
                    fontSize: '0.72rem',
                    color: '#27272A',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
                    zIndex: 10
                  }}>
                    <FileText size={12} color="#52525B" />
                    <span style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {attachedFile.name}
                    </span>
                    <button
                      type="button"
                      onClick={() => setAttachedFile(null)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0 2px', display: 'flex' }}
                    >
                      <X size={11} color="#71717A" />
                    </button>
                  </div>
                )}

                {/* Single-Row Textarea */}
                <textarea
                  ref={bottomInputRef}
                  className="copilot-compact-textarea"
                  rows={1}
                  value={inputPrompt}
                  onChange={e => {
                    setInputPrompt(e.target.value);
                    e.target.style.height = 'auto';
                    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
                  }}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                      if (e.target) e.target.style.height = 'auto';
                    }
                  }}
                  placeholder={
                    activeWorkspace && activeWorkspace.id !== 'all'
                      ? `Message Copilot in ${activeWorkspace.name}...`
                      : "Message Copilot"
                  }
                  disabled={isSending}
                />

                {/* Inline Action Buttons: Mic & Peach Arrow Send */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
                  <button
                    type="button"
                    className={`copilot-action-icon-btn ${isListening ? 'copilot-mic-listening' : ''}`}
                    title={isListening ? "Listening... click to stop" : "Voice dictation"}
                    onClick={handleMicClick}
                    style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '50%',
                      border: 'none',
                      background: isListening ? '#FEE2E2' : 'transparent',
                      color: isListening ? '#EF4444' : '#52525B',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <Mic size={17} />
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      if (!isSending) handleSendMessage();
                    }}
                    disabled={!isSending && (!inputPrompt.trim() && !attachedFile)}
                    title={isSending ? "Generating response..." : "Send question"}
                    style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '50%',
                      border: 'none',
                      background: '#FBE9D9',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      cursor: (!isSending && !inputPrompt.trim() && !attachedFile) ? 'default' : 'pointer',
                      opacity: (!isSending && !inputPrompt.trim() && !attachedFile) ? 0.6 : 1,
                      transition: 'all 0.15s cubic-bezier(0.16, 1, 0.3, 1)',
                      flexShrink: 0
                    }}
                  >
                    {isSending ? (
                      <div style={{ width: '9px', height: '9px', background: '#292524', borderRadius: '2px' }} />
                    ) : (
                      <ArrowUp size={16} color="#292524" strokeWidth={2.5} />
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>

      {/* Primary Trust Interaction: Why This Answer Lineage & Governance Modal */}
      {whyThisAnswerModalData && (
        <WhyThisAnswerModal
          data={whyThisAnswerModalData}
          onClose={() => setWhyThisAnswerModalData(null)}
          activeWorkspace={activeWorkspace}
        />
      )}

      {/* Controlled Pilot Review Modal */}
      {pilotReviewModalData && (
        <PilotReviewModal
          data={pilotReviewModalData}
          onClose={() => setPilotReviewModalData(null)}
          onFeedbackSubmitted={(msgId, feedback) => {
            setPilotReviewsByMsgId(prev => ({ ...prev, [msgId]: feedback }));
          }}
          showToast={showToast}
        />
      )}
    </div>
  );
}

