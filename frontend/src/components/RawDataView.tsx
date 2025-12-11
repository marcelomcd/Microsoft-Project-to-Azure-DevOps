import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import './RawDataView.css';

interface RawDataViewProps {
  fileId: string;
}

interface RawData {
  headers: string[];
  rows: Record<string, string>[];
  total_rows: number;
}

export default function RawDataView({ fileId }: RawDataViewProps) {
  const [rawData, setRawData] = useState<RawData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 50;

  useEffect(() => {
    loadRawData();
  }, [fileId]);

  const loadRawData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await apiService.getRawFileData(fileId);
      setRawData(data);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Erro ao carregar dados brutos';
      console.error('Erro ao carregar dados brutos:', err);
      setError(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredRows = rawData?.rows.filter(row => {
    if (!searchTerm) return true;
    const searchLower = searchTerm.toLowerCase();
    return Object.values(row).some(value => 
      String(value).toLowerCase().includes(searchLower)
    );
  }) || [];

  const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
  const startIndex = (currentPage - 1) * rowsPerPage;
  const endIndex = startIndex + rowsPerPage;
  const paginatedRows = filteredRows.slice(startIndex, endIndex);

  if (isLoading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>Carregando dados brutos do arquivo...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <div className="error">{error}</div>
        <button className="btn" onClick={loadRawData}>
          Tentar Novamente
        </button>
      </div>
    );
  }

  if (!rawData) {
    return null;
  }

  if (rawData.is_binary) {
    return (
      <div className="empty-state glass-card">
        <h3>Arquivo Binário Detectado</h3>
        <p>{rawData.message || 'Este arquivo .mpp é binário e não pode ser exibido como texto.'}</p>
        <p className="info-text">
          Para visualizar os dados brutos, exporte o arquivo .mpp para CSV no Microsoft Project e faça upload do CSV.
        </p>
      </div>
    );
  }

  if (rawData.rows.length === 0) {
    return (
      <div className="empty-state glass-card">
        <p>Nenhum dado encontrado no arquivo.</p>
      </div>
    );
  }

  return (
    <div className="raw-data-view">
      <div className="view-header glass-card">
        <div className="header-content">
          <h2>Microsoft Project - Visualização de Colunas e Linhas</h2>
          <div className="header-stats">
            <span className="stat-badge">Total: {rawData.total_rows} linhas</span>
            <span className="stat-badge">Colunas: {rawData.headers.length}</span>
          </div>
        </div>
      </div>

      <div className="controls glass-card">
        <div className="search-box">
          <input
            type="text"
            placeholder="Buscar em todas as colunas..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            className="search-input"
          />
          {searchTerm && (
            <button
              className="clear-search"
              onClick={() => {
                setSearchTerm('');
                setCurrentPage(1);
              }}
            >
              ✕
            </button>
          )}
        </div>
        {searchTerm && (
          <div className="search-results">
            {filteredRows.length} resultado(s) encontrado(s)
          </div>
        )}
      </div>

      <div className="table-container glass-card">
        <div className="table-wrapper">
          <table className="raw-data-table">
            <thead>
              <tr>
                {rawData.headers.map((header, idx) => (
                  <th key={idx}>{header || `Coluna ${idx + 1}`}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginatedRows.map((row, rowIdx) => (
                <tr key={rowIdx}>
                  {rawData.headers.map((header, colIdx) => (
                    <td key={colIdx} title={String(row[header] || '')}>
                      {String(row[header] || '').substring(0, 100)}
                      {String(row[header] || '').length > 100 && '...'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {totalPages > 1 && (
        <div className="pagination glass-card">
          <button
            className="btn btn-secondary"
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage === 1}
          >
            Anterior
          </button>
          <span className="page-info">
            Página {currentPage} de {totalPages}
          </span>
          <button
            className="btn btn-secondary"
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
          >
            Próxima
          </button>
        </div>
      )}
    </div>
  );
}

