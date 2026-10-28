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
const Sparkle = ({ size }) => <Icon size={size}><path d="m12 3 1.7 5.3L19 10l-5.3 1.7L12 17l-1.7-5.3L5 10l5.3-1.7Z"/><path d="m19 17 .7 2.3L22 20l-2.3.7L19 23l-.7-2.3L16 20l2.3-.7Z"/></Icon>;
const Plus = () => <Icon><path d="M12 5v14M5 12h14"/></Icon>;
const Search = () => <Icon><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></Icon>;
const Menu = () => <Icon><path d="M4 6h16M4 12h16M4 18h16"/></Icon>;
const Close = () => <Icon><path d="m6 6 12 12M18 6 6 18"/></Icon>;
const Send = () => <Icon><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></Icon>;
const Copy = () => <Icon size={14}><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></Icon>;

function Markdown({ text }) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre({ children }) {
            return <pre>{children}</pre>;
          },
          code({ children, className }) {
            return (
              <code className={className || "inline-code"}>
                {children}
              </code>
            );
          },
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
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
  const bottom = useRef(null);
  const textarea = useRef(null);

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
  useEffect(() => { check(); const t = setInterval(check, 30000); return () => clearInterval(t); }, []);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  async function check() {
    try {
      const [h, m] = await Promise.all([fetch(`${API}/health`), fetch(`${API}/models`)]);
      const health = await h.json(), data = await m.json();
      setConnected(Boolean(health.ollama?.connected));
      setModel(health.configured_model || data.models?.[0] || "unknown");
      setModels(data.models || []);
    } catch { setConnected(false); setModel("offline"); setModels([]); }
  }

  function newChat() { setActive(null); setMessages([]); setInput(""); setMobile(false); setTimeout(() => textarea.current?.focus(), 50); }

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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history
      })
    });

    const data = await r.json();

    if (!r.ok) {
      throw new Error(data.detail || "Request failed");
    }

    const next = [
      ...userMessages,
      { role: "assistant", content: data.response }
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

  const visible = chats.filter(c => c.title.toLowerCase().includes(search.toLowerCase())).sort((a,b)=>b.updatedAt-a.updatedAt);

  return <div className="app">
    <aside className={`sidebar ${mobile ? "show" : ""}`}>
      <div className="brand"><div className="logo"><Sparkle size={20}/></div><div><b>LocalMind</b><small>Private local AI</small></div><button className="close" onClick={()=>setMobile(false)}><Close/></button></div>
      <button className="new-chat" onClick={newChat}><Plus/>New chat</button>
      <label className="search"><Search/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search chats"/></label>
      <div className="recent"><span>RECENT CONVERSATIONS</span>{visible.length ? visible.map(c=><button className={`chat-item ${active===c.id?"active":""}`} key={c.id} onClick={()=>{setActive(c.id);setMessages(c.messages);setMobile(false)}}><span className="chat-icon">◌</span>{c.title}</button>) : <p>No conversations yet.</p>}</div>
      <div className="sidebar-bottom"><div className="connection"><i className={connected?"on":""}/><div><b>{connected?"Ollama connected":"Ollama offline"}</b><small>{connected?model:"Start your local server"}</small></div></div><button className="settings">⚙ Settings</button></div>
    </aside>
    {mobile && <button className="backdrop" onClick={()=>setMobile(false)}/>} 
    <main className="main">
      <header className="topbar"><button className="menu" onClick={()=>setMobile(true)}><Menu/></button><div className="model"><span>MODEL</span><select value={model} onChange={e=>setModel(e.target.value)} disabled={!models.length}>{(models.length?models:[model]).map(m=><option key={m}>{m}</option>)}</select></div><div className={`local ${connected?"online":""}`}><i/> {connected?"Local":"Offline"}</div></header>
      <section className="content">
        {!messages.length ? <div className="welcome"><div className="hero-icon"><Sparkle size={28}/></div><div className="eyebrow">LOCAL AI ASSISTANT</div><h1>Your AI.<br/><span>Running locally.</span></h1><p>Ask questions, write code, brainstorm ideas, or learn something new — powered by Ollama on your own machine.</p><div className="prompts">{["Explain RAG in simple terms","Help me debug a Python function","Give me 5 project ideas","Teach me a concept step by step"].map(x=><button key={x} onClick={()=>{setInput(x);textarea.current?.focus()}}><Sparkle size={14}/>{x}</button>)}</div></div> : <div className="messages">{messages.map((m,i)=><article className={`message ${m.role}`} key={i}><div className={`avatar ${m.role}`}>{m.role==="assistant"?<Sparkle size={16}/>:`Y`}</div><div className="msg-body"><div className="meta">{m.role==="assistant"?"LocalMind":"You"}</div><div className="bubble">{m.role==="assistant"?<Markdown text={m.content}/>:<p>{m.content}</p>}</div>{m.role==="assistant"&&<button className="copy" onClick={()=>navigator.clipboard?.writeText(m.content)}><Copy/> Copy</button>}</div></article>)}{loading&&<article className="message assistant"><div className="avatar assistant"><Sparkle size={16}/></div><div className="msg-body"><div className="meta">LocalMind</div><div className="thinking"><i/><i/><i/><span>Thinking locally</span></div></div></article>}<div ref={bottom}/></div>}
      </section>
      <div className="composer-wrap"><form className="composer" onSubmit={send}><textarea ref={textarea} value={input} onChange={e=>setInput(e.target.value.slice(0,10000))} onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();e.currentTarget.form?.requestSubmit()}}} placeholder="Message LocalMind..." rows="1" disabled={loading}/><div className="compose-footer"><span>{input?`${input.length.toLocaleString()} / 10,000`:`Enter to send · Shift + Enter for new line`}</span><button disabled={!input.trim()||loading||!connected}><Send/></button></div></form><div className="privacy">Your prompts are processed locally through Ollama.</div></div>
    </main>
  </div>;
}

createRoot(document.getElementById("root")).render(<App/>);
