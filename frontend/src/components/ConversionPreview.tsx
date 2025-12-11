import { useState, useEffect } from 'react';
import { apiService, ConversionResult } from '../services/api';
import './ConversionPreview.css';

interface ConversionPreviewProps {
  fileId: string;
}

export default function ConversionPreview({ fileId }: ConversionPreviewProps) {
  const [isConverting, setIsConverting] = useState(false);
  const [result, setResult] = useState<ConversionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [areaPath, setAreaPath] = useState('');
  const [iterationPath, setIterationPath] = useState('');
  const [skipDuplicates, setSkipDuplicates] = useState(true);

  const handleConvert = async () => {
    setIsConverting(true);
    setError(null);
    setResult(null);

    try {
      const conversionResult = await apiService.convertToDevOps(
        fileId,
        areaPath || undefined,
        iterationPath || undefined,
        skipDuplicates
      );
      setResult(conversionResult);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao converter para Azure DevOps');
    } finally {
      setIsConverting(false);
    }
  };

  return (
    <div className="conversion-preview glass-card">
      <h2>Converter para Azure DevOps</h2>

      <div className="conversion-form">
        <div className="form-group">
          <label htmlFor="area-path">Area Path (opcional)</label>
          <input
            id="area-path"
            type="text"
            value={areaPath}
            onChange={(e) => setAreaPath(e.target.value)}
            placeholder="Ex: Quali IT - Inovação e Tecnologia\\Cliente"
          />
        </div>

        <div className="form-group">
          <label htmlFor="iteration-path">Iteration Path (opcional)</label>
          <input
            id="iteration-path"
            type="text"
            value={iterationPath}
            onChange={(e) => setIterationPath(e.target.value)}
            placeholder="Ex: Quali IT - Inovação e Tecnologia\\Cliente"
          />
        </div>

        <div className="form-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={skipDuplicates}
              onChange={(e) => setSkipDuplicates(e.target.checked)}
            />
            Pular itens duplicados
          </label>
        </div>

        <button
          className="btn"
          onClick={handleConvert}
          disabled={isConverting}
        >
          {isConverting ? 'Convertendo...' : 'Converter para Azure DevOps'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {result && (
        <div className="conversion-result">
          <h3>Resultado da Conversão</h3>
          <div className="result-stats">
            <div className="stat-card success">
              <div className="stat-value">{result.created_user_stories}</div>
              <div className="stat-label">User Stories Criadas</div>
            </div>
            <div className="stat-card success">
              <div className="stat-value">{result.created_tasks}</div>
              <div className="stat-label">Tasks Criadas</div>
            </div>
            <div className="stat-card warning">
              <div className="stat-value">{result.skipped_user_stories}</div>
              <div className="stat-label">User Stories Puladas</div>
            </div>
            <div className="stat-card warning">
              <div className="stat-value">{result.skipped_tasks}</div>
              <div className="stat-label">Tasks Puladas</div>
            </div>
          </div>

          {result.errors.length > 0 && (
            <div className="errors-list">
              <h4>Erros:</h4>
              <ul>
                {result.errors.map((err, idx) => (
                  <li key={idx} className="error">{err}</li>
                ))}
              </ul>
            </div>
          )}

          {result.work_items.length > 0 && (
            <div className="work-items-list">
              <h4>Work Items Criados:</h4>
              <ul>
                {result.work_items.map((wi) => (
                  <li key={wi.id}>
                    <a
                      href={wi.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      #{wi.id} - {wi.fields['System.Title']}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

