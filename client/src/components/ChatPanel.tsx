import { Phase } from '../App';
import { FolderData } from '../lib/folderData';
import { Chat } from './Chat';
import './ChatPanel.scss';

interface Props {
  phase: Phase;
  folder: FolderData | null;
}

export function ChatPanel({ phase, folder }: Props) {
  return (
    <section className="panel">
      <div className="panel-hd">
        <div className="panel-eyebrow">
          <span className="panel-eyebrow-num">3</span>
          <span>Ask the agent</span>
        </div>
        <h2 className="panel-title">Folder chat</h2>
      </div>
      {phase === 'connected' && folder
        ? <Chat folder={folder} />
        : (
          <div className="chat-empty">
            <div className="chat-empty-title">
              {phase === 'scanning' ? 'Almost ready…' : 'Connect a folder to start chatting'}
            </div>
            <div className="chat-empty-sub">
              {phase === 'scanning'
                ? "I'm reading the file list now. Once I'm done, you can ask me what's inside."
                : 'Once a folder is connected, you can ask things like "what\'s the largest video?" or "find any contracts."'}
            </div>
          </div>
        )}
    </section>
  );
}
