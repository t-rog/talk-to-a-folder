import { Fragment, useState, useEffect, useRef, useMemo, FormEvent, KeyboardEvent } from 'react';
import { FolderData, buildContext, buildSuggestions, summarize } from '../lib/folderData';
import { apiUrl } from '../lib/api';

interface Source {
  file_name: string;
  file_id: string;
  chunk_index: number;
}

interface Message {
  role: 'agent' | 'user';
  text: string;
  hint?: boolean;
  sources?: Source[];
}

interface Props {
  folder: FolderData;
}

function openingLine(folder: FolderData, summary: ReturnType<typeof summarize>): string {
  const top = summary.slice(0, 3).map((s) => `${s.files.length} ${s.label.toLowerCase()}`);
  const list = top.length > 1
    ? `${top.slice(0, -1).join(', ')} and ${top.slice(-1)}`
    : top[0];
  return `I just finished reading "${folder.label}" — ${folder.files.length} files in total, mostly ${list}. What do you want to know?`;
}

function Bubble({ role, hint, children, sources }: { role: string; hint?: boolean; sources?: Source[]; children: React.ReactNode }) {
  // Dedupe sources by file_id — multiple chunks from one file → one link.
  const uniqueSources = useMemo(() => {
    if (!sources) return [];
    const seen = new Set<string>();
    return sources.filter((s) => {
      if (seen.has(s.file_id)) return false;
      seen.add(s.file_id);
      return true;
    });
  }, [sources]);

  return (
    <div className={`bubble bubble-${role} ${hint ? 'bubble-hint' : ''}`}>
      <div className="bubble-text">{children}</div>
      {uniqueSources.length > 0 && (
        <div className="bubble-sources">
          <strong>Sources:</strong>{' '}
          {uniqueSources.map((s, i) => (
            <Fragment key={s.file_id}>
              {i > 0 && ', '}
              <a
                href={`https://drive.google.com/file/d/${s.file_id}/view`}
                target="_blank"
                rel="noopener noreferrer"
                className="source-link"
              >
                {s.file_name}
              </a>
            </Fragment>
          ))}
        </div>
      )}
    </div>
  );
}

export function Chat({ folder }: Props) {
  const summary = useMemo(() => summarize(folder.files), [folder.files]);
  const folderContext = useMemo(() => buildContext(folder, summary), [folder, summary]);
  const suggestions = useMemo(() => buildSuggestions(summary), [summary]);

  const [messages, setMessages] = useState<Message[]>(() => [
    { role: 'agent', text: openingLine(folder, summary), hint: true },
  ]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMessages([{ role: 'agent', text: openingLine(folder, summary), hint: true }]);
  }, [folder.url]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, busy]);

  const send = async (overrideText?: string) => {
    const text = (overrideText ?? draft).trim();
    if (!text || busy) return;
    setDraft('');
    setMessages((m) => [...m, { role: 'user', text }]);
    setBusy(true);
    try {
      const res = await fetch(apiUrl('/api/chat'), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, context: folderContext, folder_id: folder.folderId }),
      });
      const data = await res.json();
      setMessages((m) => [...m, { role: 'agent', text: data.reply, sources: data.sources }]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: 'agent', text: "Hmm, I couldn't reach my brain just now. Mind asking again?" },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="chat-inner">
      <div className="chat-scroll" ref={scrollRef}>
        {messages.map((m, i) => (
          <Bubble key={i} role={m.role} hint={m.hint} sources={m.sources}>{m.text}</Bubble>
        ))}
        {busy && (
          <Bubble role="agent">
            <span className="typing"><i /><i /><i /></span>
          </Bubble>
        )}
      </div>
      {messages.length <= 1 && (
        <div className="suggestions">
          {suggestions.map((s) => (
            <button key={s} className="suggestion" onClick={() => send(s)}>{s}</button>
          ))}
        </div>
      )}
      <form className="chat-input" onSubmit={(e: FormEvent) => { e.preventDefault(); send(); }}>
        <textarea
          rows={1}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask Folder about this folder…"
        />
        <button type="submit" className="send" disabled={!draft.trim() || busy} aria-label="Send">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
               strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </button>
      </form>
    </div>
  );
}
