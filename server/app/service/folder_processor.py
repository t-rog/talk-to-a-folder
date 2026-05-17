"""
Top-level orchestrator: turn a Drive folder URL into a list of chunk-with-
metadata dicts ready for vector storage. Pulls together drive_api,
extractors, and chunker; nothing else in the app needs to know how those
pieces fit together.
"""
import logging
import os
import time
from typing import Dict, List

from .chunker import chunk_text
from .drive_api import (
    FOLDER_MIME,
    FolderAccessError,
    download_file,
    extract_folder_id,
    get_folder_name,
    is_supported_mime,
    traverse_folder,
)
from .extractors import extract_text

logger = logging.getLogger(__name__)


def _log(msg: str) -> None:
    """Force-flushed stdout print so messages survive worker SIGKILL."""
    print(f"[drive] {msg}", flush=True)


def process_folder(folder_url_or_id: str, credentials_dict: Dict) -> Dict:
    """
    Process a Drive folder: list files (recursively), download supported
    files, extract text, chunk. Returns a structured result with success/error
    state, file count, chunk count, skipped files (with reasons), and
    subfolder count. The caller is responsible for storing chunks downstream.
    """
    try:
        t0 = time.time()
        folder_id = extract_folder_id(folder_url_or_id)
        _log(f"START process_folder folder_id={folder_id}")

        try:
            folder_name = get_folder_name(folder_id, credentials_dict)
        except FolderAccessError as e:
            _log(f"folder access error: {e.code} — {e}")
            return {'status': 'error', 'error_code': e.code, 'message': str(e)}
        _log(f"folder_name={folder_name!r}")

        t_list = time.time()
        files, subfolder_count = traverse_folder(folder_id, credentials_dict)
        _log(f"traverse took {time.time() - t_list:.2f}s, {len(files)} files, {subfolder_count} subfolders")

        supported_files = [f for f in files if is_supported_mime(f.get('mimeType', ''))]
        unsupported_count = len(files) - len(supported_files)
        _log(f"{len(supported_files)} supported, {unsupported_count} unsupported")

        all_chunks: List[Dict] = []
        skipped_files: List[Dict] = []
        processed_count = 0

        for file_info in supported_files:
            file_id = file_info['id']
            file_name = file_info['name']
            mime_type = file_info['mimeType']
            _log(f"FILE start: {file_name} ({mime_type})")

            t_dl = time.time()
            download_result = download_file(file_id, credentials_dict, mime_type)
            _log(f"  download took {time.time() - t_dl:.2f}s")
            if not download_result:
                _log("  SKIP: download failed")
                skipped_files.append({'name': file_name, 'reason': 'download_failed'})
                continue
            tmp_path, effective_mime = download_result

            try:
                t_ex = time.time()
                text = extract_text(tmp_path, effective_mime)
                _log(f"  extract took {time.time() - t_ex:.2f}s, {len(text)} chars")
                if not text:
                    _log("  SKIP: no text")
                    skipped_files.append({'name': file_name, 'reason': 'no_text'})
                    continue

                text_chunks = chunk_text(text)
                if not text_chunks:
                    skipped_files.append({'name': file_name, 'reason': 'no_chunks'})
                    continue

                for chunk_index, chunk_text_content in enumerate(text_chunks):
                    all_chunks.append({
                        'document_text': chunk_text_content,
                        'metadata': {
                            'file_name': file_name,
                            'file_id': file_id,
                            'mime_type': mime_type,
                            'chunk_index': chunk_index,
                            'folder_id': folder_id,
                        },
                    })

                processed_count += 1
                _log(f"  FILE done: {len(text_chunks)} chunks")

            finally:
                try:
                    os.unlink(tmp_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {tmp_path}: {e}")

        _log(f"END process_folder: {processed_count} files, {len(all_chunks)} chunks, "
             f"total {time.time() - t0:.2f}s")

        return {
            'status': 'success',
            'folder_id': folder_id,
            'folder_name': folder_name,
            'file_count': processed_count,
            'chunk_count': len(all_chunks),
            'chunks': all_chunks,
            'skipped_files': skipped_files,
            'unsupported_file_count': unsupported_count,
            'subfolder_count': subfolder_count,
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
        return {'status': 'error', 'error_code': 'unknown', 'message': str(e)}
