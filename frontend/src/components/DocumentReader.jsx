import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { ChevronDown, FileText } from 'lucide-react';
import './DocumentReader.css';

const PAGE_WEIGHT_BUDGET = 2600;
const BASE_PAGE_WIDTH = 740;

function parseBlocks(rawText, joinWrappedLines = false) {
  if (!rawText) return [];
  const text = joinWrappedLines
    ? rawText.replace(/([^\n])\n(?!\n|#{1,6}\s|[-*+]\s|\d+\.\s|```|>|\|)/g, '$1 ')
    : rawText;

  const lines = text.split('\n');
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      i++;
      continue;
    }

    // Explicit page break marker
    if (/^##\s*page\s+\d+\s*$/i.test(trimmed)) {
      blocks.push({ type: 'page_break' });
      i++;
      continue;
    }

    // Fenced code block
    if (trimmed.startsWith('```')) {
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      if (i < lines.length) i++;
      blocks.push({ type: 'code', content: codeLines.join('\n'), weight: Math.max(180, codeLines.join('\n').length) });
      continue;
    }

    // Horizontal rule
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      blocks.push({ type: 'hr', weight: 40 });
      i++;
      continue;
    }

    // Headings
    const hMatch = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (hMatch) {
      blocks.push({ type: 'heading', level: hMatch[1].length, text: hMatch[2].trim(), weight: 120 });
      i++;
      continue;
    }

    // Blockquote
    if (trimmed.startsWith('>')) {
      const qLines = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        qLines.push(lines[i].trim().replace(/^>\s?/, ''));
        i++;
      }
      const qText = qLines.join(' ');
      blocks.push({ type: 'blockquote', text: qText, weight: Math.max(100, qText.length) });
      continue;
    }

    // Markdown table
    if (trimmed.startsWith('|') && i + 1 < lines.length && /^\|?[\s:-]+\|/.test(lines[i + 1].trim())) {
      const parseRow = (rowStr) =>
        rowStr.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
      const headers = parseRow(trimmed);
      const aligns = parseRow(lines[i + 1]).map((sep) => {
        if (sep.startsWith(':') && sep.endsWith(':')) return 'center';
        if (sep.endsWith(':')) return 'right';
        return 'left';
      });
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        rows.push(parseRow(lines[i]));
        i++;
      }
      blocks.push({ type: 'table', headers, aligns, rows, weight: 160 + rows.length * 90 });
      continue;
    }

    // Lists (unordered & ordered)
    if (/^([-*+]\s|\d+\.\s)/.test(trimmed)) {
      const ordered = /^\d+\.\s/.test(trimmed);
      const startMatch = trimmed.match(/^(\d+)\./);
      const start = startMatch ? Number(startMatch[1]) : 1;
      const items = [];
      while (i < lines.length && /^(\s*[-*+]\s|\s*\d+\.\s)/.test(lines[i])) {
        const cur = lines[i].trim();
        items.push(cur.replace(/^([-*+]|\d+\.)\s+/, ''));
        i++;
      }
      blocks.push({ type: 'list', ordered, start, items, weight: 80 + items.join(' ').length });
      continue;
    }

    // Paragraph
    const pLines = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^(#{1,3}\s|```|>|[-*+]\s|\d+\.\s|\|)/.test(lines[i].trim())
    ) {
      pLines.push(lines[i].trim());
      i++;
    }
    const pText = pLines.join(' ');
    blocks.push({ type: 'paragraph', text: pText, weight: Math.max(70, pText.length) });
  }

  return blocks;
}

function paginateBlocks(blocks) {
  if (!blocks.length) return [];
  const pages = [];
  let current = [];
  let weight = 0;

  for (let idx = 0; idx < blocks.length; idx++) {
    const blk = blocks[idx];
    if (blk.type === 'page_break') {
      const onlyTopTitle = pages.length === 0 && current.length === 1 && current[0].type === 'heading' && current[0].level === 1;
      if (current.length > 0 && !onlyTopTitle) {
        pages.push(current);
        current = [];
        weight = 0;
      }
      continue;
    }

    const nextWeight = weight + blk.weight;
    const isOrphanHeading = blk.type === 'heading' && idx + 1 < blocks.length && nextWeight + blocks[idx + 1].weight > PAGE_WEIGHT_BUDGET;
    if ((nextWeight > PAGE_WEIGHT_BUDGET || isOrphanHeading) && current.length > 0) {
      pages.push(current);
      current = [blk];
      weight = blk.weight;
    } else {
      current.push(blk);
      weight = nextWeight;
    }
  }
  if (current.length > 0) pages.push(current);
  return pages;
}

function renderInline(text) {
  if (!text) return null;
  const parts = String(text).split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g);
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={idx}>{part.slice(2, -2)}</strong>;
    if (part.startsWith('*') && part.endsWith('*')) return <em key={idx}>{part.slice(1, -1)}</em>;
    if (part.startsWith('`') && part.endsWith('`')) return <code key={idx}>{part.slice(1, -1)}</code>;
    const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      return (
        <a key={idx} href={linkMatch[2]} target="_blank" rel="noopener noreferrer">
          {linkMatch[1]}
        </a>
      );
    }
    return part;
  });
}

function stripMarkdown(text) {
  return String(text || '')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
}

export default function DocumentReader({
  title,
  content,
  loading = false,
  fileHref,
  joinWrappedLines = false,
}) {
  const [activePage, setActivePage] = useState(1);
  const [pageInput, setPageInput] = useState('1');
  const [zoomMode, setZoomMode] = useState('fit'); // 'fit' | number
  const [fitScale, setFitScale] = useState(1);
  const [exportOpen, setExportOpen] = useState(false);

  const canvasRef = useRef(null);
  const exportRef = useRef(null);
  const pageRefs = useRef([]);

  const pages = useMemo(() => paginateBlocks(parseBlocks(content, joinWrappedLines)), [content, joinWrappedLines]);
  const scale = zoomMode === 'fit' ? fitScale : zoomMode / 100;
  const safeTitle = (title || 'document').replace(/[^a-zA-Z0-9._-]+/g, '_');

  // Fit-to-width observer
  useEffect(() => {
    const el = canvasRef.current;
    if (!el) return;
    const updateFit = () => {
      const avail = Math.max(320, el.clientWidth - 44);
      setFitScale(Math.min(1.1, Math.max(0.55, avail / BASE_PAGE_WIDTH)));
    };
    updateFit();
    const ro = new ResizeObserver(updateFit);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Scroll-spy for active page
  useEffect(() => {
    const el = canvasRef.current;
    if (!el || pages.length === 0) return;
    const onScroll = () => {
      const mid = el.scrollTop + el.clientHeight * 0.35;
      let found = 1;
      for (let i = 0; i < pageRefs.current.length; i++) {
        const node = pageRefs.current[i];
        if (node && node.offsetTop <= mid) found = i + 1;
      }
      setActivePage(found);
      setPageInput(String(found));
    };
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, [pages.length]);

  // Close export menu on outside click or Escape
  useEffect(() => {
    if (!exportOpen) return;
    const onDown = (e) => {
      if (exportRef.current && !exportRef.current.contains(e.target)) setExportOpen(false);
    };
    const onKey = (e) => {
      if (e.key === 'Escape') setExportOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [exportOpen]);

  const applyZoom = useCallback((nextZoom) => {
    const el = canvasRef.current;
    const ratio = el && el.scrollHeight > 0 ? el.scrollTop / el.scrollHeight : 0;
    setZoomMode(nextZoom);
    requestAnimationFrame(() => {
      if (el && ratio > 0) el.scrollTop = ratio * el.scrollHeight;
    });
  }, []);

  // Keyboard zoom shortcuts (+, -, 0) ignoring inputs
  useEffect(() => {
    const onKey = (e) => {
      const tag = document.activeElement?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || document.activeElement?.isContentEditable) return;
      const curPct = Math.round((zoomMode === 'fit' ? fitScale : zoomMode / 100) * 100);
      if (e.key === '=' || e.key === '+') {
        e.preventDefault();
        applyZoom(Math.min(150, curPct + 10));
      } else if (e.key === '-') {
        e.preventDefault();
        applyZoom(Math.max(60, curPct - 10));
      } else if (e.key === '0') {
        e.preventDefault();
        applyZoom('fit');
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [zoomMode, fitScale, applyZoom]);

  const jumpToPage = (num) => {
    const target = Math.max(1, Math.min(pages.length, num));
    setActivePage(target);
    setPageInput(String(target));
    pageRefs.current[target - 1]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const downloadText = (ext, mime, raw) => {
    const blob = new Blob([raw], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${safeTitle}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(stripMarkdown(content));
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard unavailable
    }
  };

  const displayPct = Math.round(scale * 100);

  return (
    <div className="trulin-doc-reader">
      {/* Toolbar */}
      <div className="trulin-dv-toolbar">
        <div className="trulin-dv-toolbar-group">
          {pages.length > 0 && (
            <>
              <span>Page</span>
              <input
                type="text"
                aria-label="Current page number"
                className="trulin-dv-page-input"
                value={pageInput}
                onChange={(e) => setPageInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const n = parseInt(pageInput, 10);
                    if (!Number.isNaN(n)) jumpToPage(n);
                  }
                }}
                onBlur={() => {
                  const n = parseInt(pageInput, 10);
                  if (!Number.isNaN(n)) jumpToPage(n);
                  else setPageInput(String(activePage));
                }}
              />
              <span>of {pages.length}</span>
              <span style={{ color: '#CBD5E1' }}>|</span>
              <button
                type="button"
                aria-label="Zoom out"
                className="trulin-dv-btn trulin-dv-btn-icon"
                onClick={() => applyZoom(Math.max(60, displayPct - 10))}
              >
                -
              </button>
              <span style={{ minWidth: '38px', textAlign: 'center', fontWeight: 700, color: '#0F172A' }}>
                {displayPct}%
              </span>
              <button
                type="button"
                aria-label="Zoom in"
                className="trulin-dv-btn trulin-dv-btn-icon"
                onClick={() => applyZoom(Math.min(150, displayPct + 10))}
              >
                +
              </button>
              <button
                type="button"
                className="trulin-dv-btn"
                onClick={() => applyZoom('fit')}
                style={zoomMode === 'fit' ? { background: '#FFF7ED', borderColor: '#FDBA74', color: '#C2410C' } : undefined}
              >
                Fit
              </button>
            </>
          )}
        </div>

        <div className="trulin-dv-toolbar-group">
          <div ref={exportRef} style={{ position: 'relative' }}>
            <button
              type="button"
              className="trulin-dv-btn"
              aria-expanded={exportOpen}
              onClick={() => setExportOpen((o) => !o)}
            >
              <span>Export</span>
              <ChevronDown size={13} />
            </button>
            {exportOpen && (
              <div className="trulin-dv-export-menu">
                {fileHref && (
                  <a
                    href={fileHref}
                    download={`${safeTitle}.pdf`}
                    className="trulin-dv-export-item"
                    onClick={() => setExportOpen(false)}
                  >
                    Download PDF (.pdf)
                  </a>
                )}
                {content && (
                  <>
                    <button
                      type="button"
                      className="trulin-dv-export-item"
                      onClick={() => {
                        downloadText('md', 'text/markdown;charset=utf-8', content);
                        setExportOpen(false);
                      }}
                    >
                      Export Markdown (.md)
                    </button>
                    <button
                      type="button"
                      className="trulin-dv-export-item"
                      onClick={() => {
                        downloadText('txt', 'text/plain;charset=utf-8', stripMarkdown(content));
                        setExportOpen(false);
                      }}
                    >
                      Export Plain Text (.txt)
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Body: Left Structural Thumbnails + Main Pages */}
      <div className="trulin-dv-body">
        {!loading && pages.length > 0 && (
          <div className="trulin-dv-rail" aria-label="Page thumbnails">
            {pages.map((pageBlocks, idx) => {
              const pNum = idx + 1;
              return (
                <button
                  key={`thumb-${pNum}`}
                  type="button"
                  className={`trulin-dv-thumb-btn ${activePage === pNum ? 'is-active' : ''}`}
                  onClick={() => jumpToPage(pNum)}
                >
                  <div className="trulin-dv-thumb-sheet">
                    <div className="trulin-dv-thumb-mini">
                      {idx === 0 && pageBlocks[0]?.type !== 'heading' && <h1>{title}</h1>}
                      {pageBlocks.slice(0, 8).map((b, bi) => {
                        if (b.type === 'heading') return <h2 key={bi}>{b.text}</h2>;
                        if (b.type === 'paragraph') return <p key={bi}>{b.text}</p>;
                        if (b.type === 'list') return <p key={bi}>{b.items.slice(0, 3).join(' • ')}</p>;
                        if (b.type === 'table') return <p key={bi}>{b.headers.join(' | ')}</p>;
                        return null;
                      })}
                    </div>
                  </div>
                  <span className="trulin-dv-thumb-num">{pNum}</span>
                </button>
              );
            })}
          </div>
        )}

        <div ref={canvasRef} className="trulin-dv-canvas">
          {loading ? (
            <div className="trulin-dv-sheet" style={{ gap: '12px' }}>
              <div style={{ height: '18px', width: '55%', background: '#E2E8F0', borderRadius: '4px' }} />
              <div style={{ height: '10px', width: '92%', background: '#F1F5F9', borderRadius: '4px' }} />
              <div style={{ height: '10px', width: '88%', background: '#F1F5F9', borderRadius: '4px' }} />
              <div style={{ height: '10px', width: '76%', background: '#F1F5F9', borderRadius: '4px' }} />
            </div>
          ) : pages.length === 0 ? (
            <div style={{ padding: '44px 24px', textAlign: 'center', color: '#64748B', background: '#FFFFFF', borderRadius: '8px', border: '1px solid #E2E8F0', maxWidth: '460px', width: '100%' }}>
              <FileText size={26} color="#94A3B8" style={{ margin: '0 auto 8px auto', display: 'block' }} />
              <div style={{ fontWeight: 700, color: '#0F172A', marginBottom: '4px' }}>No readable content</div>
              <div style={{ fontSize: '0.78rem' }}>Use Export to download the original file if available.</div>
            </div>
          ) : (
            pages.map((pageBlocks, pageIdx) => (
              <div
                key={`page-${pageIdx}`}
                ref={(el) => { pageRefs.current[pageIdx] = el; }}
                className="trulin-dv-page-wrap"
                style={{ width: `${Math.round(BASE_PAGE_WIDTH * scale)}px` }}
              >
                <div
                  className="trulin-dv-sheet"
                  style={{
                    transform: scale !== 1 ? `scale(${scale})` : 'none',
                  }}
                >
                  <div>
                    {pageIdx === 0 && pageBlocks[0]?.type !== 'heading' && (
                      <h1 className="trulin-dv-doc-title">{title}</h1>
                    )}
                    {pageBlocks.map((b, bi) => {
                      if (b.type === 'heading') {
                        const Tag = b.level === 1 ? 'h1' : b.level === 2 ? 'h2' : 'h3';
                        return <Tag key={bi}>{renderInline(b.text)}</Tag>;
                      }
                      if (b.type === 'paragraph') return <p key={bi}>{renderInline(b.text)}</p>;
                      if (b.type === 'blockquote') return <blockquote key={bi}>{renderInline(b.text)}</blockquote>;
                      if (b.type === 'hr') return <hr key={bi} />;
                      if (b.type === 'code') return <pre key={bi}><code>{b.content}</code></pre>;
                      if (b.type === 'list') {
                        const ListTag = b.ordered ? 'ol' : 'ul';
                        return (
                          <ListTag key={bi} start={b.ordered ? b.start : undefined}>
                            {b.items.map((item, ii) => <li key={ii}>{renderInline(item)}</li>)}
                          </ListTag>
                        );
                      }
                      if (b.type === 'table') {
                        return (
                          <table key={bi}>
                            <thead>
                              <tr>
                                {b.headers.map((h, hi) => (
                                  <th key={hi} style={{ textAlign: b.aligns[hi] || 'left' }}>{renderInline(h)}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {b.rows.map((row, ri) => (
                                <tr key={ri}>
                                  {row.map((cell, ci) => (
                                    <td key={ci} style={{ textAlign: b.aligns[ci] || 'left' }}>{renderInline(cell)}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        );
                      }
                      return null;
                    })}
                  </div>
                  <div className="trulin-dv-footer">
                    <span>{title}</span>
                    <span>Page {pageIdx + 1} of {pages.length}</span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
