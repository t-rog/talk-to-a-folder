import { useState, useCallback, useEffect } from 'react';
import { GoogleOAuthProvider, useGoogleLogin } from '@react-oauth/google';
import { Header } from './components/Header';
import { UrlPanel } from './components/UrlPanel';
import { AnalyticsPanel } from './components/AnalyticsPanel';
import { ChatPanel } from './components/ChatPanel';
import { SAMPLE_FOLDERS, FolderData, FileEntry } from './lib/folderData';
import {
  type ApiFile,
  getCurrentUser,
  processFolder,
  signInWithGoogle,
  signOut,
} from './api';

// Google's native file types have no extension in their name (just "My Document"),
// so map them to a recognizable short label by MIME type before falling back to
// filename parsing.
const GOOGLE_MIME_EXT: Record<string, string> = {
  'application/vnd.google-apps.document': 'gdoc',
  'application/vnd.google-apps.spreadsheet': 'gsheet',
  'application/vnd.google-apps.presentation': 'gslides',
  'application/vnd.google-apps.form': 'gform',
  'application/vnd.google-apps.drawing': 'gdraw',
};

function apiFileToEntry(f: ApiFile): FileEntry {
  const googleExt = GOOGLE_MIME_EXT[f.mime_type];
  let ext: string;
  if (googleExt) {
    ext = googleExt;
  } else {
    const dotIdx = f.name.lastIndexOf('.');
    ext = dotIdx > 0 ? f.name.slice(dotIdx + 1).toLowerCase() : 'file';
  }
  const sizeMB = (f.size || 0) / (1024 * 1024);
  const modifiedDate = f.modified_time ? new Date(f.modified_time) : new Date();
  const modifiedDays = Math.max(0, Math.floor((Date.now() - modifiedDate.getTime()) / (1000 * 60 * 60 * 24)));
  return { name: f.name, ext, sizeMB, modifiedDays };
}

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

export type Phase = 'empty' | 'scanning' | 'connected';

export interface UserInfo {
  id: string;
  name: string;
  email: string;
  initials: string;
}

const FOLDER_STORAGE_PREFIX = 'ttf:folder:';

function loadFolderForUser(userId: string): FolderData | null {
  try {
    const raw = localStorage.getItem(FOLDER_STORAGE_PREFIX + userId);
    return raw ? (JSON.parse(raw) as FolderData) : null;
  } catch {
    return null;
  }
}

function saveFolderForUser(userId: string, folder: FolderData | null): void {
  const key = FOLDER_STORAGE_PREFIX + userId;
  if (folder) {
    localStorage.setItem(key, JSON.stringify(folder));
  } else {
    localStorage.removeItem(key);
  }
}

function deriveName(url: string): string {
  const m = url.match(/folders\/([\w-]+)/);
  if (m) return `Folder · ${m[1].slice(0, 8)}`;
  return 'Untitled folder';
}

function makeInitials(name: string): string {
  return name.split(' ').map((p) => p[0]).join('').slice(0, 2).toUpperCase();
}

function AppInner() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [signedIn, setSignedIn] = useState(false);
  const [phase, setPhase] = useState<Phase>('empty');
  const [folder, setFolder] = useState<FolderData | null>(null);
  const [urlInput, setUrlInput] = useState('');
  const [connectError, setConnectError] = useState<string | null>(null);

  // Check existing session on mount; restore active folder from localStorage if any
  useEffect(() => {
    getCurrentUser()
      .then((u) => {
        if (!u) return;
        setUser({ id: u.id, name: u.name, email: u.email, initials: makeInitials(u.name) });
        setSignedIn(true);
        const saved = loadFolderForUser(u.id);
        if (saved) {
          setFolder(saved);
          setPhase('connected');
        }
      })
      .catch(() => {});
  }, []);

  // Persist folder changes to localStorage so refresh restores the active folder.
  useEffect(() => {
    if (user?.id) saveFolderForUser(user.id, folder);
  }, [user, folder]);

  const handleGoogleLogin = useGoogleLogin({
    flow: 'auth-code',
    scope: 'openid email profile https://www.googleapis.com/auth/drive.readonly',
    onSuccess: async ({ code }) => {
      try {
        const u = await signInWithGoogle(code);
        setUser({ id: u.id, name: u.name, email: u.email, initials: makeInitials(u.name) });
        setSignedIn(true);
      } catch (err) {
        console.error('Google sign-in failed:', err);
      }
    },
    onError: () => console.error('Google login failed'),
  });

  const handleSignOut = async () => {
    await signOut().catch(() => {});
    setUser(null);
    setSignedIn(false);
    disconnect();
  };

  const connect = useCallback((sampleKey: string, customUrl?: string) => {
    if (customUrl) {
      setFolder({ label: deriveName(customUrl), owner: user?.name || 'You', members: 1, url: customUrl, files: [] });
      setPhase('scanning');

      setConnectError(null);
      processFolder(customUrl)
        .then((data) => {
          console.log('Folder processed:', data);
          const apiFiles: ApiFile[] = data.files || [];
          setFolder({
            label: data.folder_name || deriveName(customUrl),
            owner: user?.name || 'You',
            members: 1,
            url: customUrl,
            files: apiFiles.map(apiFileToEntry),
            folderId: data.folder_id,
            skippedFiles: data.skipped_files || [],
            unsupportedFileCount: data.unsupported_file_count || 0,
            subfolderCount: data.subfolder_count || 0,
            indexedFileCount: data.file_count || 0,
          });
          setPhase('connected');
        })
        .catch((err) => {
          console.error('Folder processing failed:', err);
          setConnectError(
            err?.message ||
              "Network error while indexing. The folder may have completed processing; try Disconnect and reconnect to verify."
          );
          setPhase('empty');
          setFolder(null);
        });
    } else {
      // Sample folder — pure mock for demo
      setFolder(SAMPLE_FOLDERS[sampleKey] ?? SAMPLE_FOLDERS.marketing);
      setPhase('scanning');
      setTimeout(() => setPhase('connected'), 1600);
    }
  }, [user]);

  const disconnect = () => {
    setPhase('empty');
    setFolder(null);
    setUrlInput('');
    setConnectError(null);
  };

  return (
    <div className="app" data-theme="cream">
      <Header
        signedIn={signedIn}
        user={user}
        onSignIn={handleGoogleLogin}
        onSignOut={handleSignOut}
      />
      <div className="three-up">
        <UrlPanel
          phase={phase}
          folder={folder}
          urlInput={urlInput}
          setUrlInput={setUrlInput}
          onConnect={(url) => connect('marketing', url)}
          onSample={connect}
          onDisconnect={disconnect}
          signedIn={signedIn}
          errorMessage={connectError}
        />
        <AnalyticsPanel phase={phase} folder={folder} />
        <ChatPanel phase={phase} folder={folder} />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AppInner />
    </GoogleOAuthProvider>
  );
}
