import { FormEvent } from 'react';
import { Phase } from '../App';
import { FolderData /*, SAMPLE_FOLDERS, fmtSize */ } from '../lib/folderData';
import './UrlPanel.scss';

interface Props {
  phase: Phase;
  folder: FolderData | null;
  urlInput: string;
  setUrlInput: (v: string) => void;
  onConnect: (url: string) => void;
  onSample: (key: string) => void;
  onDisconnect: () => void;
  signedIn: boolean;
}

export function UrlPanel({ phase, folder, urlInput, setUrlInput, onConnect, onSample: _onSample, onDisconnect, signedIn }: Props) {
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim() || !signedIn) return;
    onConnect(urlInput.trim());
  };

  const statusState = phase === 'connected' ? 'connected' : phase === 'scanning' ? 'scanning' : 'idle';

  return (
    <section className="panel">
      <div className="panel-hd">
        <div className="panel-eyebrow">
          <span className="panel-eyebrow-num">1</span>
          <span>Connect a folder</span>
        </div>
        <h2 className="panel-title">Drive URL</h2>
      </div>

      <div className="urlpanel-body">
        <form className="urlpanel-input" onSubmit={submit}>
          <span>https://</span>
          <input
            placeholder="drive.google.com/drive/folders/…"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            disabled={!signedIn}
          />
          <button type="submit" disabled={!urlInput.trim() || !signedIn || phase === 'scanning'}>
            {phase === 'scanning' ? '…' : 'Go'}
          </button>
        </form>

        {/* Sample folders UI temporarily disabled. Uncomment to restore demo mode.
        <div>
          <div className="urlpanel-section-h">Sample folders</div>
          <div className="urlpanel-samples">
            {Object.entries(SAMPLE_FOLDERS).map(([key, f]) => {
              const totalMB = f.files.reduce((s, x) => s + x.sizeMB, 0);
              return (
                <button
                  key={key}
                  className="urlpanel-sample"
                  onClick={() => onSample(key)}
                  disabled={!signedIn}
                >
                  <div className="urlpanel-sample-name">{f.label}</div>
                  <div className="urlpanel-sample-meta">
                    {f.files.length} files · {fmtSize(totalMB)}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
        */}

        <div className="urlpanel-status" data-state={statusState}>
          <span className="urlpanel-status-dot" />
          <div style={{ flex: 1, minWidth: 0 }}>
            {!signedIn && (
              <>
                <strong>Not signed in</strong>
                <span>Sign in with Google to connect a folder.</span>
              </>
            )}
            {signedIn && phase === 'empty' && (
              <>
                <strong>No folder connected</strong>
                <span>Paste a Drive URL or pick a sample.</span>
              </>
            )}
            {signedIn && phase === 'scanning' && (
              <>
                <strong>Reading folder…</strong>
                {folder && <code>{folder.url}</code>}
              </>
            )}
            {signedIn && phase === 'connected' && folder && (
              <>
                <strong>{folder.label}</strong>
                <code>{folder.url}</code>
                <button className="urlpanel-disconnect" onClick={onDisconnect}>
                  Disconnect
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
