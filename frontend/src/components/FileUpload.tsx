import { useState, useCallback, useEffect } from 'react';
import { apiService, UploadResponse } from '../services/api';
import './FileUpload.css';

interface FileUploadProps {
  uploadedFile?: UploadResponse | null;
  onUploadSuccess?: (fileId: string, uploadResponse: UploadResponse) => void;
}

export default function FileUpload({ uploadedFile, onUploadSuccess }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(uploadedFile || null);
  const [error, setError] = useState<string | null>(null);

  // Atualiza quando uploadedFile muda
  useEffect(() => {
    if (uploadedFile) {
      setUploadResult(uploadedFile);
    }
  }, [uploadedFile]);

  const handleFile = async (file: File) => {
    if (!file.name.endsWith('.mpp')) {
      setError('Por favor, selecione um arquivo .mpp');
      return;
    }

    setIsUploading(true);
    setError(null);
    setUploadResult(null);

    try {
      const result = await apiService.uploadFile(file);
      console.log('FileUpload - Upload result completo:', result);
      console.log('FileUpload - work_item_id:', result.work_item_id);
      console.log('FileUpload - work_item_id type:', typeof result.work_item_id);
      console.log('FileUpload - work_item_id truthy?', !!result.work_item_id);
      console.log('FileUpload - work_item_id === null?', result.work_item_id === null);
      console.log('FileUpload - work_item_id === undefined?', result.work_item_id === undefined);
      
      // Se work_item_id está null mas parsed_data tem work_item_id, tenta extrair de lá
      if (!result.work_item_id && result.parsed_data?.project?.work_item_id) {
        console.log('FileUpload - work_item_id está null, tentando extrair de parsed_data.project.work_item_id');
        result.work_item_id = result.parsed_data.project.work_item_id;
        console.log('FileUpload - work_item_id corrigido:', result.work_item_id);
      }
      
      setUploadResult(result);
      if (onUploadSuccess) {
        console.log('FileUpload - Chamando onUploadSuccess com work_item_id:', result.work_item_id);
        onUploadSuccess(result.file_id, result);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao fazer upload do arquivo');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFile(file);
    }
  };

  return (
    <div className="file-upload-container">
      <div
        className={`upload-area ${isDragging ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-input"
          accept=".mpp"
          onChange={handleFileInput}
          disabled={isUploading}
          style={{ display: 'none' }}
        />
        <label htmlFor="file-input" className="upload-label">
          {isUploading ? (
            <div className="loading">
              <div className="spinner"></div>
              <p>Processando arquivo...</p>
            </div>
          ) : (
            <>
              <svg
                width="64"
                height="64"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
              <h3>Arraste um arquivo .mpp aqui</h3>
              <p>ou clique para selecionar</p>
            </>
          )}
        </label>
      </div>

      {error && <div className="error">{error}</div>}

      {uploadResult && (
        <div className="upload-success glass-card">
          <h3>✓ Arquivo carregado com sucesso!</h3>
          <div className="upload-info">
            <p><strong>Arquivo:</strong> {uploadResult.filename}</p>
            <p><strong>Projeto:</strong> {uploadResult.project_name}</p>
            {uploadResult.work_item_id && (
              <p><strong>Work Item ID:</strong> {uploadResult.work_item_id}</p>
            )}
            <p><strong>User Stories:</strong> {uploadResult.user_stories_count}</p>
            <p><strong>Tasks:</strong> {uploadResult.tasks_count}</p>
          </div>
          <p className="info-text">
            Use as outras abas para visualizar os dados, verificar o projeto no DevOps e sincronizar.
          </p>
        </div>
      )}
    </div>
  );
}

