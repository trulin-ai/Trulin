import React from 'react';
import { getNodeStatusMeta } from './lineageTransforms';

export default function LineageTableView({ nodes, edges, selectedNodeId, onSelectNode }) {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Entities Table */}
      <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '12px', overflow: 'hidden' }}>
        <div style={{ padding: '10px 14px', borderBottom: '1px solid #E2E8F0', background: '#F8FAFC', fontSize: '0.76rem', fontWeight: 700, color: '#0F172A' }}>
          Visible Entities ({nodes.length})
        </div>
        <div style={{ overflowX: 'auto', maxHeight: '320px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid #E2E8F0', color: '#64748B', fontSize: '0.7rem', textTransform: 'uppercase' }}>
                <th style={{ padding: '8px 12px' }}>Type</th>
                <th style={{ padding: '8px 12px' }}>Label</th>
                <th style={{ padding: '8px 12px' }}>Status</th>
                <th style={{ padding: '8px 12px' }}>Connections</th>
              </tr>
            </thead>
            <tbody>
              {nodes.map((n) => {
                const st = getNodeStatusMeta(n);
                const selected = n.id === selectedNodeId;
                const connCount = edges.filter((e) => e.source === n.id || e.target === n.id).length;
                return (
                  <tr
                    key={n.id}
                    tabIndex={0}
                    onClick={() => onSelectNode(n)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onSelectNode(n);
                      }
                    }}
                    style={{
                      borderBottom: '1px solid #F1F5F9',
                      background: selected ? '#FFF7ED' : 'transparent',
                      cursor: 'pointer',
                    }}
                  >
                    <td style={{ padding: '8px 12px', fontWeight: 700, textTransform: 'uppercase', fontSize: '0.68rem', color: '#475569' }}>{n.type}</td>
                    <td style={{ padding: '8px 12px', color: '#0F172A', fontWeight: 600 }}>{n.fullText || n.label}</td>
                    <td style={{ padding: '8px 12px' }}>
                      <span style={{ fontSize: '0.68rem', fontWeight: 700, color: st.color, background: st.bg, border: `1px solid ${st.border}`, padding: '1px 7px', borderRadius: '999px' }}>
                        {st.label}
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px', color: '#64748B' }}>{connCount}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Relationships Table */}
      <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '12px', overflow: 'hidden' }}>
        <div style={{ padding: '10px 14px', borderBottom: '1px solid #E2E8F0', background: '#F8FAFC', fontSize: '0.76rem', fontWeight: 700, color: '#0F172A' }}>
          Visible Relationships ({edges.length})
        </div>
        <div style={{ overflowX: 'auto', maxHeight: '240px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.76rem' }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid #E2E8F0', color: '#64748B', fontSize: '0.68rem', textTransform: 'uppercase' }}>
                <th style={{ padding: '8px 12px' }}>Source</th>
                <th style={{ padding: '8px 12px' }}>Relationship</th>
                <th style={{ padding: '8px 12px' }}>Target</th>
                <th style={{ padding: '8px 12px' }}>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {edges.map((e) => (
                <tr key={e.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                  <td style={{ padding: '7px 12px', color: '#0F172A' }}>{nodeMap.get(e.source)?.label || e.source}</td>
                  <td style={{ padding: '7px 12px', fontWeight: 600, color: '#475569' }}>{e.label || e.type}</td>
                  <td style={{ padding: '7px 12px', color: '#0F172A' }}>{nodeMap.get(e.target)?.label || e.target}</td>
                  <td style={{ padding: '7px 12px', color: e.inferred ? '#9A3412' : '#166534', fontWeight: 600 }}>
                    {e.inferred ? 'Inferred (legacy)' : 'Explicit'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
