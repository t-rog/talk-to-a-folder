import { useState, useEffect, useRef } from 'react';
import { UserInfo } from '../App';
import './Header.scss';

interface Props {
  signedIn: boolean;
  user: UserInfo | null;
  onSignIn: () => void;
  onSignOut: () => void;
}

function GoogleG() {
  return (
    <svg className="gsi-glyph" viewBox="0 0 18 18" aria-hidden="true">
      <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.49h4.84a4.14 4.14 0 0 1-1.8 2.71v2.26h2.91c1.7-1.57 2.69-3.88 2.69-6.62z" />
      <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.91-2.26c-.81.54-1.84.86-3.05.86-2.34 0-4.33-1.58-5.04-3.71H.96v2.33A9 9 0 0 0 9 18z" />
      <path fill="#FBBC05" d="M3.96 10.71A5.4 5.4 0 0 1 3.68 9c0-.59.1-1.17.28-1.71V4.96H.96A9 9 0 0 0 0 9c0 1.45.35 2.83.96 4.04l3-2.33z" />
      <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.34l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.96l3 2.33C4.67 5.16 6.66 3.58 9 3.58z" />
    </svg>
  );
}

function SignInButton({ onClick }: { onClick: () => void }) {
  return (
    <button className="gsi-btn" onClick={onClick}>
      <GoogleG />
      <span>Sign in with Google</span>
    </button>
  );
}

function UserButton({ user, onSignOut }: { user: UserInfo; onSignOut: () => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  return (
    <button ref={ref} className="user-btn" onClick={() => setOpen((o) => !o)}>
      <span className="user-avatar">{user.initials}</span>
      <span className="user-btn-name">{user.name.split(' ')[0]}</span>
      <span className="user-btn-caret" aria-hidden="true">▾</span>
      {open && (
        <div className="user-menu" onClick={(e) => e.stopPropagation()}>
          <div className="user-menu-hd">
            <span className="user-avatar">{user.initials}</span>
            <div>
              <div className="user-menu-name">{user.name}</div>
              <div className="user-menu-email">{user.email}</div>
            </div>
          </div>
          <div className="user-menu-list">
            <button className="user-menu-item danger" onClick={onSignOut}>Sign out</button>
          </div>
        </div>
      )}
    </button>
  );
}

export function Header({ signedIn, user, onSignIn, onSignOut }: Props) {
  return (
    <header className="hdr">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 28 24" fill="none" stroke="currentColor" strokeWidth="1.6"
               strokeLinejoin="round" strokeLinecap="round">
            <path d="M2 6c0-1.1.9-2 2-2h6l3 3h11c1.1 0 2 .9 2 2v11c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2z" />
            <path d="M9 13c1.5-1.5 4-1.5 5.5 0M11.5 11.5l.01.01" strokeWidth="1.4" />
          </svg>
        </span>
        <span className="brand-text">
          <span>Talk-to-a-</span><em>Folder</em>
        </span>
      </div>
      <div className="hdr-right">
        {signedIn && user
          ? <UserButton user={user} onSignOut={onSignOut} />
          : <SignInButton onClick={onSignIn} />}
      </div>
    </header>
  );
}
