interface Props {
  id: string;
}

export function TypeGlyph({ id }: Props) {
  const stroke = {
    fill: 'none' as const,
    stroke: 'currentColor',
    strokeWidth: 1.4,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
  };
  switch (id) {
    case 'doc':
      return (
        <svg viewBox="0 0 24 24" {...stroke}>
          <path d="M6 3h8l4 4v14H6z" />
          <path d="M14 3v4h4" />
          <path d="M9 12h6M9 15h6M9 18h4" />
        </svg>
      );
    case 'pdf':
      return (
        <svg viewBox="0 0 24 24" {...stroke}>
          <path d="M6 3h8l4 4v14H6z" />
          <path d="M14 3v4h4" />
          <text x="12" y="17.5" textAnchor="middle" fontSize="5.5" fontWeight="700"
                fontFamily="ui-monospace, monospace" fill="currentColor" stroke="none">PDF</text>
        </svg>
      );
    case 'sheet':
      return (
        <svg viewBox="0 0 24 24" {...stroke}>
          <rect x="4" y="5" width="16" height="14" rx="1" />
          <path d="M4 10h16M4 14h16M10 5v14M16 5v14" />
        </svg>
      );
    case 'deck':
      return (
        <svg viewBox="0 0 24 24" {...stroke}>
          <rect x="3" y="5" width="18" height="12" rx="1" />
          <path d="M9 20h6M12 17v3" />
        </svg>
      );
    case 'image':
      return (
        <svg viewBox="0 0 24 24" {...stroke}>
          <rect x="4" y="5" width="16" height="14" rx="1" />
          <circle cx="9" cy="10" r="1.4" />
          <path d="m4 17 5-5 4 4 3-3 4 4" />
        </svg>
      );
    case 'video':
      return (
        <svg viewBox="0 0 24 24" {...stroke}>
          <rect x="3" y="6" width="14" height="12" rx="1" />
          <path d="m17 10 4-2v8l-4-2z" />
        </svg>
      );
    case 'audio':
      return (
        <svg viewBox="0 0 24 24" {...stroke}>
          <path d="M10 17V6l8-2v11" />
          <circle cx="8" cy="17" r="2.2" />
          <circle cx="16" cy="15" r="2.2" />
        </svg>
      );
    case 'code':
      return (
        <svg viewBox="0 0 24 24" {...stroke}>
          <path d="m9 8-5 4 5 4M15 8l5 4-5 4M14 6l-4 12" />
        </svg>
      );
    case 'archive':
      return (
        <svg viewBox="0 0 24 24" {...stroke}>
          <rect x="4" y="4" width="16" height="16" rx="1" />
          <path d="M12 4v16M10 7h4M10 10h4M10 13h4M11 16h2v3h-2z" />
        </svg>
      );
    default:
      return (
        <svg viewBox="0 0 24 24" {...stroke}>
          <path d="M6 3h8l4 4v14H6z" />
          <path d="M14 3v4h4" />
        </svg>
      );
  }
}
