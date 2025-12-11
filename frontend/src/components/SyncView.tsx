import { useState, useEffect } from 'react';
import { apiService, WorkItem } from '../services/api';
import './SyncView.css';

interface SyncViewProps {
  fileId: string | null;
  filename: string | null;
  workItemId: string | null;
  parsedData?: any;
}

interface SyncResult {
  success: boolean;
  message: string;
  synced_items?: number;
}

export default function SyncView({ fileId, filename, workItemId, parsedData }: SyncViewProps) {
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
    if (!fileId) {
      setError('Nenhum arquivo .mpp carregado');
      return;
    }

    setSyncDirection('mpp-to-devops');
    setSyncStatus('Sincronizando arquivo .mpp para Azure DevOps...');
    setSyncResult(null);
    setError(null);

    try {
      // Usa o workItemId como parent_feature_id para vincular User Stories à Feature
      // skipDuplicates=true: verifica duplicatas antes de criar
      // update_existing=true: atualiza itens existentes em vez de criar duplicatas
      const parentFeatureId = workItemId ? parseInt(workItemId) : undefined;
      const result = await apiService.convertToDevOps(
        fileId, 
        undefined, 
        undefined, 
        true, // skipDuplicates=true: verifica duplicatas
        parentFeatureId,
        true // update_existing=true: atualiza itens existentes
      );
      
      const totalCreated = result.created_user_stories + result.created_tasks;
      const totalUpdated = (result.updated_user_stories || 0) + (result.updated_tasks || 0);
      const totalSkipped = result.skipped_user_stories + result.skipped_tasks;
      
      let message = 'Sincronização concluída!\n';
      if (totalCreated > 0) {
        message += `✓ ${result.created_user_stories} User Stories criadas\n`;
        message += `✓ ${result.created_tasks} Tasks criadas\n`;
      }
      if (totalUpdated > 0) {
        message += `\n✓ ${result.updated_user_stories || 0} User Stories atualizadas\n`;
        message += `✓ ${result.updated_tasks || 0} Tasks atualizadas\n`;
      }
      if (totalSkipped > 0) {
        message += `\n${result.skipped_user_stories} User Stories já existiam (mantidas)\n`;
        message += `${result.skipped_tasks} Tasks já existiam (mantidas)`;
      }
      if (totalCreated === 0 && totalUpdated === 0 && totalSkipped === 0) {
        message = 'Nenhum item para sincronizar. Todos os itens do arquivo .mpp já existem no Azure DevOps.';
      }
      
      setSyncResult({
        success: true,
        message: message,
        synced_items: totalCreated
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

  if (!fileId) {
    return (
      <div className="sync-view">
        <div className="glass-card">
          <div className="empty-state">
            <h3>Sincronização .MPP ↔ DevOps</h3>
            <p>Por favor, faça upload de um arquivo .mpp na aba "Upload File .MPP" para habilitar a sincronização.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="sync-view">
      <div className="view-header glass-card">
        <div className="header-content">
          <h2>Sincronização .MPP ↔ DevOps</h2>
          {filename && (
            <div className="file-info">
              <span className="file-name">Arquivo: {filename}</span>
              {workItemId && (
                <span className="work-item-badge">Work Item ID: {workItemId}</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Dados do Work Item do DevOps */}
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
                  href={`https://dev.azure.com/qualiit/Quali%20IT%20-%20Inova%C3%A7%C3%A3o%20e%20Tecnologia/_boards/board/t/Quali%20IT%20!%20Gestao%20de%20Projeto/Features?workitem=${workItem.id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-link-small"
                >
                  Ver no DevOps →
                </a>
              </div>

              {/* User Stories */}
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

              {/* Tasks */}
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

      {/* Comparação MPP vs DevOps */}
      {parsedData && analysisResult && (
        <div className="comparison-section glass-card">
          <h3>Comparação: Arquivo .mpp vs Azure DevOps</h3>
          <div className="comparison-grid">
            <div className="comparison-item">
              <h4>📄 Arquivo .mpp</h4>
              <div className="comparison-stats">
                <div className="stat-item">
                  <span className="stat-label">User Stories:</span>
                  <span className="stat-value">{parsedData.user_stories?.length || 0}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Tasks:</span>
                  <span className="stat-value">{parsedData.tasks?.length || 0}</span>
                </div>
              </div>
            </div>
            <div className="comparison-item">
              <h4>☁️ Azure DevOps</h4>
              <div className="comparison-stats">
                <div className="stat-item">
                  <span className="stat-label">User Stories:</span>
                  <span className="stat-value">{analysisResult.user_stories?.length || 0}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Tasks:</span>
                  <span className="stat-value">
                    {(analysisResult.user_stories?.reduce((acc: number, us: any) => acc + (us.tasks?.length || 0), 0) || 0) + 
                     (analysisResult.tasks?.length || 0)}
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div className="comparison-note">
            <p>
              A sincronização criará apenas os itens do arquivo .mpp que ainda não existem no Azure DevOps.
              Itens já existentes serão mantidos.
            </p>
          </div>
        </div>
      )}

      {/* Sincronização */}
      <div className="sync-section glass-card">
        <h3>Sincronização</h3>
        <p className="sync-description">
          Sincronize o arquivo .mpp com o Azure DevOps. Apenas itens que não existem no DevOps serão criados.
        </p>
        <div className="sync-buttons">
          <button
            className="btn btn-primary"
            onClick={handleSyncMPPToDevOps}
            disabled={!!syncDirection || !!syncStatus || !fileId}
          >
            🔄 Sincronizar .mpp → DevOps
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleSyncDevOpsToMPP}
            disabled={!!syncDirection || !!syncStatus || !workItem || !workItemId}
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
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontFamily: 'inherit' }}>
              {syncResult.message}
            </pre>
            {syncResult.synced_items !== undefined && syncResult.synced_items > 0 && (
              <p className="sync-count" style={{ marginTop: '0.5rem', marginBottom: 0 }}>
                Total: {syncResult.synced_items} itens criados
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

