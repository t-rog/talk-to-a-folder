import { useMemo } from 'react';
import { Phase } from '../App';
import { FolderData, FileEntry, TypeCategory, summarize, fmtSize, categorize } from '../lib/folderData';
import { TypeGlyph } from './TypeGlyph';
import './AnalyticsPanel.scss';

interface Props {
  phase: Phase;
  folder: FolderData | null;
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function CardsView({ summary, total }: { summary: TypeCategory[]; total: number }) {
  return (
    <div className="cards">
      {summary.map((t, i) => (
        <div key={t.id} className="card" style={{ '--i': i } as React.CSSProperties}>
          <div className="card-icon"><TypeGlyph id={t.id} /></div>
          <div className="card-count">{t.files.length}</div>
          <div className="card-label">{t.label}</div>
          <div className="card-size">{fmtSize(t.totalMB)}</div>
          <div className="card-bar">
            <span style={{ width: `${(t.files.length / total) * 100}%` }} />
          </div>
          <div className="card-exts">
            {[...new Set(t.files.map((f) => f.ext))].slice(0, 4).map((e) => (
              <span key={e} className="ext-pill">.{e}</span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function RecentList({ files }: { files: FileEntry[] }) {
  const recent = useMemo(
    () => [...files].sort((a, b) => a.modifiedDays - b.modifiedDays).slice(0, 5),
    [files],
  );
  return (
    <div className="recent">
      <div className="recent-hd">Recently modified</div>
      <ul>
        {recent.map((f) => (
          <li key={f.name}>
            <span className="recent-icon"><TypeGlyph id={categorize(f.ext)} /></span>
            <span className="recent-name">{f.name}</span>
            <span className="recent-meta">
              {fmtSize(f.sizeMB)} · {f.modifiedDays === 1 ? '1d' : `${f.modifiedDays}d`} ago
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AnalyticsPanel({ phase, folder }: Props) {
  const summary = useMemo(() => folder ? summarize(folder.files) : [], [folder]);
  const totalMB = useMemo(() => folder ? folder.files.reduce((s, f) => s + f.sizeMB, 0) : 0, [folder]);

  return (
    <section className="panel">
      <div className="panel-hd">
        <div className="panel-eyebrow">
          <span className="panel-eyebrow-num">2</span>
          <span>Folder contents</span>
        </div>
        <h2 className="panel-title">{folder ? folder.label : 'Analytics'}</h2>
      </div>

      {phase !== 'connected' || !folder ? (
        <div className="analytics-empty">
          <div className="analytics-empty-glyph">
            {phase === 'scanning'
              ? <span className="dot-pulse" />
              : (
                <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor"
                     strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="7" height="9" rx="1" />
                  <rect x="14" y="3" width="7" height="5" rx="1" />
                  <rect x="14" y="12" width="7" height="9" rx="1" />
                  <rect x="3" y="16" width="7" height="5" rx="1" />
                </svg>
              )}
          </div>
          <h3 className="analytics-empty-title">
            {phase === 'scanning' ? 'Indexing files…' : 'Waiting for a folder'}
          </h3>
          <p className="analytics-empty-sub">
            {phase === 'scanning'
              ? 'Skimming through file names, sizes, and modified dates. This usually takes a couple of seconds.'
              : "Once you connect a folder on the left, you’ll see a breakdown of every file type here."}
          </p>
        </div>
      ) : (
        <>
          <div className="analytics-stats">
            <Stat label="Files" value={folder.files.length.toLocaleString()} />
            <Stat label="Size" value={fmtSize(totalMB)} />
            <Stat label="Owner" value={folder.owner} />
            <Stat label="Members" value={folder.members} />
          </div>
          <div className="panel-body">
            <CardsView summary={summary} total={folder.files.length} />
            <RecentList files={folder.files} />
          </div>
        </>
      )}
    </section>
  );
}
