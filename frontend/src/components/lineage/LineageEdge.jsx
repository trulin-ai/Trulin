import React from 'react';
import { CARD_WIDTH, CARD_HEIGHT } from './lineageLayout';

const EDGE_STYLES = {
  provenance: { stroke: '#94A3B8', dash: undefined, width: 1.5 },
  extraction: { stroke: '#2563EB', dash: undefined, width: 1.75 },
  decision_grounding: { stroke: '#0D9488', dash: undefined, width: 1.75 },
  conflict: { stroke: '#EA580C', dash: '6 4', width: 1.75 },
  inferred_grounding: { stroke: '#64748B', dash: '2 4', width: 1.5 },
};

export default function LineageEdge({ edge, sourcePos, targetPos, isHighlighted, isDimmed }) {
  if (!sourcePos || !targetPos) return null;

  const x1 = sourcePos.x + CARD_WIDTH;
  const y1 = sourcePos.y + CARD_HEIGHT / 2;
  const x2 = targetPos.x;
  const y2 = targetPos.y + CARD_HEIGHT / 2;
  const dx = Math.max(40, Math.abs(x2 - x1) * 0.45);
  const d = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;

  const style = EDGE_STYLES[edge.type] || EDGE_STYLES.provenance;
  const opacity = isDimmed ? 0.18 : isHighlighted ? 1 : 0.72;

  return (
    <g style={{ opacity }}>
      <path
        d={d}
        fill="none"
        stroke={isHighlighted ? '#EA580C' : style.stroke}
        strokeWidth={isHighlighted ? style.width + 0.8 : style.width}
        strokeDasharray={style.dash}
      />
      {edge.inferred && (
        <text
          x={(x1 + x2) / 2}
          y={(y1 + y2) / 2 - 6}
          textAnchor="middle"
          fontSize="10"
          fill="#64748B"
          fontWeight="600"
        >
          inferred
        </text>
      )}
    </g>
  );
}
