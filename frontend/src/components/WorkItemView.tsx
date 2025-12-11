import { useState } from 'react';
import { apiService, WorkItem } from '../services/api';
import './WorkItemView.css';

interface AnalysisResult {
  id: number;
  type: string;
  title: string;
  cliente?: string;
  user_stories: any[];
  tasks: any[];
  assigned_to?: any;
  start_date?: string;
  target_date?: string;
}

export default function WorkItemView() {
  const [searchTitle, setSearchTitle] = useState('');
  const [workItemType, setWorkItemType] = useState('');
  const [areaPath, setAreaPath] = useState('');
  const [workItems, setWorkItems] = useState<WorkItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [workItemId, setWorkItemId] = useState('');
  const [selectedWorkItem, setSelectedWorkItem] = useState<WorkItem | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);

  const handleSearch = async () => {
    if (!searchTitle.trim()) {
      setError('Por favor, informe o título para buscar');
      return;
    }

    setIsLoading(true);
    setError(null);
    setWorkItems([]);

    try {
      const data = await apiService.searchWorkItems(
        searchTitle,
        workItemType || undefined,
        areaPath || undefined
      );
      setWorkItems(data);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Erro ao buscar Work Items';
      console.error('Erro ao buscar Work Items:', err);
      setError(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGetById = async () => {
    if (!workItemId.trim()) {
      setError('Por favor, informe o ID do Work Item');
      return;
    }

    setIsLoading(true);
    setError(null);
    setSelectedWorkItem(null);
    setAnalysisResult(null);

    try {
      const data = await apiService.getWorkItem(parseInt(workItemId));
      setSelectedWorkItem(data);
      
      // Busca análise completa também
      try {
        const analysis = await apiService.analyzeWorkItem(parseInt(workItemId));
        setAnalysisResult(analysis);
      } catch (analysisErr) {
        // Ignora erro de análise, mostra apenas o Work Item básico
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Erro ao buscar Work Item';
      console.error('Erro ao buscar Work Item:', err);
      setError(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="work-item-view">
      <h2>Buscar Work Items</h2>

      <div className="search-forms">
        <div className="glass-card">
          <h3>Buscar por Título</h3>
          <div className="search-form">
            <div className="form-group">
              <label htmlFor="search-title">Título</label>
              <input
                id="search-title"
                type="text"
                value={searchTitle}
                onChange={(e) => setSearchTitle(e.target.value)}
                placeholder="Digite o título do Work Item"
              />
            </div>
            <div className="form-group">
              <label htmlFor="work-item-type">Tipo (opcional)</label>
              <select
                id="work-item-type"
                value={workItemType}
                onChange={(e) => setWorkItemType(e.target.value)}
              >
                <option value="">Todos</option>
                <option value="User Story">User Story</option>
                <option value="Task">Task</option>
                <option value="Feature">Feature</option>
                <option value="Epic">Epic</option>
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="search-area-path">Area Path (opcional)</label>
              <input
                id="search-area-path"
                type="text"
                value={areaPath}
                onChange={(e) => setAreaPath(e.target.value)}
                placeholder="Ex: Quali IT - Inovação e Tecnologia\\Cliente"
              />
            </div>
            <button className="btn" onClick={handleSearch} disabled={isLoading}>
              Buscar
            </button>
          </div>
        </div>

        <div className="glass-card">
          <h3>Buscar por ID</h3>
          <div className="search-form">
            <div className="form-group">
              <label htmlFor="work-item-id">ID do Work Item</label>
              <input
                id="work-item-id"
                type="number"
                value={workItemId}
                onChange={(e) => setWorkItemId(e.target.value)}
                placeholder="Digite o ID"
              />
            </div>
            <button className="btn" onClick={handleGetById} disabled={isLoading}>
              Buscar
            </button>
          </div>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {isLoading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>Buscando...</p>
        </div>
      )}

      {/* Lista de resultados da busca */}
      {workItems.length > 0 && (
        <div className="work-items-results glass-card">
          <h3>Resultados ({workItems.length})</h3>
          <div className="work-items-list">
            {workItems.map((wi) => (
              <div key={wi.id} className="work-item-card compact">
                <div className="work-item-header">
                  <a
                    href={wi.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="work-item-link"
                  >
                    #{wi.id} - {wi.fields['System.Title']}
                  </a>
                  <span className="work-item-type">
                    {wi.fields['System.WorkItemType']}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Work Item selecionado - Formato Compacto */}
      {(analysisResult || selectedWorkItem) && (
        <div className="work-item-detail glass-card">
          <div className="work-item-header-compact">
            <div className="work-item-id-title-compact">
              <span className="work-item-id-compact">
                #{analysisResult?.id || selectedWorkItem?.id}
              </span>
              <span className="work-item-title-compact">
                {analysisResult?.title || selectedWorkItem?.fields['System.Title']}
              </span>
              </div>
            {(selectedWorkItem || analysisResult) && (
              <a
                href={selectedWorkItem?.url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-link-small"
              >
                Ver no DevOps →
              </a>
              )}
            </div>

          {/* User Stories */}
          {analysisResult?.user_stories && analysisResult.user_stories.length > 0 && (
            <div className="related-items-compact">
                <h4>User Stories ({analysisResult.user_stories.length})</h4>
              <div className="items-list-compact">
                  {analysisResult.user_stories.map((us) => (
                  <div key={us.id} className="item-compact">
                    <span className="item-id-compact">#{us.id}</span>
                    <span className="item-title-compact">{us.title || us.name}</span>
                        {us.state && (
                      <span className={`status-badge-compact status-${us.state?.toLowerCase().replace(/\s+/g, '-')}`}>
                        {us.state}
                      </span>
                        )}
                    </div>
                  ))}
                </div>
              </div>
            )}

          {/* Tasks */}
          {analysisResult?.tasks && analysisResult.tasks.length > 0 && (
            <div className="related-items-compact">
                <h4>Tasks ({analysisResult.tasks.length})</h4>
              <div className="items-list-compact">
                  {analysisResult.tasks.map((task) => (
                  <div key={task.id} className="item-compact">
                    <span className="item-id-compact">#{task.id}</span>
                    <span className="item-title-compact">{task.title || task.name}</span>
                        {task.state && (
                      <span className={`status-badge-compact status-${task.state?.toLowerCase().replace(/\s+/g, '-')}`}>
                        {task.state}
                      </span>
                        )}
                    </div>
                  ))}
              </div>
              </div>
            )}

          {(!analysisResult || 
            (!analysisResult.user_stories || analysisResult.user_stories.length === 0) &&
            (!analysisResult.tasks || analysisResult.tasks.length === 0)) && (
            <div className="empty-state-small">
              {isLoading ? 'Carregando User Stories e Tasks relacionadas...' : 'Nenhuma User Story ou Task relacionada encontrada'}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
