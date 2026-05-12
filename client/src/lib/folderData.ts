export interface FileEntry {
  name: string;
  ext: string;
  sizeMB: number;
  modifiedDays: number;
}

export interface FolderData {
  label: string;
  owner: string;
  members: number;
  url: string;
  files: FileEntry[];
}

export interface TypeCategory {
  id: string;
  label: string;
  exts: string[];
  files: FileEntry[];
  totalMB: number;
}

function gen(stem: string, ext: string, count: number, [smin, smax]: [number, number]): FileEntry[] {
  const out: FileEntry[] = [];
  for (let i = 1; i <= count; i++) {
    const seed = (stem.length * 13 + i * 7 + ext.length) % 1000;
    const r = (seed % 100) / 100;
    out.push({
      name: `${stem}-${String(i).padStart(2, '0')}.${ext}`,
      ext,
      sizeMB: smin + r * (smax - smin),
      modifiedDays: Math.floor((seed % 90) + 1),
    });
  }
  return out;
}

export const SAMPLE_FOLDERS: Record<string, FolderData> = {
  marketing: {
    label: 'Q4 Marketing Campaign',
    owner: 'Lena Park',
    members: 8,
    url: 'drive.google.com/drive/folders/1A8z_q4-marketing',
    files: [
      ...gen('brief', 'docx', 7, [0.3, 1.2]),
      ...gen('draft', 'docx', 4, [0.2, 0.8]),
      ...gen('contract', 'pdf', 3, [0.4, 2.0]),
      ...gen('report', 'pdf', 5, [1.5, 4.0]),
      ...gen('budget', 'xlsx', 4, [0.1, 0.6]),
      ...gen('metrics', 'csv', 6, [0.05, 0.3]),
      ...gen('deck', 'pptx', 9, [3.0, 22.0]),
      ...gen('keynote-export', 'key', 2, [12.0, 28.0]),
      ...gen('hero-shot', 'jpg', 24, [2.0, 7.0]),
      ...gen('product-render', 'png', 18, [3.0, 14.0]),
      ...gen('logo-variant', 'svg', 11, [0.02, 0.1]),
      ...gen('teaser', 'mp4', 6, [40.0, 240.0]),
      ...gen('bts-clip', 'mov', 3, [180.0, 520.0]),
      ...gen('voiceover', 'mp3', 4, [3.0, 14.0]),
      ...gen('studio-mix', 'wav', 2, [40.0, 80.0]),
      ...gen('brand-assets', 'zip', 2, [85.0, 220.0]),
      ...gen('tracker', 'txt', 3, [0.005, 0.04]),
    ],
  },
  wedding: {
    label: 'Wedding · June 2025',
    owner: 'Jess & Mo',
    members: 3,
    url: 'drive.google.com/drive/folders/2B9_wedding-jm',
    files: [
      ...gen('ceremony', 'jpg', 142, [3.0, 9.0]),
      ...gen('reception', 'jpg', 188, [2.5, 8.0]),
      ...gen('portrait', 'png', 31, [8.0, 18.0]),
      ...gen('raw', 'raw', 88, [22.0, 40.0]),
      ...gen('first-dance', 'mov', 4, [340.0, 720.0]),
      ...gen('speech', 'mp4', 7, [220.0, 410.0]),
      ...gen('highlight-cut', 'mp4', 1, [580.0, 600.0]),
      ...gen('playlist', 'mp3', 24, [4.0, 9.0]),
      ...gen('vows', 'docx', 2, [0.05, 0.1]),
      ...gen('seating-chart', 'pdf', 1, [0.4, 0.5]),
      ...gen('guest-list', 'xlsx', 1, [0.08, 0.1]),
    ],
  },
  onboarding: {
    label: 'Engineering Onboarding',
    owner: 'Platform Team',
    members: 42,
    url: 'drive.google.com/drive/folders/3C0_eng-onboarding',
    files: [
      ...gen('welcome', 'docx', 1, [0.3, 0.4]),
      ...gen('handbook', 'pdf', 4, [2.0, 8.0]),
      ...gen('policy', 'pdf', 11, [0.5, 3.0]),
      ...gen('runbook', 'md', 18, [0.02, 0.18]),
      ...gen('readme', 'md', 9, [0.01, 0.06]),
      ...gen('setup', 'sh', 6, [0.005, 0.02]),
      ...gen('config', 'yaml', 12, [0.005, 0.03]),
      ...gen('snippet', 'py', 22, [0.005, 0.05]),
      ...gen('example', 'ts', 17, [0.005, 0.04]),
      ...gen('sql-tour', 'sql', 5, [0.01, 0.1]),
      ...gen('intro-deck', 'pptx', 4, [4.0, 18.0]),
      ...gen('architecture', 'pdf', 2, [3.5, 9.0]),
      ...gen('recording', 'mp4', 8, [80.0, 380.0]),
      ...gen('diagram', 'png', 14, [0.4, 2.5]),
      ...gen('screenshot', 'png', 27, [0.3, 1.6]),
      ...gen('schema', 'json', 9, [0.02, 0.4]),
      ...gen('tracker', 'csv', 3, [0.05, 0.3]),
    ],
  },
};

const TYPES: Omit<TypeCategory, 'files' | 'totalMB'>[] = [
  { id: 'doc',     label: 'Documents',     exts: ['docx', 'doc', 'txt', 'rtf', 'md', 'pages'] },
  { id: 'pdf',     label: 'PDFs',          exts: ['pdf'] },
  { id: 'sheet',   label: 'Spreadsheets',  exts: ['xlsx', 'xls', 'csv', 'numbers', 'tsv'] },
  { id: 'deck',    label: 'Presentations', exts: ['pptx', 'ppt', 'key'] },
  { id: 'image',   label: 'Images',        exts: ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'heic', 'raw'] },
  { id: 'video',   label: 'Videos',        exts: ['mp4', 'mov', 'avi', 'mkv', 'webm'] },
  { id: 'audio',   label: 'Audio',         exts: ['mp3', 'wav', 'm4a', 'flac', 'aac'] },
  { id: 'code',    label: 'Code',          exts: ['py', 'ts', 'js', 'jsx', 'tsx', 'go', 'rs', 'sh', 'yaml', 'yml', 'json', 'sql', 'html', 'css'] },
  { id: 'archive', label: 'Archives',      exts: ['zip', 'tar', 'gz', 'rar', '7z'] },
];
const OTHER: Omit<TypeCategory, 'files' | 'totalMB'> = { id: 'other', label: 'Other', exts: [] };

export function categorize(ext: string): string {
  const e = ext.toLowerCase();
  return TYPES.find((t) => t.exts.includes(e))?.id ?? 'other';
}

export function summarize(files: FileEntry[]): TypeCategory[] {
  const byType: Record<string, TypeCategory> = {};
  for (const t of TYPES) byType[t.id] = { ...t, files: [], totalMB: 0 };
  byType.other = { ...OTHER, files: [], totalMB: 0 };
  for (const f of files) {
    const id = categorize(f.ext);
    byType[id].files.push(f);
    byType[id].totalMB += f.sizeMB;
  }
  return [...TYPES, OTHER]
    .map((t) => byType[t.id])
    .filter((t) => t.files.length > 0)
    .sort((a, b) => b.files.length - a.files.length);
}

export function fmtSize(mb: number): string {
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
  if (mb >= 1) return `${mb.toFixed(0)} MB`;
  return `${(mb * 1024).toFixed(0)} KB`;
}

export function buildContext(folder: FolderData, summary: TypeCategory[]): string {
  const totalMB = folder.files.reduce((s, f) => s + f.sizeMB, 0);
  const breakdown = summary
    .map((s) => `  - ${s.label}: ${s.files.length} files, ${fmtSize(s.totalMB)} (extensions: ${[...new Set(s.files.map((f) => f.ext))].join(', ')})`)
    .join('\n');
  const recent = [...folder.files]
    .sort((a, b) => a.modifiedDays - b.modifiedDays)
    .slice(0, 8)
    .map((f) => `  - ${f.name} (${fmtSize(f.sizeMB)}, ${f.modifiedDays}d ago)`)
    .join('\n');
  return [
    `Folder: ${folder.label}`,
    `Owner: ${folder.owner}`,
    `Members: ${folder.members}`,
    `Total: ${folder.files.length} files, ${fmtSize(totalMB)}`,
    `Breakdown:\n${breakdown}`,
    `Most recently modified files:\n${recent}`,
  ].join('\n');
}

export function buildSuggestions(summary: TypeCategory[]): string[] {
  const out = ["What's in this folder?"];
  if (summary.find((s) => s.id === 'video')) out.push('How much video do we have?');
  if (summary.find((s) => s.id === 'deck')) out.push('Find the latest deck.');
  if (out.length < 4) out.push('Anything I can clean up?');
  return out.slice(0, 4);
}
