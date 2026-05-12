import os
import re
import tempfile
import logging
from typing import Optional, Dict, List, Tuple
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from docx import Document
import io

logger = logging.getLogger(__name__)


def _build_drive_service(credentials_dict: Dict):
    """Build Google Drive service from session credentials dict."""
    credentials = Credentials(
        token=credentials_dict.get('token'),
        refresh_token=credentials_dict.get('refresh_token'),
        token_uri=credentials_dict.get('token_uri'),
        client_id=credentials_dict.get('client_id'),
        client_secret=credentials_dict.get('client_secret'),
        scopes=credentials_dict.get('scopes'),
    )
    return build('drive', 'v3', credentials=credentials)


def _extract_folder_id(folder_url_or_id: str) -> str:
    """Extract folder ID from a Google Drive URL or return as-is if already an ID."""
    # Format: https://drive.google.com/drive/folders/FOLDER_ID
    match = re.search(r'/folders/([a-zA-Z0-9-_]+)', folder_url_or_id)
    if match:
        return match.group(1)
    return folder_url_or_id.strip()


def extract_docx_text(file_path: str) -> str:
    """Extract all text from a DOCX file (paragraphs and tables)."""
    try:
        doc = Document(file_path)
        text_parts = []

        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)

        for table in doc.tables:
            for row in table.rows:
                row_text = ' | '.join(cell.text.strip() for cell in row.cells)
                if row_text.strip():
                    text_parts.append(row_text)

        return '\n'.join(text_parts)
    except Exception as e:
        logger.error(f"Error extracting DOCX from {file_path}: {e}")
        return ''


def extract_markdown_text(file_path: str) -> str:
    """Read a markdown (or any plain-text) file as-is."""
    try:
        with open(file_path, encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading text from {file_path}: {e}")
        return ''


# Extractor registry: MIME type -> extraction function.
# Keyed by the *effective* MIME type after any export.
EXTRACTORS = {
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': extract_docx_text,
    'text/markdown': extract_markdown_text,
}

# Google native MIME types are not downloadable directly; they must be exported
# via files().export_media(). Map each Google native type to the format we
# export it as, which must match a key in EXTRACTORS.
GOOGLE_EXPORTS = {
    'application/vnd.google-apps.document': 'text/markdown',
}


def extract_text(file_path: str, mime_type: str) -> str:
    """Route to appropriate extractor based on MIME type."""
    extractor = EXTRACTORS.get(mime_type)
    if not extractor:
        logger.warning(f"No extractor for MIME type {mime_type}")
        return ''
    return extractor(file_path)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks by character count."""
    if not text:
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def get_folder_files(folder_id: str, credentials_dict: Dict) -> List[Dict]:
    """List all files in a Google Drive folder."""
    try:
        service = _build_drive_service(credentials_dict)

        files = []
        page_token = None

        while True:
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                spaces='drive',
                fields='files(id, name, mimeType, size, modifiedTime)',
                pageToken=page_token,
                pageSize=100,
            ).execute()

            files.extend(results.get('files', []))
            page_token = results.get('nextPageToken')

            if not page_token:
                break

        return files
    except Exception as e:
        logger.error(f"Error listing folder {folder_id}: {e}")
        return []


def download_file(file_id: str, credentials_dict: Dict, mime_type: str) -> Optional[Tuple[str, str]]:
    """
    Download a file from Google Drive. For Google native types listed in
    GOOGLE_EXPORTS, export them as the target format instead. Returns
    (tmp_path, effective_mime_type) or None on failure.
    """
    try:
        service = _build_drive_service(credentials_dict)

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


def process_folder(folder_url_or_id: str, credentials_dict: Dict) -> Dict:
    """
    Process a Google Drive folder: list files, download, extract text, chunk.
    Returns dict with status, file_count, chunk_count, and list of chunks with metadata.
    """
    try:
        folder_id = _extract_folder_id(folder_url_or_id)
        logger.info(f"Processing folder {folder_id}")

        # Get list of files (exclude subfolders)
        all_items = get_folder_files(folder_id, credentials_dict)
        files = [
            f for f in all_items
            if f.get('mimeType') != 'application/vnd.google-apps.folder'
        ]
        logger.info(f"Found {len(files)} files in folder {folder_id}")

        # Filter to MIME types we can extract directly OR export from Google native
        supported_files = [
            f for f in files
            if f.get('mimeType') in EXTRACTORS or f.get('mimeType') in GOOGLE_EXPORTS
        ]
        logger.info(f"Found {len(supported_files)} files with supported MIME types")

        all_chunks = []
        processed_count = 0

        for file_info in supported_files:
            file_id = file_info['id']
            file_name = file_info['name']
            mime_type = file_info['mimeType']

            logger.info(f"Processing file: {file_name}")

            # Download file (exports Google native types to a supported format)
            download_result = download_file(file_id, credentials_dict, mime_type)
            if not download_result:
                logger.warning(f"Failed to download {file_name}, skipping")
                continue
            tmp_path, effective_mime = download_result

            try:
                # Extract text using the effective MIME type (post-export)
                text = extract_text(tmp_path, effective_mime)
                if not text:
                    logger.warning(f"No text extracted from {file_name}, skipping")
                    continue

                # Chunk text
                text_chunks = chunk_text(text)
                if not text_chunks:
                    logger.warning(f"No chunks produced from {file_name}, skipping")
                    continue

                # Create chunks with metadata
                for chunk_index, chunk_text_content in enumerate(text_chunks):
                    all_chunks.append({
                        'document_text': chunk_text_content,
                        'metadata': {
                            'file_name': file_name,
                            'file_id': file_id,
                            'mime_type': mime_type,
                            'chunk_index': chunk_index,
                            'folder_id': folder_id,
                        }
                    })

                processed_count += 1
                logger.info(f"Extracted {len(text_chunks)} chunks from {file_name}")

            finally:
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {tmp_path}: {e}")

        logger.info(
            f"Folder processing complete: {processed_count} files processed, "
            f"{len(all_chunks)} total chunks"
        )

        return {
            'status': 'success',
            'folder_id': folder_id,
            'file_count': processed_count,
            'chunk_count': len(all_chunks),
            'chunks': all_chunks,
            'files': [
                {
                    'name': f.get('name', ''),
                    'mime_type': f.get('mimeType', ''),
                    'size': int(f.get('size', 0) or 0),
                    'modified_time': f.get('modifiedTime', ''),
                }
                for f in files
            ],
        }

    except Exception as e:
        logger.error(f"Error processing folder {folder_url_or_id}: {e}")
        return {
            'status': 'error',
            'error': str(e),
        }
