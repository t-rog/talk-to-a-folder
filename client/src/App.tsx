import { useState, useCallback, useEffect } from 'react';
import { GoogleOAuthProvider, useGoogleLogin } from '@react-oauth/google';
import { Header } from './components/Header';
import { UrlPanel } from './components/UrlPanel';
import { AnalyticsPanel } from './components/AnalyticsPanel';
import { ChatPanel } from './components/ChatPanel';
import {
  TweaksPanel,
  TweakSection,
  TweakRadio,
  TweakToggle,
  TweakText,
  useTweaks,
} from './components/TweaksPanel';
import { SAMPLE_FOLDERS, FolderData } from './lib/folderData';

const GOOGLE_CLIENT_ID = '604215321895-lhqtfskga2a6ri1lkhuqgojuvv3med69.apps.googleusercontent.com';

const TWEAK_DEFAULTS = {
  theme: 'cream',
  vis: 'cards',
  showSizes: true,
  agentName: 'Folder',
};

export type Phase = 'empty' | 'scanning' | 'connected';

export interface UserInfo {
  name: string;
  email: string;
  initials: string;
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
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [signedIn, setSignedIn] = useState(false);
  const [phase, setPhase] = useState<Phase>('empty');
  const [folder, setFolder] = useState<FolderData | null>(null);
  const [urlInput, setUrlInput] = useState('');

  // Check existing session on mount
  useEffect(() => {
    fetch('/api/auth/me', { credentials: 'include' })
      .then(async (res) => {
        if (!res.ok) return;
        const data = await res.json();
        if (data.user) {
          setUser({ name: data.user.name, email: data.user.email, initials: makeInitials(data.user.name) });
          setSignedIn(true);
        }
      })
      .catch(() => {});
  }, []);

  const handleGoogleLogin = useGoogleLogin({
    flow: 'auth-code',
    scope: 'https://www.googleapis.com/auth/drive.metadata.readonly',
    onSuccess: async ({ code }) => {
      const res = await fetch('/api/auth/google', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      });
      if (res.ok) {
        const data = await res.json();
        const u = data.user;
        setUser({ name: u.name, email: u.email, initials: makeInitials(u.name) });
        setSignedIn(true);
      }
    },
    onError: () => console.error('Google login failed'),
  });

  const handleSignOut = async () => {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {});
    setUser(null);
    setSignedIn(false);
    disconnect();
  };

  const connect = useCallback((sampleKey: string, customUrl?: string) => {
    const sample = SAMPLE_FOLDERS[sampleKey] ?? SAMPLE_FOLDERS.marketing;
    const f = customUrl
      ? { ...sample, url: customUrl, label: deriveName(customUrl) }
      : sample;
    setFolder(f);
    setPhase('scanning');
    setTimeout(() => setPhase('connected'), 1600);
  }, []);

  const disconnect = () => {
    setPhase('empty');
    setFolder(null);
    setUrlInput('');
  };

  return (
    <div className="app" data-theme={t.theme}>
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
        />
        <AnalyticsPanel phase={phase} folder={folder} tweaks={t} />
        <ChatPanel phase={phase} folder={folder} agentName={t.agentName} />
      </div>
      <TweaksPanel>
        <TweakSection label="Theme">
          <TweakRadio label="Palette" value={t.theme} options={['cream', 'slate', 'mono']}
                      onChange={(v) => setTweak('theme', v)} />
        </TweakSection>
        <TweakSection label="Analytics">
          <TweakRadio label="Layout" value={t.vis} options={['cards', 'bars', 'list']}
                      onChange={(v) => setTweak('vis', v)} />
          <TweakToggle label="Show sizes" value={t.showSizes as boolean}
                       onChange={(v) => setTweak('showSizes', v)} />
        </TweakSection>
        <TweakSection label="Chat">
          <TweakText label="Agent name" value={t.agentName as string}
                     onChange={(v) => setTweak('agentName', v)} />
        </TweakSection>
      </TweaksPanel>
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
