import { useMemo } from 'react';
import { Phase } from '../App';
import { FolderData, FileEntry, TypeCategory, summarize, fmtSize, categorize } from '../lib/folderData';
import { TypeGlyph } from './TypeGlyph';
import './AnalyticsPanel.scss';

interface Tweaks {
  vis: string;
  showSizes: boolean;
}

interface Props {
  phase: Phase;
  folder: FolderData | null;
  tweaks: Tweaks;
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function CardsView({ summary, total, showSizes }: { summary: TypeCategory[]; total: number; showSizes: boolean }) {
  return (
    <div className="cards">
      {summary.map((t, i) => (
        <div key={t.id} className="card" style={{ '--i': i } as React.CSSProperties}>
          <div className="card-icon"><TypeGlyph id={t.id} /></div>
          <div className="card-count">{t.files.length}</div>
          <div className="card-label">{t.label}</div>
          {showSizes && <div className="card-size">{fmtSize(t.totalMB)}</div>}
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

function BarsView({ summary, showSizes }: { summary: TypeCategory[]; showSizes: boolean }) {
  const max = Math.max(...summary.map((t) => t.files.length));
  return (
    <div className="bars">
      {summary.map((t) => (
        <div key={t.id} className="bar-row">
          <div className="bar-icon"><TypeGlyph id={t.id} /></div>
          <div className="bar-label">{t.label}</div>
          <div className="bar-track">
            <span className="bar-fill" style={{ width: `${(t.files.length / max) * 100}%` }} />
            <span className="bar-count">{t.files.length}</span>
          </div>
          {showSizes && <div className="bar-size">{fmtSize(t.totalMB)}</div>}
        </div>
      ))}
    </div>
  );
}

function ListView({ summary, total, showSizes }: { summary: TypeCategory[]; total: number; showSizes: boolean }) {
  return (
    <table className="list">
      <thead>
        <tr>
          <th>Type</th>
          <th>Count</th>
          <th>Share</th>
          {showSizes && <th>Size</th>}
          <th>Extensions</th>
        </tr>
      </thead>
      <tbody>
        {summary.map((t) => (
          <tr key={t.id}>
            <td className="list-type">
              <TypeGlyph id={t.id} />
              <span>{t.label}</span>
            </td>
            <td className="num">{t.files.length}</td>
            <td className="num">{((t.files.length / total) * 100).toFixed(0)}%</td>
            {showSizes && <td className="num">{fmtSize(t.totalMB)}</td>}
            <td className="list-exts">
              {[...new Set(t.files.map((f) => f.ext))].map((e) => (
                <span key={e} className="ext-pill">.{e}</span>
              ))}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function BreakdownView({ summary, total, tweaks }: { summary: TypeCategory[]; total: number; tweaks: Tweaks }) {
  if (tweaks.vis === 'bars') return <BarsView summary={summary} showSizes={tweaks.showSizes} />;
  if (tweaks.vis === 'list') return <ListView summary={summary} total={total} showSizes={tweaks.showSizes} />;
  return <CardsView summary={summary} total={total} showSizes={tweaks.showSizes} />;
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

export function AnalyticsPanel({ phase, folder, tweaks }: Props) {
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
            <BreakdownView summary={summary} total={folder.files.length} tweaks={tweaks} />
            <RecentList files={folder.files} />
          </div>
        </>
      )}
    </section>
  );
}
