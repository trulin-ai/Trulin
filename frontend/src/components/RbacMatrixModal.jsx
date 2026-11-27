import React, { useState } from 'react';
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  X,
  UserCheck,
  Lock,
  FileCheck,
  Layers,
  Database,
  Users,
  Settings,
  AlertTriangle,
  Info
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function RbacMatrixModal({ isOpen, onClose }) {
  const { user, effectiveRole, setSimulatedRole, rbacMatrix, permissions, hasPermission } = useAuth();
  const [selectedRoleFilter, setSelectedRoleFilter] = useState('all');

  if (!isOpen) return null;

  const currentRole = (user?.role || '').toLowerCase();

  // Role metadata
  const rolesList = [
    {
      key: 'admin',
      title: 'Admin / CCO',
      personaName: 'Sarah Chen',
      desc: 'Chief Compliance Officer with universal override & governance authority',
      color: '#059669',
      bg: '#ECFDF5',
      border: '#A7F3D0'
    },
    {
      key: 'data_owner',
      title: 'Data Steward',
      personaName: 'Marcus Vance',
      desc: 'Source data owner responsible for ingestion & claim extraction pipelines',
      color: '#2563EB',
      bg: '#EFF6FF',
      border: '#BFDBFE'
    },
    {
      key: 'reviewer',
      title: 'Risk Auditor',
      personaName: 'Elena Rostova',
      desc: 'Independent compliance officer adjudicating conflicts & audit trails',
      color: '#7C3AED',
      bg: '#F5F3FF',
      border: '#DDD6FE'
    },
    {
      key: 'developer',
      title: 'ML / AI Operator',
      personaName: 'Dev / Agent Service',
      desc: 'Operational agent evaluating real-time decisions and API inference',
      color: '#D97706',
      bg: '#FFFBEB',
      border: '#FDE68A'
    },
    {
      key: 'viewer',
      title: 'Observer',
      personaName: 'Read-Only Auditor',
      desc: 'Stakeholder with read-only inspection access across claims & conflicts',
      color: '#4B5563',
      bg: '#F3F4F6',
      border: '#E5E7EB'
    }
  ];

  // Permission categories definition
  const permissionCategories = [
    {
      category: 'Data Sources & Connector Ingestion',
      icon: <Database size={16} color="#2563EB" />,
      items: [
        {
          key: 'sources:read',
          name: 'Inspect Connected Sources',
          desc: 'View connected PostgreSQL, S3, and API documentation sources'
        },
        {
          key: 'sources:sync',
          name: 'Trigger Pipeline Sync',
          desc: 'Execute real-time or batch synchronization of knowledge corpora'
        },
        {
          key: 'sources:manage',
          name: 'Create & Edit Connectors',
          desc: 'Provision new credentials, modify schemas, or drop sources'
        }
      ]
    },
    {
      category: 'Claims & Knowledge Normalization',
      icon: <Layers size={16} color="#059669" />,
      items: [
        {
          key: 'claims:read',
          name: 'Read Extracted Claims',
          desc: 'Browse claim registry, semantic embeddings, and confidence scores'
        },
        {
          key: 'claims:extract',
          name: 'Run Extraction Pipeline',
          desc: 'Trigger LLM entity extraction and fact-triangulation workflows'
        },
        {
          key: 'claims:edit',
          name: 'Edit & Curate Claims',
          desc: 'Modify canonical claim definitions, dates, and trust weights'
        },
        {
          key: 'claims:delete',
          name: 'Delete Obsolete Claims',
          desc: 'Prune decommissioned policy statements and deprecated facts'
        }
      ]
    },
    {
      category: 'Conflict Adjudication & Blast Radius',
      icon: <ShieldAlert size={16} color="#DC2626" />,
      items: [
        {
          key: 'conflicts:read',
          name: 'Inspect Policy Conflicts',
          desc: 'View detected inconsistencies, blast radius scores, and severity'
        },
        {
          key: 'conflicts:resolve',
          name: 'Adjudicate & Resolve Conflicts',
          desc: 'Accept winning policy candidate, supersede stale versions, or create rule'
        },
        {
          key: 'conflicts:override',
          name: 'Emergency Policy Override',
          desc: 'Superadmin unilateral override bypassing standard committee sign-off'
        }
      ]
    },
    {
      category: 'Decision Engine & Evidence Audit',
      icon: <FileCheck size={16} color="#7C3AED" />,
      items: [
        {
          key: 'decisions:evaluate',
          name: 'Real-Time Decision Evaluation',
          desc: 'Query Context Trust Layer for runtime truth validation during LLM inference'
        },
        {
          key: 'decisions:audit',
          name: 'Inspect Evidence Audit Trails',
          desc: 'Audit tamper-evident cryptographic provenance logs and token histories'
        }
      ]
    },
    {
      category: 'Organization & Tenant Administration',
      icon: <Settings size={16} color="#4B5563" />,
      items: [
        {
          key: 'org:settings',
          name: 'Workspace Governance Settings',
          desc: 'Configure corporate domain whitelists and SSO IdP providers'
        },
        {
          key: 'org:members',
          name: 'Manage Tenant Members',
          desc: 'Assign roles, adjust clearance levels, and revoke enterprise access'
        },
        {
          key: 'org:invite',
          name: 'Issue Organization Invites',
          desc: 'Generate secure time-limited invitation links with assigned roles'
        }
      ]
    }
  ];

  // Helper to check if role has permission
  const checkRolePermission = (roleKey, permKey) => {
    if (rbacMatrix?.roles?.[roleKey]?.permissions) {
      return rbacMatrix.roles[roleKey].permissions.includes(permKey);
    }
    // Static fallback
    if (roleKey === 'admin') return true;
    if (roleKey === 'data_owner') {
      return ['sources:read', 'sources:sync', 'sources:manage', 'claims:read', 'claims:extract', 'claims:edit', 'conflicts:read', 'decisions:evaluate', 'decisions:audit'].includes(permKey);
    }
    if (roleKey === 'reviewer') {
      return ['sources:read', 'claims:read', 'conflicts:read', 'conflicts:resolve', 'decisions:evaluate', 'decisions:audit'].includes(permKey);
    }
    if (roleKey === 'developer') {
      return ['sources:read', 'claims:read', 'conflicts:read', 'decisions:evaluate'].includes(permKey);
    }
    if (roleKey === 'viewer') {
      return ['sources:read', 'claims:read', 'conflicts:read'].includes(permKey);
    }
    return false;
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(6px)',
        WebkitBackdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: '24px'
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: '#FFFFFF',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '1100px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          border: '1px solid #E2E8F0',
          overflow: 'hidden'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid #F1F5F9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'linear-gradient(to right, #F8FAFC, #FFFFFF)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '10px',
                backgroundColor: '#EFF6FF',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid #BFDBFE'
              }}
            >
              <ShieldCheck size={22} color="#2563EB" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#0F172A', margin: 0 }}>
                  Enterprise RBAC & Policy Permissions Matrix
                </h2>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: '700',
                    backgroundColor: '#EEF2FF',
                    color: '#4F46E5',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    border: '1px solid #C7D2FE'
                  }}
                >
                  PBAC / SoD Enforced
                </span>
              </div>
              <p style={{ fontSize: '13px', color: '#64748B', margin: '4px 0 0 0' }}>
                Strict Separation of Duties (SoD) enforcement across evidence ingestion, claim mutation, and conflict resolution.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              color: '#94A3B8',
              padding: '6px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.15s ease'
            }}
            title="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Current Active User Banner & Quick Persona Switcher */}
        <div
          style={{
            padding: '12px 24px',
            backgroundColor: '#F8FAFC',
            borderBottom: '1px solid #E2E8F0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                backgroundColor: '#2563EB',
                color: '#FFF',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: '700',
                fontSize: '13px'
              }}
            >
              {(user?.name || 'U')[0]}
            </div>
            <div>
              <div style={{ fontSize: '13px', fontWeight: '600', color: '#1E293B', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>{user?.name || 'Anonymous User'}</span>
                <span style={{ fontSize: '12px', color: '#64748B' }}>({user?.email || 'guest@domain.com'})</span>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: '700',
                    backgroundColor: '#EFF6FF',
                    color: '#1D4ED8',
                    padding: '1px 7px',
                    borderRadius: '6px',
                    border: '1px solid #BFDBFE'
                  }}
                >
                  {currentRole.toUpperCase()}
                </span>
              </div>
              <div style={{ fontSize: '12px', color: '#64748B' }}>
                Active Clearance: <strong>{permissions.length} of 15</strong> enterprise privileges granted
              </div>
            </div>
          </div>

          {/* Role Simulation for Testing */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '12px', fontWeight: '600', color: '#475569', marginRight: '4px' }}>
              Simulate Role:
            </span>
            {['admin', 'data_owner', 'reviewer', 'developer'].map((r) => {
              const isSelected = (effectiveRole || '').toLowerCase() === r;
              return (
                <button
                  key={r}
                  onClick={() => setSimulatedRole && setSimulatedRole(r === user?.role ? null : r)}
                  style={{
                    padding: '4px 10px',
                    fontSize: '12px',
                    fontWeight: isSelected ? '700' : '500',
                    borderRadius: '6px',
                    border: isSelected ? '1.5px solid #2563EB' : '1px solid #CBD5E1',
                    backgroundColor: isSelected ? '#EFF6FF' : '#FFFFFF',
                    color: isSelected ? '#1D4ED8' : '#475569',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                  title={`Simulate ${r} permissions`}
                >
                  {r === 'admin' ? 'Admin / CCO' : r === 'data_owner' ? 'Data Steward' : r === 'reviewer' ? 'Auditor' : 'Engineer'}
                </button>
              );
            })}
          </div>
        </div>

        {/* Separation of Duties (SoD) Policy Alert Box */}
        <div
          style={{
            margin: '16px 24px 8px 24px',
            padding: '12px 16px',
            borderRadius: '8px',
            backgroundColor: '#FEF3C7',
            border: '1px solid #FCD34D',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '12px'
          }}
        >
          <AlertTriangle size={18} color="#D97706" style={{ marginTop: '2px', flexShrink: 0 }} />
          <div style={{ fontSize: '12px', color: '#92400E', lineHeight: '1.5' }}>
            <strong>Enterprise Separation of Duties (SoD) Principle:</strong> In accordance with SOC 2 Type II and ISO 27001 compliance standards, 
            <strong> Data Stewards</strong> who own ingestion pipelines are strictly barred from resolving policy conflicts to prevent self-approving unverified facts. 
            Conversely, <strong> Risk Auditors</strong> who adjudicate conflicts cannot modify source ingestion pipelines.
          </div>
        </div>

        {/* Permissions Matrix Table Container */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '12px 24px 20px 24px'
          }}
        >
          <table
            style={{
              width: '100%',
              borderCollapse: 'separate',
              borderSpacing: 0,
              fontSize: '13px',
              textAlign: 'left'
            }}
          >
            <thead>
              <tr style={{ position: 'sticky', top: 0, zIndex: 10, backgroundColor: '#FFFFFF' }}>
                <th
                  style={{
                    padding: '10px 14px',
                    borderBottom: '2px solid #CBD5E1',
                    color: '#334155',
                    fontWeight: '700',
                    width: '38%'
                  }}
                >
                  Permission & Scope
                </th>
                {rolesList.map((r) => {
                  const isActive = r.key === currentRole;
                  return (
                    <th
                      key={r.key}
                      style={{
                        padding: '10px 10px',
                        borderBottom: '2px solid #CBD5E1',
                        textAlign: 'center',
                        backgroundColor: isActive ? '#F0FDF4' : 'transparent',
                        borderTopLeftRadius: isActive ? '8px' : '0',
                        borderTopRightRadius: isActive ? '8px' : '0',
                        borderLeft: isActive ? '2px solid #86EFAC' : 'none',
                        borderRight: isActive ? '2px solid #86EFAC' : 'none'
                      }}
                    >
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                        <span
                          style={{
                            fontSize: '12px',
                            fontWeight: '700',
                            color: r.color
                          }}
                        >
                          {r.title}
                        </span>
                        {isActive && (
                          <span
                            style={{
                              fontSize: '10px',
                              fontWeight: '700',
                              backgroundColor: '#DCFCE7',
                              color: '#15803D',
                              padding: '1px 6px',
                              borderRadius: '10px',
                              marginTop: '2px'
                            }}
                          >
                            YOU
                          </span>
                        )}
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {permissionCategories.map((cat, catIdx) => (
                <React.Fragment key={cat.category}>
                  {/* Category Header Row */}
                  <tr style={{ backgroundColor: '#F8FAFC' }}>
                    <td
                      colSpan={6}
                      style={{
                        padding: '10px 14px',
                        fontWeight: '700',
                        color: '#1E293B',
                        fontSize: '12px',
                        borderTop: catIdx > 0 ? '1px solid #E2E8F0' : 'none',
                        borderBottom: '1px solid #E2E8F0',
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {cat.icon}
                        <span>{cat.category}</span>
                      </div>
                    </td>
                  </tr>

                  {/* Category Permission Items */}
                  {cat.items.map((item, itemIdx) => {
                    const userHasIt = hasPermission(item.key);
                    return (
                      <tr
                        key={item.key}
                        style={{
                          borderBottom: '1px solid #F1F5F9',
                          transition: 'background-color 0.15s ease'
                        }}
                      >
                        {/* Scope Name & Description */}
                        <td
                          style={{
                            padding: '10px 14px',
                            borderBottom: '1px solid #F1F5F9',
                            verticalAlign: 'middle'
                          }}
                        >
                          <div style={{ fontWeight: '600', color: '#0F172A', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <code>{item.key}</code>
                          </div>
                          <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
                            {item.desc}
                          </div>
                        </td>

                        {/* Each Role's Grant Status */}
                        {rolesList.map((r) => {
                          const isGranted = checkRolePermission(r.key, item.key);
                          const isActive = r.key === currentRole;
                          
                          // Check if specifically barred by SoD
                          const isSodBarred = (
                            (r.key === 'data_owner' && item.key.startsWith('conflicts:resolve')) ||
                            (r.key === 'reviewer' && (item.key === 'sources:sync' || item.key === 'sources:manage'))
                          );

                          return (
                            <td
                              key={r.key}
                              style={{
                                padding: '10px 10px',
                                textAlign: 'center',
                                verticalAlign: 'middle',
                                borderBottom: '1px solid #F1F5F9',
                                backgroundColor: isActive ? '#F0FDF4' : 'transparent',
                                borderLeft: isActive ? '2px solid #86EFAC' : 'none',
                                borderRight: isActive ? '2px solid #86EFAC' : 'none'
                              }}
                            >
                              {isGranted ? (
                                <span
                                  style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    width: '24px',
                                    height: '24px',
                                    borderRadius: '50%',
                                    backgroundColor: '#DCFCE7',
                                    color: '#15803D'
                                  }}
                                  title="Granted"
                                >
                                  <CheckCircle2 size={16} />
                                </span>
                              ) : isSodBarred ? (
                                <span
                                  style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '4px',
                                    padding: '2px 6px',
                                    borderRadius: '4px',
                                    backgroundColor: '#FEE2E2',
                                    color: '#DC2626',
                                    fontSize: '11px',
                                    fontWeight: '600'
                                  }}
                                  title="Restricted by Separation of Duties (SoD)"
                                >
                                  <XCircle size={14} />
                                  <span>SoD</span>
                                </span>
                              ) : (
                                <span
                                  style={{
                                    color: '#CBD5E1',
                                    fontSize: '16px',
                                    fontWeight: '700'
                                  }}
                                  title="Not Granted"
                                >
                                  —
                                </span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '14px 24px',
            borderTop: '1px solid #E2E8F0',
            backgroundColor: '#F8FAFC',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#64748B', fontSize: '12px' }}>
            <Lock size={14} color="#64748B" />
            <span>Policy evaluated at runtime by Context Trust Layer PBAC engine on each API request.</span>
          </div>
          <button
            onClick={onClose}
            style={{
              padding: '8px 18px',
              backgroundColor: '#0F172A',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '8px',
              fontWeight: '600',
              fontSize: '13px',
              cursor: 'pointer'
            }}
          >
            Close Matrix
          </button>
        </div>
      </div>
    </div>
  );
}
