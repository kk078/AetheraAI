import React, { useState, useRef, useCallback } from 'react';
import { api } from '../../utils/api';

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB
const ACCEPTED_TYPES = [
  'application/pdf',
  'text/plain',
  'text/csv',
  'application/json',
  'image/png',
  'image/jpeg',
  'image/gif',
  'image/webp',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];

const FILE_TYPE_ICONS = {
  'application/pdf': (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
    </svg>
  ),
  'image/': (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  ),
  default: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
};

function getFileIcon(mimeType) {
  if (!mimeType) return FILE_TYPE_ICONS.default;
  if (mimeType === 'application/pdf') return FILE_TYPE_ICONS['application/pdf'];
  if (mimeType.startsWith('image/')) return FILE_TYPE_ICONS['image/'];
  return FILE_TYPE_ICONS.default;
}

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FileUploadZone({ onUploadComplete, onFilesChange }) {
  const [files, setFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);
  const dragCounter = useRef(0);

  const addFiles = useCallback((newFiles) => {
    setError(null);
    const fileArray = Array.from(newFiles);
    const validated = [];

    for (const file of fileArray) {
      if (file.size > MAX_FILE_SIZE) {
        setError(`${file.name} exceeds 50 MB limit`);
        continue;
      }
      validated.push({
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        file,
        name: file.name,
        type: file.type || 'application/octet-stream',
        size: file.size,
        status: 'pending',
        progress: 0,
        error: null,
        url: null,
      });
    }

    setFiles((prev) => {
      const updated = [...prev, ...validated];
      onFilesChange?.(updated.filter((f) => f.status !== 'removed'));
      return updated;
    });
  }, [onFilesChange]);

  const uploadFile = useCallback(async (fileEntry) => {
    setFiles((prev) =>
      prev.map((f) =>
        f.id === fileEntry.id ? { ...f, status: 'uploading', progress: 0 } : f
      )
    );

    const formData = new FormData();
    formData.append('file', fileEntry.file);

    try {
      const xhr = new XMLHttpRequest();

      const result = await new Promise((resolve, reject) => {
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            const progress = Math.round((e.loaded / e.total) * 100);
            setFiles((prev) =>
              prev.map((f) =>
                f.id === fileEntry.id ? { ...f, progress } : f
              )
            );
          }
        });

        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              resolve(JSON.parse(xhr.responseText));
            } catch {
              resolve({ url: xhr.responseText });
            }
          } else {
            reject(new Error(`Upload failed: HTTP ${xhr.status}`));
          }
        });

        xhr.addEventListener('error', () => reject(new Error('Network error during upload')));
        xhr.addEventListener('abort', () => reject(new Error('Upload cancelled')));

        xhr.open('POST', `${api.baseURL}/api/upload`);
        xhr.send(formData);
      });

      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileEntry.id
            ? { ...f, status: 'complete', progress: 100, url: result.url, error: null }
            : f
        )
      );

      onUploadComplete?.(result, fileEntry);
    } catch (err) {
      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileEntry.id
            ? { ...f, status: 'error', error: err.message }
            : f
        )
      );
    }
  }, [onUploadComplete]);

  const removeFile = useCallback((fileId) => {
    setFiles((prev) => {
      const updated = prev.filter((f) => f.id !== fileId);
      onFilesChange?.(updated.filter((f) => f.status !== 'removed'));
      return updated;
    });
  }, [onFilesChange]);

  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current++;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current--;
    if (dragCounter.current === 0) {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    dragCounter.current = 0;

    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles && droppedFiles.length > 0) {
      addFiles(droppedFiles);
    }
  }, [addFiles]);

  const handleInputChange = useCallback((e) => {
    const selectedFiles = e.target.files;
    if (selectedFiles && selectedFiles.length > 0) {
      addFiles(selectedFiles);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [addFiles]);

  const handleUploadAll = useCallback(() => {
    const pending = files.filter((f) => f.status === 'pending' || f.status === 'error');
    pending.forEach((f) => uploadFile(f));
  }, [files, uploadFile]);

  const pendingCount = files.filter((f) => f.status === 'pending' || f.status === 'error').length;
  const uploadingCount = files.filter((f) => f.status === 'uploading').length;

  return (
    <div className="space-y-3">
      {/* Drop zone */}
      <div
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          relative cursor-pointer rounded-xl border-2 border-dashed p-6 text-center transition-all
          ${isDragging
            ? 'border-aethera-primary bg-aethera-primary/10'
            : 'border-aethera-border hover:border-aethera-primary/50 hover:bg-aethera-surface/50'
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleInputChange}
          accept={ACCEPTED_TYPES.join(',')}
          className="hidden"
        />

        <div className="flex flex-col items-center gap-2">
          <svg className={`w-10 h-10 transition-colors ${isDragging ? 'text-aethera-primary' : 'text-aethera-text-secondary'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p className="text-sm text-aethera-foreground font-medium">
            {isDragging ? 'Drop files here' : 'Drag & drop files or click to browse'}
          </p>
          <p className="text-xs text-aethera-text-secondary">
            PDF, images, CSV, JSON, DOCX, XLSX (max 50 MB each)
          </p>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-aethera-foreground">
              {files.length} file{files.length !== 1 ? 's' : ''}
            </span>
            {pendingCount > 0 && (
              <button
                onClick={handleUploadAll}
                disabled={uploadingCount > 0}
                className="px-3 py-1 text-sm bg-aethera-primary hover:bg-cyan-600 disabled:bg-aethera-tertiary disabled:text-aethera-text-secondary text-white rounded-lg transition-colors"
              >
                {uploadingCount > 0 ? `Uploading ${uploadingCount}...` : `Upload ${pendingCount} file${pendingCount !== 1 ? 's' : ''}`}
              </button>
            )}
          </div>

          {files.map((fileEntry) => (
            <div
              key={fileEntry.id}
              className="flex items-center gap-3 p-3 bg-aethera-surface rounded-lg border border-aethera-border"
            >
              {/* File icon */}
              <div className="text-aethera-text-secondary flex-shrink-0">
                {getFileIcon(fileEntry.type)}
              </div>

              {/* File info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-aethera-foreground truncate">{fileEntry.name}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs text-aethera-text-secondary">{formatFileSize(fileEntry.size)}</span>
                  {fileEntry.status === 'uploading' && (
                    <span className="text-xs text-amber-400">{fileEntry.progress}%</span>
                  )}
                  {fileEntry.status === 'complete' && (
                    <span className="text-xs text-green-400">Uploaded</span>
                  )}
                  {fileEntry.status === 'error' && (
                    <span className="text-xs text-red-400" title={fileEntry.error}>Failed</span>
                  )}
                </div>

                {/* Progress bar */}
                {fileEntry.status === 'uploading' && (
                  <div className="mt-1.5 w-full bg-aethera-tertiary rounded-full h-1">
                    <div
                      className="bg-aethera-primary h-1 rounded-full transition-all"
                      style={{ width: `${fileEntry.progress}%` }}
                    />
                  </div>
                )}
              </div>

              {/* Status indicator */}
              {fileEntry.status === 'uploading' && (
                <svg className="w-4 h-4 text-amber-400 animate-spin flex-shrink-0" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              )}
              {fileEntry.status === 'complete' && (
                <svg className="w-4 h-4 text-green-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
              {fileEntry.status === 'error' && (
                <svg className="w-4 h-4 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}

              {/* Remove button */}
              <button
                onClick={(e) => { e.stopPropagation(); removeFile(fileEntry.id); }}
                className="p-1 text-aethera-text-secondary hover:text-red-400 transition-colors flex-shrink-0"
                title="Remove file"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}