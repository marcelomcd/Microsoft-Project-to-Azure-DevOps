import { useState, useEffect } from 'react';
import { apiService, WorkItem } from '../services/api';
import './MPPFileView.css';

interface MPPFileViewProps {
  fileId: string;
  filename: string;
  workItemId: string | null;
  parsedData: any;
}

interface SyncResult {
  success: boolean;
  message: string;
  synced_items?: number;
}

export default function MPPFileView({ fileId, filename, workItemId, parsedData }: MPPFileViewProps) {
  const [workItem, setWorkItem] = useState<WorkItem | null>(null);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncDirection, setSyncDirection] = useState<'mpp-to-devops' | 'devops-to-mpp' | null>(null);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);

  // Busca Work Item automaticamente quando há ID
  useEffect(() => {
    if (workItemId) {
      loadWorkItem();
    }
  }, [workItemId]);

  const loadWorkItem = async () => {
    if (!workItemId) return;

    setIsLoading(true);
    setError(null);

    try {
      const itemId = parseInt(workItemId);
      const data = await apiService.getWorkItem(itemId);
      setWorkItem(data);
      
      // Busca análise completa com User Stories e Tasks
      try {
        const analysis = await apiService.analyzeWorkItem(itemId);
        setAnalysisResult(analysis);
      } catch (analysisErr) {
        // Ignora erro de análise
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Erro ao carregar Work Item';
      console.error('Erro ao carregar Work Item:', err);
      setError(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSyncMPPToDevOps = async () => {
    setSyncDirection('mpp-to-devops');
    setSyncStatus('Sincronizando arquivo .mpp para Azure DevOps...');
    setSyncResult(null);
    setError(null);

    try {
      const result = await apiService.convertToDevOps(fileId, undefined, undefined, true);
      setSyncResult({
        success: true,
        message: `Sincronização concluída! ${result.created_user_stories} User Stories e ${result.created_tasks} Tasks criadas.`,
        synced_items: result.created_user_stories + result.created_tasks
      });
      setSyncStatus(null);
      // Recarrega Work Item após sync
      if (workItemId) {
        setTimeout(() => loadWorkItem(), 1000);
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Erro ao sincronizar';
      setSyncResult({
        success: false,
        message: errorMsg
      });
      setSyncStatus(null);
    }
  };

  const handleSyncDevOpsToMPP = async () => {
    if (!workItemId) {
      setError('Work Item ID necessário para sincronização');
      return;
    }

    setSyncDirection('devops-to-mpp');
    setSyncStatus('Sincronizando Azure DevOps para arquivo .mpp...');
    setSyncResult(null);
    setError(null);

    try {
      const result = await apiService.syncFromDevOps(parseInt(workItemId), true);
      const userStoriesCount = result.data?.user_stories?.length || 0;
      const tasksCount = result.data?.tasks?.length || 0;
      
      setSyncResult({
        success: true,
        message: `Sincronização concluída! ${userStoriesCount} User Stories e ${tasksCount} Tasks sincronizadas do Azure DevOps.`,
        synced_items: userStoriesCount + tasksCount
      });
      setSyncStatus(null);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Erro ao sincronizar';
      setSyncResult({
        success: false,
        message: errorMsg
      });
      setSyncStatus(null);
    }
  };

  const project = parsedData?.project;
  const userStories = parsedData?.user_stories || [];
  const tasks = parsedData?.tasks || [];

  return (
    <div className="mpp-file-view">
      {/* Header compacto */}
      <div className="view-header glass-card">
        <div className="header-content">
          <div>
            <h3>Arquivo: {filename}</h3>
            {workItemId && (
              <div className="work-item-badge">Work Item ID: {workItemId}</div>
            )}
          </div>
        </div>
      </div>

      {/* Dados do Work Item do DevOps - Formato Compacto */}
      {workItemId && (
        <div className="devops-content glass-card">
          <div className="section-header">
            <h3>Work Item no Azure DevOps</h3>
            <button className="btn btn-secondary btn-small" onClick={loadWorkItem} disabled={isLoading}>
              Atualizar
            </button>
          </div>

          {isLoading && (
            <div className="loading-inline">
              <div className="spinner-small"></div>
              <span>Carregando...</span>
            </div>
          )}

          {error && <div className="error-inline">{error}</div>}

          {workItem && (
            <div className="work-item-compact">
              <div className="work-item-header-compact">
                <div className="work-item-id-title-compact">
                  <span className="work-item-id-compact">#{workItem.id}</span>
                  <span className="work-item-title-compact">{workItem.fields['System.Title']}</span>
                </div>
                <a
                  href={workItem.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-link-small"
                >
                  Ver no DevOps →
                </a>
              </div>

              {/* User Stories - Lista Compacta */}
              {analysisResult && analysisResult.user_stories && analysisResult.user_stories.length > 0 && (
                <div className="related-items-compact">
                  <h4>User Stories ({analysisResult.user_stories.length})</h4>
                  <div className="items-list-compact">
                    {analysisResult.user_stories.map((us: any) => (
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

              {/* Tasks - Lista Compacta */}
              {analysisResult && analysisResult.tasks && analysisResult.tasks.length > 0 && (
                <div className="related-items-compact">
                  <h4>Tasks ({analysisResult.tasks.length})</h4>
                  <div className="items-list-compact">
                    {analysisResult.tasks.map((task: any) => (
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

              {analysisResult && 
               (!analysisResult.user_stories || analysisResult.user_stories.length === 0) &&
               (!analysisResult.tasks || analysisResult.tasks.length === 0) && (
                <div className="empty-state-small">
                  Nenhuma User Story ou Task relacionada encontrada
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Conteúdo do Arquivo MPP - Formato Compacto */}
      <div className="mpp-content glass-card">
        <h3>Conteúdo do Arquivo .mpp</h3>
        
        {project && (
          <div className="project-info-compact">
            <div className="info-row">
              <strong>Nome:</strong> {project.name}
            </div>
            {project.work_item_id && (
              <div className="info-row">
                <strong>Work Item ID:</strong> {project.work_item_id}
              </div>
            )}
          </div>
        )}

        <div className="content-sections-compact">
          {/* User Stories do Arquivo */}
          <div className="section-compact">
            <h4>User Stories ({userStories.length})</h4>
            {userStories.length === 0 ? (
              <p className="empty-state-small">Nenhuma User Story encontrada no arquivo</p>
            ) : (
              <div className="items-list-compact">
                {userStories.map((us: any, idx: number) => (
                  <div key={idx} className="item-compact">
                    <span className="item-title-compact">{us.name || us.title}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Tasks do Arquivo */}
          <div className="section-compact">
            <h4>Tasks ({tasks.length})</h4>
            {tasks.length === 0 ? (
              <p className="empty-state-small">Nenhuma Task encontrada no arquivo</p>
            ) : (
              <div className="items-list-compact">
                {tasks.map((task: any, idx: number) => (
                  <div key={idx} className="item-compact">
                    <span className="item-title-compact">{task.name || task.title}</span>
                    {task.resource_name && (
                      <span className="item-resource-compact">{task.resource_name}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Sincronização */}
      <div className="sync-section glass-card">
        <h3>Sincronização</h3>
        <div className="sync-buttons">
          <button
            className="btn btn-primary"
            onClick={handleSyncMPPToDevOps}
            disabled={!!syncDirection || !!syncStatus}
          >
            Sincronizar .mpp → DevOps
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleSyncDevOpsToMPP}
            disabled={!!syncDirection || !!syncStatus || !workItem}
          >
            Sincronizar DevOps → .mpp
          </button>
        </div>

        {syncStatus && (
          <div className="sync-status">
            <div className="spinner-small"></div>
            <p>{syncStatus}</p>
          </div>
        )}

        {syncResult && (
          <div className={`sync-result ${syncResult.success ? 'success' : 'error'}`}>
            <p>{syncResult.message}</p>
            {syncResult.synced_items !== undefined && syncResult.synced_items > 0 && (
              <p className="sync-count">{syncResult.synced_items} itens sincronizados</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
