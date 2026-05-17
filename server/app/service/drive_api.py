"""
Google Drive API access — folder metadata, listing children, file downloads,
and recursive folder traversal. No text extraction here; that's `extractors`.
"""
import logging
import re
import tempfile
from typing import Dict, List, Optional, Tuple

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from .extractors import EXTRACTORS, GOOGLE_EXPORTS

logger = logging.getLogger(__name__)

FOLDER_MIME = 'application/vnd.google-apps.folder'


class FolderAccessError(Exception):
    """Raised when a folder is not found, not accessible, or not a folder."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code  # 'folder_not_found' | 'access_denied' | 'not_a_folder' | 'unknown'


def build_drive_service(credentials_dict: Dict):
    """Construct a Drive v3 service client from session credentials."""
    credentials = Credentials(
        token=credentials_dict.get('token'),
        refresh_token=credentials_dict.get('refresh_token'),
        token_uri=credentials_dict.get('token_uri'),
        client_id=credentials_dict.get('client_id'),
        client_secret=credentials_dict.get('client_secret'),
        scopes=credentials_dict.get('scopes'),
    )
    return build('drive', 'v3', credentials=credentials)


def extract_folder_id(folder_url_or_id: str) -> str:
    """Pull the folder ID out of a Drive URL, or return the input if it already looks like an ID."""
    match = re.search(r'/folders/([a-zA-Z0-9-_]+)', folder_url_or_id)
    if match:
        return match.group(1)
    return folder_url_or_id.strip()


def get_folder_name(folder_id: str, credentials_dict: Dict) -> str:
    """
    Fetch the human-readable name of a Drive folder.
    Raises FolderAccessError with a specific code on common failures.
    """
    try:
        service = build_drive_service(credentials_dict)
        meta = service.files().get(fileId=folder_id, fields='name, mimeType').execute()
    except HttpError as e:
        status = e.resp.status if hasattr(e, 'resp') else None
        if status == 404:
            raise FolderAccessError('folder_not_found', "Folder not found. Check the URL.")
        if status in (401, 403):
            raise FolderAccessError('access_denied', "You don't have access to this folder.")
        raise FolderAccessError('unknown', f"Drive API error ({status}).")
    if meta.get('mimeType') != FOLDER_MIME:
        raise FolderAccessError('not_a_folder', "That URL points to a file, not a folder.")
    return meta.get('name') or 'Untitled folder'


def get_folder_files(folder_id: str, credentials_dict: Dict) -> List[Dict]:
    """List immediate children of a Drive folder (one level only)."""
    service = build_drive_service(credentials_dict)
    files: List[Dict] = []
    page_token = None
    while True:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            spaces='drive',
            fields='files(id, name, mimeType, size, modifiedTime), nextPageToken',
            pageToken=page_token,
            pageSize=100,
        ).execute()
        files.extend(results.get('files', []))
        page_token = results.get('nextPageToken')
        if not page_token:
            break
    return files


def traverse_folder(folder_id: str, credentials_dict: Dict, max_depth: int = 5) -> Tuple[List[Dict], int]:
    """
    Walk a folder recursively up to `max_depth` levels deep. Returns
    (files, subfolder_count). Subfolders are counted only for surfacing
    "we walked into N subfolders" in the UI.
    """
    all_files: List[Dict] = []
    subfolder_count = 0
    queue: List[Tuple[str, int]] = [(folder_id, 0)]
    visited: set = set()

    while queue:
        current_id, depth = queue.pop(0)
        if current_id in visited or depth > max_depth:
            continue
        visited.add(current_id)

        children = get_folder_files(current_id, credentials_dict)
        for c in children:
            if c.get('mimeType') == FOLDER_MIME:
                subfolder_count += 1
                queue.append((c['id'], depth + 1))
            else:
                all_files.append(c)

    return all_files, subfolder_count


def download_file(file_id: str, credentials_dict: Dict, mime_type: str) -> Optional[Tuple[str, str]]:
    """
    Download a file from Google Drive. For Google native types listed in
    GOOGLE_EXPORTS, export them as the target format instead. Returns
    (tmp_path, effective_mime_type) or None on failure.
    """
    try:
        service = build_drive_service(credentials_dict)

        if mime_type in GOOGLE_EXPORTS:
            effective_mime = GOOGLE_EXPORTS[mime_type]
            request = service.files().export_media(fileId=file_id, mimeType=effective_mime)
        else:
            effective_mime = mime_type
            request = service.files().get_media(fileId=file_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp_file:
            tmp_path = tmp_file.name

        with open(tmp_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        return tmp_path, effective_mime
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        return None


def is_supported_mime(mime_type: str) -> bool:
    """Check whether a MIME type can be extracted (directly or via export)."""
    return mime_type in EXTRACTORS or mime_type in GOOGLE_EXPORTS
