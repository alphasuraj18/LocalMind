import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./styles.css";

const API = "http://localhost:8000/api";
const KEY = "localmind-chats";

const Icon = ({ children, size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{children}</svg>
);

const Sparkle = ({ size }) => <Icon size={size}><path d="m12 3 1.7 5.3L19 10l-5.3 1.7L12 17l-1.7-5.3L5 10l5.3-1.7Z"/><path d="m19 17 .7 2.3L22 20l2.3.7L19 23l-.7-2.3L16 20l2.3-.7Z"/></Icon>;
const Plus = () => <Icon><path d="M12 5v14M5 12h14"/></Icon>;
const Search = () => <Icon><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></Icon>;
const Menu = () => <Icon><path d="M4 6h16M4 12h16M4 18h16"/></Icon>;
const Close = () => <Icon><path d="m6 6 12 12M18 6 6 18"/></Icon>;
const Send = () => <Icon><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></Icon>;
const Copy = () => <Icon size={14}><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></Icon>;

function Markdown({ text, sources = [], activeSource, onCitationClick }) {
  // Convert backend references such as [Source 1] into clickable inline citations.
  const citationText = (text || "").replace(
    /\[Source\s+(\d+)\]/gi,
    (match, number) => Number(number) <= sources.length
      ? `[${number}](#localmind-source-${number})`
      : match
  );

  const selectedSource = activeSource !== null && activeSource !== undefined
    ? sources[activeSource]
    : null;

  return (
    <>
      <div className="markdown">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            pre({ children }) {
              return <pre>{children}</pre>;
            },
            code({ children, className }) {
              const isBlock = /language-/.test(className || "") || String(children).includes("\n");

              return (
                <code className={isBlock ? className : "inline-code"}>
                  {children}
                </code>
              );
            },
            a({ href, children }) {
              const citation = href?.match(/^#localmind-source-(\d+)$/);

              if (citation) {
                const sourceIndex = Number(citation[1]) - 1;
                const isActive = activeSource === sourceIndex;

                return (
                  <button
                    type="button"
                    className={`inline-citation${isActive ? " active" : ""}`}
                    onClick={() => onCitationClick?.(sourceIndex)}
                    aria-label={`Show source ${sourceIndex + 1}`}
                    aria-expanded={isActive}
                  >
                    {children}
                  </button>
                );
              }

              return <a href={href} target="_blank" rel="noreferrer">{children}</a>;
            },
          }}
        >
          {citationText}
        </ReactMarkdown>
      </div>

      {selectedSource && (
        <div className="citation-detail" role="status">
          <div className="citation-detail-heading">
            <span className="citation-detail-number">[{activeSource + 1}]</span>
            <strong>{selectedSource.source || "Local document"}</strong>
            <button
              type="button"
              className="citation-detail-close"
              onClick={() => onCitationClick?.(activeSource)}
              aria-label="Close source details"
            >
              ×
            </button>
          </div>
          <div className="citation-detail-meta">
            {selectedSource.chunk ? `Chunk ${selectedSource.chunk}` : "Retrieved passage"}
            {typeof selectedSource.score === "number"
              ? ` · ${(selectedSource.score * 100).toFixed(1)}% relevance`
              : ""}
          </div>
          {selectedSource.text && (
            <p className="citation-detail-text">{selectedSource.text}</p>
          )}
        </div>
      )}
    </>
  );
}

function App() {
  const storedChats = JSON.parse(localStorage.getItem(KEY) || "[]");
  const storedActive = localStorage.getItem(`${KEY}-active`);

  const [chats, setChats] = useState(storedChats);
  const [active, setActive] = useState(storedActive);
  const [messages, setMessages] = useState(
    () => storedChats.find(c => c.id === storedActive)?.messages || []
  );

  const [input, setInput] = useState("");
  const [model, setModel] = useState("checking...");
  const [models, setModels] = useState([]);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [mobile, setMobile] = useState(false);

  const [useRag, setUseRag] = useState(false);
  const [topK, setTopK] = useState(3);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const [documentName, setDocumentName] = useState("");
  const [documentChunks, setDocumentChunks] = useState(0);
  const [documents, setDocuments] = useState([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentsError, setDocumentsError] = useState("");
  const [documentSearch, setDocumentSearch] = useState("");
  const [deletingDocument, setDeletingDocument] = useState("");
  const [showLibrary, setShowLibrary] = useState(false);
  const [expandedCitation, setExpandedCitation] = useState(null);

  const bottom = useRef(null);
  const textarea = useRef(null);
  const fileInput = useRef(null);

  useEffect(() => {
    localStorage.setItem(KEY, JSON.stringify(chats));
  }, [chats]);

  useEffect(() => {
    if (active) {
      localStorage.setItem(`${KEY}-active`, active);
    } else {
      localStorage.removeItem(`${KEY}-active`);
    }
  }, [active]);

  useEffect(() => {
    check();
    fetchDocuments();
    const t = setInterval(check, 30000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function fetchDocuments() {
    setDocumentsLoading(true);
    setDocumentsError("");

    try {
      const response = await fetch(`${API}/rag/documents`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not load documents.");
      }

      setDocuments(Array.isArray(data.documents) ? data.documents : []);
    } catch (err) {
      setDocumentsError(err.message || "Could not connect to the document library.");
    } finally {
      setDocumentsLoading(false);
    }
  }

  async function deleteDocument(filename) {
    const confirmed = window.confirm(
      `Delete "${filename}" from LocalMind? This removes its indexed chunks and uploaded file.`
    );

    if (!confirmed) return;

    setDeletingDocument(filename);
    setDocumentsError("");

    try {
      const response = await fetch(
        `${API}/rag/documents/${encodeURIComponent(filename)}`,
        { method: "DELETE" }
      );
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Document deletion failed.");
      }

      if (documentName === filename) {
        setDocumentName("");
        setDocumentChunks(0);
      }

      const remaining = documents.filter(doc => doc.filename !== filename);
      setDocuments(remaining);

      if (remaining.length === 0) {
        setUseRag(false);
      }
    } catch (err) {
      await fetchDocuments();
      setDocumentsError(err.message || "Document deletion failed.");
    } finally {
      setDeletingDocument("");
    }
  }

  async function check() {
    try {
      const [h, m] = await Promise.all([
        fetch(`${API}/health`),
        fetch(`${API}/models`)
      ]);

      const health = await h.json();
      const data = await m.json();

      setConnected(Boolean(health.ollama?.connected));
      setModel(health.configured_model || data.models?.[0] || "unknown");
      setModels(data.models || []);
    } catch {
      setConnected(false);
      setModel("offline");
      setModels([]);
    }
  }

  function newChat() {
    setShowLibrary(false);
    setActive(null);
    setMessages([]);
    setInput("");
    setMobile(false);
    setTimeout(() => textarea.current?.focus(), 50);
  }

  function save(next, chatId) {
    if (!next.length) return;

    const id = chatId || active || crypto.randomUUID();

    if (!active) {
      setActive(id);
    }

    const first = next.find(x => x.role === "user");

    const item = {
      id,
      title: first?.content.replace(/\s+/g, " ").slice(0, 42) || "New conversation",
      messages: next,
      updatedAt: Date.now()
    };

    setChats(prev => [item, ...prev.filter(x => x.id !== id)]);
  }

  async function uploadDocument(file) {
    if (!file) return;

    const allowed = [".pdf", ".docx", ".txt"];
    const extension = "." + file.name.split(".").pop().toLowerCase();

    if (!allowed.includes(extension)) {
      setUploadStatus("Unsupported file type.");
      return;
    }

    setUploading(true);
    setUploadStatus("Uploading and indexing...");
    setDocumentName("");
    setDocumentChunks(0);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API}/rag/upload`, {
        method: "POST",
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      setDocumentName(data.file);
      setDocumentChunks(data.chunks);
      setUploadStatus(
        `Ready · ${data.chunks} chunk${data.chunks === 1 ? "" : "s"} indexed`
      );
      setUseRag(true);
      await fetchDocuments();
    } catch (err) {
      setUploadStatus(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  }

  async function send(e) {
    e?.preventDefault();

    const text = input.trim();

    if (!text || loading || !connected) return;

    const chatId = active || crypto.randomUUID();
    const history = messages.map(({ role, content }) => ({ role, content }));
    const userMessages = [...messages, { role: "user", content: text }];

    setActive(chatId);
    setMessages(userMessages);
    save(userMessages, chatId);
    setInput("");
    setLoading(true);

    try {
      const r = await fetch(`${API}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          message: text,
          history,
          use_rag: useRag,
          top_k: Number(topK)
        })
      });

      const data = await r.json();

      if (!r.ok) {
        throw new Error(data.detail || "Request failed");
      }

      const next = [
        ...userMessages,
        {
          role: "assistant",
          content: data.response,
          sources: data.sources || []
        }
      ];

      setMessages(next);
      save(next, chatId);

    } catch (err) {
      const next = [
        ...userMessages,
        {
          role: "assistant",
          content: `Something went wrong: ${err.message}`
        }
      ];

      setMessages(next);
      save(next, chatId);

    } finally {
      setLoading(false);
      textarea.current?.focus();
    }
  }

  const visible = chats
    .filter(c => c.title.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => b.updatedAt - a.updatedAt);

  const visibleDocuments = documents.filter(doc =>
    (doc.filename || "").toLowerCase().includes(documentSearch.toLowerCase())
  );
  const totalChunks = documents.reduce(
    (total, doc) => total + Number(doc.chunks || 0),
    0
  );

  return (
    <div className="app">
      <aside className={`sidebar ${mobile ? "show" : ""}`}>
        <div className="brand">
          <div className="logo"><Sparkle size={20}/></div>
          <div>
            <b>LocalMind</b>
            <small>Private local AI</small>
          </div>
          <button className="close" onClick={() => setMobile(false)}>
            <Close/>
          </button>
        </div>

        <button className="new-chat" onClick={newChat}>
          <Plus/>New chat
        </button>

        <button
          className={`library-nav ${showLibrary ? "active" : ""}`}
          onClick={() => {
            setShowLibrary(true);
            setMobile(false);
            fetchDocuments();
          }}
        >
          <span>▤</span>
          Document Library
          <span className="library-count">{documents.length}</span>
        </button>

        <label className="search">
          <Search/>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search chats"
          />
        </label>

        <div className="recent">
          <span>RECENT CONVERSATIONS</span>

          {visible.length ? visible.map(c => (
            <button
              className={`chat-item ${active === c.id ? "active" : ""}`}
              key={c.id}
              onClick={() => {
                setShowLibrary(false);
                setActive(c.id);
                setMessages(c.messages);
                setMobile(false);
              }}
            >
              <span className="chat-icon">◌</span>
              {c.title}
            </button>
          )) : <p>No conversations yet.</p>}
        </div>

        <div className="sidebar-bottom">
          <div className="connection">
            <i className={connected ? "on" : ""}/>
            <div>
              <b>{connected ? "Ollama connected" : "Ollama offline"}</b>
              <small>{connected ? model : "Start your local server"}</small>
            </div>
          </div>

          <button className="settings">⚙ Settings</button>
        </div>
      </aside>

      {mobile && <button className="backdrop" onClick={() => setMobile(false)}/>} 

      <main className="main">
        <header className="topbar">
          <button className="menu" onClick={() => setMobile(true)}>
            <Menu/>
          </button>

          <div className="model">
            <span>MODEL</span>
            <select
              value={model}
              onChange={e => setModel(e.target.value)}
              disabled={!models.length}
            >
              {(models.length ? models : [model]).map(m => (
                <option key={m}>{m}</option>
              ))}
            </select>
          </div>

          <div className={`local ${connected ? "online" : ""}`}>
            <i/> {connected ? "Local" : "Offline"}
          </div>
        </header>

        <section className={`content ${showLibrary ? "library-open" : ""}`}>
          {showLibrary ? (
            <div className="library-page">
              <div className="library-heading">
                <div>
                  <div className="eyebrow">LOCAL KNOWLEDGE BASE</div>
                  <h1>Document Library</h1>
                  <p>Manage the files indexed for local retrieval.</p>
                </div>
                <button className="library-close" onClick={() => setShowLibrary(false)}>
                  Back to chat
                </button>
              </div>

              <div className="library-stats">
                <div className="library-stat">
                  <span>DOCUMENTS</span>
                  <strong>{documents.length}</strong>
                </div>
                <div className="library-stat">
                  <span>INDEXED CHUNKS</span>
                  <strong>{totalChunks}</strong>
                </div>
                <div className="library-stat">
                  <span>SUPPORTED FORMATS</span>
                  <strong>PDF · DOCX · TXT</strong>
                </div>
              </div>

              <div className="library-toolbar">
                <label className="library-search">
                  <Search/>
                  <input
                    value={documentSearch}
                    onChange={e => setDocumentSearch(e.target.value)}
                    placeholder="Search documents..."
                  />
                </label>
                <button
                  className="library-refresh"
                  onClick={fetchDocuments}
                  disabled={documentsLoading}
                >
                  {documentsLoading ? "Refreshing..." : "↻ Refresh"}
                </button>
              </div>

              {documentsError && (
                <div className="library-error" role="alert">
                  {documentsError}
                </div>
              )}

              {documentsLoading && documents.length === 0 ? (
                <div className="library-state">Loading your documents...</div>
              ) : visibleDocuments.length > 0 ? (
                <div className="document-list">
                  {visibleDocuments.map(doc => (
                    <article className="library-document" key={doc.filename}>
                      <div className="library-file-icon">▤</div>
                      <div className="library-document-info">
                        <strong title={doc.filename}>{doc.filename}</strong>
                        <span>
                          {(doc.filename || "").split(".").pop().toUpperCase()}
                          <i>·</i>
                          {doc.chunks || 0} chunks
                          {doc.embedding_dimension ? (
                            <>
                              <i>·</i>
                              {doc.embedding_dimension} dimensions
                            </>
                          ) : null}
                        </span>
                      </div>
                      <button
                        className="document-delete"
                        onClick={() => deleteDocument(doc.filename)}
                        disabled={Boolean(deletingDocument)}
                        title={`Delete ${doc.filename}`}
                      >
                        {deletingDocument === doc.filename ? "Deleting..." : "Delete"}
                      </button>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="library-empty">
                  <div>▤</div>
                  <h2>{documents.length ? "No matching documents" : "Your library is empty"}</h2>
                  <p>
                    {documents.length
                      ? "Try a different filename."
                      : "Upload a PDF, DOCX, or TXT file below the chat to index it for local retrieval."}
                  </p>
                  {documents.length > 0 && (
                    <button onClick={() => setDocumentSearch("")}>Clear search</button>
                  )}
                </div>
              )}
            </div>
          ) : !messages.length ? (
            <div className="welcome">
              <div className="hero-icon"><Sparkle size={28}/></div>
              <div className="eyebrow">LOCAL AI ASSISTANT</div>

              <h1>
                Your AI.<br/>
                <span>Running locally.</span>
              </h1>

              <p>
                Ask questions, write code, brainstorm ideas, or learn something new —
                powered by Ollama on your own machine.
              </p>

              <div className="prompts">
                {[
                  "Summarize my uploaded document",
                  "What skills are listed in my resume?",
                  "Explain this document like I am a beginner",
                  "Give me 5 project ideas"
                ].map(x => (
                  <button
                    key={x}
                    onClick={() => {
                      setInput(x);
                      textarea.current?.focus();
                    }}
                  >
                    <Sparkle size={14}/>{x}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages">
              {messages.map((m, i) => (
                <article className={`message ${m.role}`} key={i}>
                  <div className={`avatar ${m.role}`}>
                    {m.role === "assistant" ? <Sparkle size={16}/> : `Y`}
                  </div>

                  <div className="msg-body">
                    <div className="meta">
                      {m.role === "assistant" ? "LocalMind" : "You"}
                    </div>

                    <div className="bubble">
                      {m.role === "assistant"
                        ? (
                          <Markdown
                            text={m.content}
                            sources={m.sources || []}
                            activeSource={expandedCitation?.messageIndex === i ? expandedCitation.sourceIndex : null}
                            onCitationClick={(sourceIndex) => setExpandedCitation((current) =>
                              current?.messageIndex === i && current.sourceIndex === sourceIndex
                                ? null
                                : { messageIndex: i, sourceIndex }
                            )}
                          />
                        )
                        : <p>{m.content}</p>}
                    </div>

                    {m.role === "assistant" && (
                      <button
                        className="copy"
                        onClick={() => navigator.clipboard?.writeText(m.content)}
                      >
                        <Copy/> Copy
                      </button>
                    )}
                  </div>
                </article>
              ))}

              {loading && (
                <article className="message assistant">
                  <div className="avatar assistant">
                    <Sparkle size={16}/>
                  </div>

                  <div className="msg-body">
                    <div className="meta">LocalMind</div>

                    <div className="thinking">
                      <i/><i/><i/>
                      <span>
                        {useRag ? "Searching local documents" : "Thinking locally"}
                      </span>
                    </div>
                  </div>
                </article>
              )}

              <div ref={bottom}/>
            </div>
          )}
        </section>

        {!showLibrary && <div className="composer-wrap">
          {uploadStatus && (!documentName || uploading) && (
            <div className={`upload-status ${uploading ? "loading" : ""}`}>
              {uploading ? "⏳ " : "✓ "}
              {uploadStatus}
            </div>
          )}

          {documentName && !uploading && (
            <div className="document-chip">
              <span>📄</span>
              <span className="document-chip-name">{documentName}</span>
              <span className="document-chip-meta">· {documentChunks} chunks</span>
              <button type="button" className="document-chip-remove" onClick={() => { setDocumentName(""); setDocumentChunks(0); setUseRag(false); setUploadStatus(""); }} aria-label="Remove document" title="Remove document">×</button>
            </div>
          )}

          <form className="composer" onSubmit={send}>
            <textarea
              ref={textarea}
              value={input}
              onChange={e => setInput(e.target.value.slice(0, 10000))}
              onKeyDown={e => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  e.currentTarget.form?.requestSubmit();
                }
              }}
              placeholder={useRag && documents.length === 0 ? "Upload a document to ask about it..." : useRag ? "Ask about your documents..." : "Message LocalMind..."}
              rows="1"
              disabled={loading}
            />

            <div className="compose-footer">
              <div className="rag-controls">
                <label className="upload-button">
                  <input
                    ref={fileInput}
                    type="file"
                    accept=".pdf,.docx,.txt"
                    hidden
                    onChange={e => {
                      uploadDocument(e.target.files?.[0]);
                      e.target.value = "";
                    }}
                  />
                  <span>📄 Upload</span>
                </label>
                <label className="rag-toggle">
                  <input
                    type="checkbox"
                    checked={useRag}
                    onChange={e => setUseRag(e.target.checked)} disabled={documents.length === 0 || uploading}
                  />
                  <span>RAG</span>
                </label>
                <select
                  value={topK}
                  onChange={e => setTopK(Number(e.target.value))}
                  disabled={!useRag}
                  title="Number of retrieved chunks"
                >
                  <option value={1}>Top 1</option>
                  <option value={3}>Top 3</option>
                  <option value={5}>Top 5</option>
                </select>
              </div>
              <span>
                {input
                  ? `${input.length.toLocaleString()} / 10,000`
                  : `Enter to send · Shift + Enter for new line`}
              </span>

              <button disabled={!input.trim() || loading || !connected}>
                <Send/>
              </button>
            </div>
          </form>

          <div className="privacy">
            Your prompts are processed locally through Ollama.
          </div>
        </div>}
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App/>);











