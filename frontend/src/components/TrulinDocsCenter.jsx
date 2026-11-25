import React, { useState, useEffect, useMemo } from 'react';
import {
  BookOpen,
  Search,
  ChevronRight,
  ChevronDown,
  Copy,
  Check,
  ExternalLink,
  Info,
  AlertTriangle,
  Lightbulb,
  ArrowLeft,
  ArrowRight,
  Terminal,
  Database
} from 'lucide-react';
import { DOCS_CATEGORIES } from '../data/docsContent';

export default function TrulinDocsCenter({ initialArticleId = 'welcome', onNavigate }) {
  const [selectedId, setSelectedId] = useState(initialArticleId || 'welcome');
  const [searchQuery, setSearchQuery] = useState('');
  const [collapsedCats, setCollapsedCats] = useState({});
  const [copiedKey, setCopiedKey] = useState(null);
  const [liveTools, setLiveTools] = useState([]);
  const [liveResources, setLiveResources] = useState([]);

  useEffect(() => {
    if (initialArticleId) setSelectedId(initialArticleId);
  }, [initialArticleId]);

  const flatArticles = useMemo(() => {
    const list = [];
    DOCS_CATEGORIES.forEach((cat) => {
      cat.articles.forEach((art) => {
        list.push({ ...art, categoryId: cat.id, categoryLabel: cat.label });
      });
    });
    return list;
  }, []);

  const currentIndex = flatArticles.findIndex((a) => a.id === selectedId);
  const currentArticle = flatArticles[currentIndex >= 0 ? currentIndex : 0];
  const prevArticle = currentIndex > 0 ? flatArticles[currentIndex - 1] : null;
  const nextArticle = currentIndex >= 0 && currentIndex < flatArticles.length - 1 ? flatArticles[currentIndex + 1] : null;

  useEffect(() => {
    if (!currentArticle?.renderLiveMcpSchema) return;
    let cancelled = false;
    Promise.all([
      fetch('/v1/mcp/tools').then((r) => (r.ok ? r.json() : { tools: [] })),
      fetch('/v1/mcp/resources').then((r) => (r.ok ? r.json() : { resources: [] }))
    ])
      .then(([tData, rData]) => {
        if (!cancelled) {
          setLiveTools(tData.tools || []);
          setLiveResources(rData.resources || []);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [currentArticle?.renderLiveMcpSchema]);

  const filteredCategories = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return DOCS_CATEGORIES;
    return DOCS_CATEGORIES.map((cat) => ({
      ...cat,
      articles: cat.articles.filter(
        (a) =>
          a.title.toLowerCase().includes(q) ||
          a.summary.toLowerCase().includes(q) ||
          a.sections.some(
            (s) =>
              s.heading.toLowerCase().includes(q) ||
              s.body.some((p) => p.toLowerCase().includes(q))
          )
      )
    })).filter((cat) => cat.articles.length > 0);
  }, [searchQuery]);

  const handleCopy = (key, text) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 1800);
  };

  const scrollToSection = (secId) => {
    const el = document.getElementById(`docs-sec-${secId}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const renderCallout = (callout) => {
    const styles = {
      info: { bg: '#EFF6FF', border: '#BFDBFE', title: '#1E40AF', icon: <Info size={16} color="#2563EB" /> },
      warning: { bg: '#FFF7ED', border: '#FED7AA', title: '#9A3412', icon: <AlertTriangle size={16} color="#EA580C" /> },
      tip: { bg: '#F0FDF4', border: '#BBF7D0', title: '#166534', icon: <Lightbulb size={16} color="#16A34A" /> }
    };
    const st = styles[callout.type] || styles.info;
    return (
      <div
        style={{
          background: st.bg,
          border: `1px solid ${st.border}`,
          borderRadius: '10px',
          padding: '14px 16px',
          marginTop: '14px',
          display: 'flex',
          gap: '12px',
          alignItems: 'flex-start'
        }}
      >
        <div style={{ marginTop: '2px', flexShrink: 0 }}>{st.icon}</div>
        <div>
          <div style={{ fontSize: '0.82rem', fontWeight: 700, color: st.title, marginBottom: '4px' }}>
            {callout.title}
          </div>
          <div style={{ fontSize: '0.82rem', color: '#334155', lineHeight: 1.55 }}>{callout.text}</div>
        </div>
      </div>
    );
  };

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '250px minmax(0, 1fr) 200px',
        gap: '24px',
        alignItems: 'start',
        width: '100%',
        maxWidth: '1320px',
        margin: '0 auto',
        paddingBottom: '40px'
      }}
    >
      {/* LEFT RAIL: Search + Categorized Navigation Tree */}
      <aside
        style={{
          position: 'sticky',
          top: '16px',
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '12px',
          padding: '14px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingBottom: '8px', borderBottom: '1px solid #F1F5F9' }}>
          <BookOpen size={16} color="#EA580C" />
          <span style={{ fontSize: '0.84rem', fontWeight: 700, color: '#0F172A' }}>Trulin Docs</span>
        </div>

        <div style={{ position: 'relative' }}>
          <Search size={14} color="#94A3B8" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search guides & API..."
            style={{
              width: '100%',
              padding: '7px 10px 7px 30px',
              fontSize: '0.78rem',
              borderRadius: '8px',
              border: '1px solid #E2E8F0',
              background: '#F8FAFC',
              color: '#0F172A',
              outline: 'none'
            }}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {filteredCategories.map((cat) => {
            const isCollapsed = !!collapsedCats[cat.id] && !searchQuery;
            return (
              <div key={cat.id}>
                <button
                  type="button"
                  onClick={() => setCollapsedCats((prev) => ({ ...prev, [cat.id]: !prev[cat.id] }))}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    background: 'transparent',
                    border: 'none',
                    padding: '4px 4px',
                    fontSize: '0.68rem',
                    fontWeight: 800,
                    letterSpacing: '0.06em',
                    textTransform: 'uppercase',
                    color: '#64748B',
                    cursor: 'pointer'
                  }}
                >
                  <span>{cat.label}</span>
                  {isCollapsed ? <ChevronRight size={13} /> : <ChevronDown size={13} />}
                </button>

                {!isCollapsed && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '4px' }}>
                    {cat.articles.map((art) => {
                      const active = art.id === currentArticle.id;
                      return (
                        <button
                          key={art.id}
                          type="button"
                          onClick={() => setSelectedId(art.id)}
                          style={{
                            textAlign: 'left',
                            padding: '6px 10px',
                            borderRadius: '7px',
                            border: 'none',
                            background: active ? '#FFF7ED' : 'transparent',
                            color: active ? '#C2410C' : '#475569',
                            fontWeight: active ? 700 : 500,
                            fontSize: '0.79rem',
                            cursor: 'pointer',
                            borderLeft: active ? '2px solid #EA580C' : '2px solid transparent'
                          }}
                        >
                          {art.title}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </aside>

      {/* CENTER CANVAS: Article Reading Pane */}
      <article
        style={{
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '14px',
          padding: '28px 34px',
          minWidth: 0
        }}
      >
        {/* Breadcrumbs + Deep-Link Action */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: '#64748B' }}>
            <span>Docs</span>
            <ChevronRight size={13} />
            <span>{currentArticle.categoryLabel}</span>
            <ChevronRight size={13} />
            <span style={{ color: '#0F172A', fontWeight: 600 }}>{currentArticle.title}</span>
          </div>

          {currentArticle.deepLink && onNavigate && (
            <button
              type="button"
              onClick={() => onNavigate(currentArticle.deepLink.tab, currentArticle.deepLink.subView)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: '8px',
                border: '1px solid #FED7AA',
                background: '#FFF7ED',
                color: '#C2410C',
                fontSize: '0.76rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <span>{currentArticle.deepLink.label}</span>
              <ExternalLink size={13} />
            </button>
          )}
        </div>

        <h1 style={{ fontSize: '1.65rem', fontWeight: 800, color: '#0F172A', margin: '0 0 8px 0', letterSpacing: '-0.02em' }}>
          {currentArticle.title}
        </h1>
        <p style={{ fontSize: '0.94rem', color: '#475569', lineHeight: 1.6, margin: '0 0 10px 0' }}>
          {currentArticle.summary}
        </p>
        <div style={{ fontSize: '0.72rem', color: '#94A3B8', fontWeight: 600, paddingBottom: '18px', borderBottom: '1px solid #F1F5F9' }}>
          {currentArticle.readTime}
        </div>

        {/* Article Sections */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '26px', marginTop: '22px' }}>
          {currentArticle.sections.map((sec) => (
            <section key={sec.id} id={`docs-sec-${sec.id}`}>
              <h2 style={{ fontSize: '1.12rem', fontWeight: 700, color: '#0F172A', margin: '0 0 10px 0' }}>
                {sec.heading}
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {sec.body.map((para, idx) => (
                  <p key={idx} style={{ fontSize: '0.88rem', color: '#334155', lineHeight: 1.68, margin: 0 }}>
                    {para}
                  </p>
                ))}
              </div>
              {sec.callout && renderCallout(sec.callout)}
              {sec.code && (
                <div style={{ marginTop: '14px', borderRadius: '10px', overflow: 'hidden', border: '1px solid #1E293B', background: '#0F172A' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 14px', background: '#1E293B', color: '#CBD5E1', fontSize: '0.74rem', fontWeight: 600 }}>
                    <span>{sec.code.label}</span>
                    <button
                      type="button"
                      onClick={() => handleCopy(`${currentArticle.id}-${sec.id}`, sec.code.snippet)}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        background: 'transparent',
                        border: 'none',
                        color: '#E2E8F0',
                        cursor: 'pointer',
                        fontSize: '0.72rem'
                      }}
                    >
                      {copiedKey === `${currentArticle.id}-${sec.id}` ? <Check size={13} color="#4ADE80" /> : <Copy size={13} />}
                      <span>{copiedKey === `${currentArticle.id}-${sec.id}` ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                  <pre style={{ margin: 0, padding: '14px', color: '#E2E8F0', fontSize: '0.78rem', lineHeight: 1.55, overflowX: 'auto', fontFamily: 'monospace' }}>
                    {sec.code.snippet}
                  </pre>
                </div>
              )}
            </section>
          ))}

          {/* Live MCP Tool & Resource Schemas (when viewing Reference) */}
          {currentArticle.renderLiveMcpSchema && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px', marginTop: '6px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.86rem', fontWeight: 700, color: '#0F172A' }}>
                  <Terminal size={15} color="#EA580C" />
                  <span>Live Registered Tools ({liveTools.length})</span>
                </div>
                {liveTools.map((tool) => (
                  <div key={tool.name} style={{ border: '1px solid #E2E8F0', borderRadius: '10px', padding: '12px 14px', background: '#F8FAFC' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                      <code style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0F172A' }}>{tool.name}</code>
                      <span style={{ fontSize: '0.68rem', fontWeight: 700, color: '#1D4ED8', background: '#DBEAFE', padding: '2px 8px', borderRadius: '999px' }}>
                        MCP Tool
                      </span>
                    </div>
                    <p style={{ fontSize: '0.8rem', color: '#475569', margin: '6px 0 8px 0', lineHeight: 1.5 }}>{tool.description}</p>
                    {tool.inputSchema?.properties && (
                      <div style={{ fontSize: '0.74rem', color: '#64748B' }}>
                        <strong>Parameters:</strong>{' '}
                        {Object.keys(tool.inputSchema.properties).map((p) => (
                          <code key={p} style={{ background: '#E2E8F0', color: '#0F172A', padding: '1px 5px', borderRadius: '4px', marginRight: '5px' }}>
                            {p}
                          </code>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.86rem', fontWeight: 700, color: '#0F172A' }}>
                  <Database size={15} color="#2563EB" />
                  <span>Live Context Resources ({liveResources.length})</span>
                </div>
                {liveResources.map((res) => (
                  <div key={res.uri} style={{ border: '1px solid #E2E8F0', borderRadius: '10px', padding: '10px 14px', background: '#F8FAFC' }}>
                    <code style={{ fontSize: '0.8rem', fontWeight: 700, color: '#1E40AF' }}>{res.uri}</code>
                    <div style={{ fontSize: '0.78rem', color: '#475569', marginTop: '4px' }}>{res.description}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Previous / Next Article Footer */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '34px', paddingTop: '20px', borderTop: '1px solid #E2E8F0' }}>
          {prevArticle ? (
            <button
              type="button"
              onClick={() => setSelectedId(prevArticle.id)}
              style={{
                textAlign: 'left',
                padding: '12px 14px',
                borderRadius: '10px',
                border: '1px solid #E2E8F0',
                background: '#F8FAFC',
                cursor: 'pointer'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.7rem', color: '#64748B', fontWeight: 600 }}>
                <ArrowLeft size={12} /> Previous
              </div>
              <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#0F172A', marginTop: '2px' }}>{prevArticle.title}</div>
            </button>
          ) : <div />}

          {nextArticle ? (
            <button
              type="button"
              onClick={() => setSelectedId(nextArticle.id)}
              style={{
                textAlign: 'right',
                padding: '12px 14px',
                borderRadius: '10px',
                border: '1px solid #E2E8F0',
                background: '#F8FAFC',
                cursor: 'pointer'
              }}
            >
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.7rem', color: '#64748B', fontWeight: 600 }}>
                Next <ArrowRight size={12} />
              </div>
              <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#0F172A', marginTop: '2px' }}>{nextArticle.title}</div>
            </button>
          ) : <div />}
        </div>
      </article>

      {/* RIGHT OUTLINE: Sticky "On This Page" */}
      <aside
        style={{
          position: 'sticky',
          top: '16px',
          padding: '8px 4px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}
      >
        <div style={{ fontSize: '0.68rem', fontWeight: 800, color: '#64748B', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          On this page
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', borderLeft: '1px solid #E2E8F0', paddingLeft: '10px' }}>
          {currentArticle.sections.map((sec) => (
            <button
              key={sec.id}
              type="button"
              onClick={() => scrollToSection(sec.id)}
              style={{
                textAlign: 'left',
                background: 'transparent',
                border: 'none',
                padding: '2px 0',
                fontSize: '0.76rem',
                color: '#475569',
                cursor: 'pointer',
                lineHeight: 1.4
              }}
            >
              {sec.heading}
            </button>
          ))}
        </div>
      </aside>
    </div>
  );
}
