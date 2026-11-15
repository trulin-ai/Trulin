import React, { useState, useEffect, useRef } from 'react';
import { 
  MessageSquare, Plus, MoreHorizontal, Search, Trash2, 
  CheckCircle2, Clock, ShieldCheck, Sparkles, AlertTriangle, 
  Copy, Check, ChevronDown, ChevronRight, BookOpen, Layers, Shield,
  ExternalLink, ShieldAlert, ArrowUpRight, Mic, ArrowUp, FileText, X,
  PanelLeftClose, PanelLeftOpen, Pencil, Share2
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
    icon: "🎯"
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
function RichAnswerContent({ content, onCitationClick }) {
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
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'rgba(0, 0, 0, 0.05)',
              border: 'none',
              borderRadius: '4px',
              color: '#78716C',
              fontWeight: 600,
              fontSize: '0.72rem',
              padding: '1px 5px',
              margin: '0 2px',
              cursor: 'pointer',
              verticalAlign: 'baseline',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#FBE9D9';
              e.currentTarget.style.color = '#7C2D12';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(0, 0, 0, 0.05)';
              e.currentTarget.style.color = '#78716C';
            }}
            title={`View Source ${num}`}
          >
            {num}
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
      elements.push(
        <h4 key={`header-${i}`} style={{
          fontSize: '0.98rem',
          fontWeight: 600,
          color: '#1C1917',
          margin: '14px 0 6px 0'
        }}>
          {renderInlineFormatted(headerText)}
        </h4>
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
  { id: 'quick', label: 'Quick response', icon: '💬', desc: 'Direct bottom-line answer with synthesized takeaways' },
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
  const [copiedMsgId, setCopiedMsgId] = useState(null);

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

  // Group chat sessions chronologically like ChatGPT
  const groupSessionsByDate = (sessionList) => {
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

    sessionList.forEach(session => {
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

    return [
      { label: 'Today', items: groups.today },
      { label: 'Yesterday', items: groups.yesterday },
      { label: 'Previous 7 Days', items: groups.previous7Days },
      { label: 'Previous 30 Days', items: groups.previous30Days },
      { label: 'Older', items: groups.older },
    ].filter(g => g.items.length > 0);
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
                          <span className="copilot-history-item-title">
                            {(session.title || 'Untitled Conversation').replace(/^\[.*?\]\s*/, '')}
                          </span>

                          {/* 3-Dots Action Button & Dropdown Menu */}
                          <div
                            className={`copilot-history-item-actions ${isMenuOpen ? 'copilot-history-item-actions-visible' : ''}`}
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
                            >
                              <MoreHorizontal size={14} />
                            </button>

                            {/* Floating Dropdown Menu */}
                            {isMenuOpen && (
                              <div className="copilot-history-dropdown-menu">
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

                      {/* Clean Natural Prose Response - NO extra background, NO ai slop cards */}
                      <RichAnswerContent
                        content={msg.content}
                        onCitationClick={(srcNum) => handleCitationClick(msg.id, srcNum)}
                      />

                      {/* Clean subtle Sources row if citations exist */}
                      {citations.length > 0 && (() => {
                        // Deduplicate citations by clean title so we don't display repetitive rows
                        const seenTitles = new Set();
                        const displayCitations = [];
                        citations.forEach((c, ci) => {
                          const srcIdx = c.source_index || ci + 1;
                          const rawTitle = c.source_title || 'Enterprise Policy';
                          const cleanTitle = rawTitle
                            .replace(/^Slack Thread:\s*#?/i, '#')
                            .replace(/\.pdf\].*$/i, '.pdf]')
                            .replace(/\s*\(\d+\.\d+\)$/, '');
                          const key = `${c.document_id || ''}-${cleanTitle}`;
                          if (!seenTitles.has(key)) {
                            seenTitles.add(key);
                            displayCitations.push({ ...c, srcIdx, cleanTitle });
                          }
                        });

                        return (
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            flexWrap: 'wrap',
                            marginTop: '12px',
                            paddingTop: '6px',
                            fontSize: '0.74rem',
                            color: '#78716C'
                          }}>
                            <span style={{ fontWeight: 600, color: '#57534E' }}>Sources:</span>
                            {displayCitations.map((c, ci) => (
                              <a
                                key={ci}
                                href={`/vault?workspace=${activeWorkspace?.id || 'all'}&doc=${c.document_id || ''}&claimId=${c.claim_id || ''}&section=claims`}
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  fontSize: '0.72rem',
                                  fontWeight: 500,
                                  padding: '2px 8px',
                                  borderRadius: '10px',
                                  background: '#F5F5F4',
                                  color: '#44403C',
                                  textDecoration: 'none',
                                  transition: 'all 0.15s ease'
                                }}
                                onMouseEnter={e => {
                                  e.currentTarget.style.background = '#E7E5E4';
                                  e.currentTarget.style.color = '#1C1917';
                                }}
                                onMouseLeave={e => {
                                  e.currentTarget.style.background = '#F5F5F4';
                                  e.currentTarget.style.color = '#44403C';
                                }}
                                title={`Open ${c.source_title} in Knowledge Vault`}
                              >
                                <span style={{ color: '#D97706', fontWeight: 700 }}>[{c.srcIdx}]</span>
                                <span>{c.cleanTitle}</span>
                                <ExternalLink size={10} color="#A8A29E" />
                              </a>
                            ))}
                          </div>
                        );
                      })()}

                      {/* Conflict Warnings & HITL Escalation Alert */}
                      {(warnings.length > 0 || meta.answer_status === 'DISPUTED') && (
                        <div style={{
                          marginTop: '10px',
                          background: 'rgba(239, 68, 68, 0.06)',
                          border: '1px solid rgba(239, 68, 68, 0.2)',
                          borderRadius: '10px',
                          padding: '10px 14px',
                          fontSize: '0.78rem',
                          color: '#991B1B'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                            <div style={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <AlertTriangle size={14} color="#DC2626" />
                              <span>Contradiction & Policy Dispute Alert</span>
                            </div>
                            <button
                              type="button"
                              onClick={() => {
                                if (onOpenHitlModal) onOpenHitlModal();
                                else window.dispatchEvent(new CustomEvent('open-hitl-modal', { detail: { messageId: msg.id } }));
                                if (showToast) showToast('Escalated question to Human Data Steward review queue.');
                              }}
                              style={{
                                background: '#DC2626',
                                color: '#FFFFFF',
                                border: 'none',
                                borderRadius: '6px',
                                padding: '3px 9px',
                                fontSize: '0.70rem',
                                fontWeight: 700,
                                cursor: 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px'
                              }}
                              title="Escalate this dispute directly to human data steward queue"
                            >
                              <ShieldAlert size={12} color="#FFFFFF" />
                              <span>Escalate to Data Steward</span>
                            </button>
                          </div>
                          {warnings.map((w, wi) => (
                            <div key={wi} style={{ lineHeight: 1.4, marginTop: '4px' }}>{w}</div>
                          ))}
                        </div>
                      )}

                      {/* Minimal Bottom Action Row: Copy button and optional decision badge */}
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        marginTop: '10px',
                        fontSize: '0.74rem',
                        color: '#78716C'
                      }}>
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard.writeText(msg.content);
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

                        {decision && (
                          <span style={{
                            fontSize: '0.70rem',
                            fontWeight: 600,
                            color: decision === 'ALLOW' ? '#15803D' : '#B91C1C',
                            background: decision === 'ALLOW' ? '#DCFCE7' : '#FEE2E2',
                            padding: '2px 8px',
                            borderRadius: '8px'
                          }}>
                            {decision === 'ALLOW' ? '✓ Allowed' : '✕ Blocked'}
                          </span>
                        )}
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
    </div>
  );
}

