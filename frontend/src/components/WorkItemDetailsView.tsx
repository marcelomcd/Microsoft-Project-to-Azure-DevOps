import { useState, useEffect } from 'react';
import { apiService, WorkItem, UploadResponse, ConversionResult } from '../services/api';
import './WorkItemDetailsView.css';

interface WorkItemDetailsViewProps {
  uploadedFile?: UploadResponse | null;
}

export default function WorkItemDetailsView({ uploadedFile }: WorkItemDetailsViewProps) {
  const [workItem, setWorkItem] = useState<WorkItem | null>(null);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<ConversionResult | null>(null);

  // Log inicial quando o componente é montado
  useEffect(() => {
    console.log('WorkItemDetailsView - Componente montado/atualizado');
    console.log('WorkItemDetailsView - Props recebidas:', { uploadedFile });
  }, []);

  // Busca automaticamente o Work Item ID do arquivo carregado
  useEffect(() => {
    console.log('WorkItemDetailsView - uploadedFile completo:', uploadedFile);
    console.log('WorkItemDetailsView - work_item_id:', uploadedFile?.work_item_id);
    console.log('WorkItemDetailsView - work_item_id type:', typeof uploadedFile?.work_item_id);
    console.log('WorkItemDetailsView - work_item_id truthy?', !!uploadedFile?.work_item_id);
    console.log('WorkItemDetailsView - work_item_id !== null?', uploadedFile?.work_item_id !== null);
    console.log('WorkItemDetailsView - work_item_id !== undefined?', uploadedFile?.work_item_id !== undefined);
    
    // Extrai work_item_id (pode ser string ou número)
    const workItemId = uploadedFile?.work_item_id;
    
    // Verifica se work_item_id existe e é válido
    if (workItemId !== null && workItemId !== undefined && workItemId !== '') {
      // Converte para string se necessário
      const workItemIdStr = String(workItemId).trim();
      console.log('WorkItemDetailsView - workItemIdStr após conversão:', workItemIdStr);
      
      if (workItemIdStr && workItemIdStr !== 'null' && workItemIdStr !== 'undefined' && workItemIdStr !== '') {
        console.log('WorkItemDetailsView - Carregando Work Item ID:', workItemIdStr);
        loadWorkItem(workItemIdStr);
      } else {
        // Limpa dados se work_item_id é inválido
        console.log('WorkItemDetailsView - work_item_id inválido após conversão');
        setWorkItem(null);
        setAnalysisResult(null);
        setError('Work Item ID não encontrado no arquivo carregado');
      }
    } else if (uploadedFile) {
      // Limpa dados se não há arquivo ou não tem work_item_id
      console.log('WorkItemDetailsView - uploadedFile existe mas work_item_id é null/undefined/vazio');
      setWorkItem(null);
      setAnalysisResult(null);
      setError(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uploadedFile?.work_item_id, uploadedFile?.filename]);

  const loadWorkItem = async (workItemId: string | number) => {
    // Converte para string e valida
    const workItemIdStr = String(workItemId).trim();
    if (!workItemIdStr || workItemIdStr === 'null' || workItemIdStr === 'undefined' || workItemIdStr === '') {
      setError('Work Item ID não encontrado no arquivo carregado');
      return;
    }

    // Evita chamadas duplicadas
    if (isLoading) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setWorkItem(null);
    setAnalysisResult(null);

    try {
      const itemId = parseInt(workItemIdStr);
      if (isNaN(itemId)) {
        throw new Error(`Work Item ID inválido: "${workItemIdStr}"`);
      }
      
      console.log('WorkItemDetailsView - Carregando Work Item ID:', itemId);
      console.log('WorkItemDetailsView - Fazendo chamada para apiService.getWorkItem...');

      const data = await apiService.getWorkItem(itemId);
      console.log('WorkItemDetailsView - Work Item recebido:', data);
      setWorkItem(data);
      
      // Busca análise completa com User Stories e Tasks (incluindo Tasks filhas de cada User Story)
      console.log('WorkItemDetailsView - Fazendo chamada para apiService.analyzeWorkItem...');
      try {
        const analysis = await apiService.analyzeWorkItem(itemId);
        console.log('WorkItemDetailsView - Análise recebida:', analysis);
        setAnalysisResult(analysis);
      } catch (analysisErr: any) {
        console.error('WorkItemDetailsView - Erro ao buscar análise:', analysisErr);
        console.error('WorkItemDetailsView - Detalhes do erro:', analysisErr.response?.data || analysisErr.message);
        // Não define erro aqui, apenas mostra o Work Item básico
        setError(null);
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Erro ao buscar Work Item';
      console.error('WorkItemDetailsView - Erro ao buscar Work Item:', err);
      console.error('WorkItemDetailsView - Detalhes do erro:', err.response?.data || err.message);
      setError(errorMsg);
    } finally {
      setIsLoading(false);
      console.log('WorkItemDetailsView - Carregamento finalizado');
    }
  };

  // Extrai informações do responsável técnico
  const getResponsavelTecnico = () => {
    if (!workItem) return '';
    const responsavel = workItem.fields['Custom.ResponsavelTecnico'];
    if (!responsavel) return '';
    if (typeof responsavel === 'object') {
      return responsavel.displayName || responsavel.nome || '';
    }
    return String(responsavel);
  };

  // Extrai informações do criado por
  const getCriadoPor = () => {
    if (!workItem) return '';
    const createdBy = workItem.fields['System.CreatedBy'];
    if (!createdBy) return '';
    if (typeof createdBy === 'object') {
      return createdBy.displayName || createdBy.nome || '';
    }
    return String(createdBy);
  };

  // Formata data
  const formatDate = (dateStr: string | undefined) => {
    if (!dateStr) return '';
    try {
      return new Date(dateStr).toLocaleDateString('pt-BR');
    } catch {
      return dateStr;
    }
  };

  // Sincroniza arquivo .mpp para Azure DevOps
  const handleSyncToDevOps = async () => {
    if (!uploadedFile?.file_id || !uploadedFile?.work_item_id) {
      setError('Arquivo ou Work Item ID não encontrado');
      return;
    }

    setIsSyncing(true);
    setError(null);
    setSyncResult(null);

    try {
      const parentFeatureId = parseInt(String(uploadedFile.work_item_id));
      if (isNaN(parentFeatureId)) {
        throw new Error('Work Item ID inválido');
      }

      const result = await apiService.convertToDevOps(
        uploadedFile.file_id,
        undefined,
        undefined,
        true, // skipDuplicates: verifica duplicatas
        parentFeatureId,
        true // update_existing: atualiza itens existentes
      );

      setSyncResult(result);
      
      // Recarrega Work Item após sincronização
      if (uploadedFile.work_item_id) {
        setTimeout(() => {
          loadWorkItem(String(uploadedFile.work_item_id));
        }, 1000);
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Erro ao sincronizar';
      setError(errorMsg);
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div className="work-item-details-view">
      <div className="view-header glass-card">
        <div className="header-content">
          <h2>📋 Azure DevOps User Stories and Task's</h2>
          {uploadedFile?.work_item_id && (
            <div className="work-item-badge-header">
              <span className="icon">🔗</span>
              <span>Work Item ID: {uploadedFile.work_item_id}</span>
            </div>
          )}
          {uploadedFile?.file_id && uploadedFile?.work_item_id && (
            <button
              className="btn btn-primary"
              onClick={handleSyncToDevOps}
              disabled={isSyncing || isLoading}
              style={{ marginLeft: 'auto' }}
            >
              {isSyncing ? '🔄 Sincronizando...' : '🔄 Sincronizar .mpp → DevOps'}
            </button>
          )}
        </div>
      </div>


      {!uploadedFile && !isLoading && (
        <div className="empty-state glass-card">
          <p>⚠️ Por favor, carregue um arquivo .mpp na aba "Upload File .MPP" para visualizar as informações do Work Item.</p>
        </div>
      )}

      {uploadedFile && !uploadedFile.work_item_id && !isLoading && !error && (
        <div className="empty-state glass-card">
          <p>⚠️ O arquivo carregado não possui um Work Item ID associado.</p>
          <p>Nome do arquivo: <strong>{uploadedFile.filename}</strong></p>
          <p style={{ marginTop: '10px', fontSize: '0.9em', color: '#666' }}>
            O Work Item ID deve ser os <strong>5 primeiros dígitos</strong> do nome do arquivo.
            <br />
            Exemplo: Para o arquivo <code>15404 025543-02 - Camil.mpp</code>, o Work Item ID será <code>15404</code>.
          </p>
        </div>
      )}

      {error && !isLoading && (
        <div className="error glass-card">
          <p><strong>Erro:</strong> {error}</p>
        </div>
      )}

      {isLoading && (
        <div className="loading glass-card">
          <div className="spinner"></div>
          <p>Carregando Work Item do Azure DevOps...</p>
          {uploadedFile?.work_item_id && (
            <p style={{ marginTop: '10px', fontSize: '0.9em', color: '#666' }}>
              Work Item ID: <strong>{uploadedFile.work_item_id}</strong>
            </p>
          )}
        </div>
      )}

      {workItem && (
        <div className="work-item-info glass-card">
          <div className="work-item-header-section">
            <div className="work-item-id-title">
              <div className="work-item-id-container">
                <span className="icon">🆔</span>
                <span className="work-item-id">#{workItem.id}</span>
              </div>
              <div className="work-item-title-container">
                <span className="icon">📝</span>
                <span className="work-item-title">{workItem.fields['System.Title']}</span>
              </div>
            </div>
            <a
              href={`https://dev.azure.com/qualiit/Quali%20IT%20-%20Inova%C3%A7%C3%A3o%20e%20Tecnologia/_boards/board/t/Quali%20IT%20!%20Gestao%20de%20Projeto/Features?workitem=${workItem.id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-link-small"
            >
              🔗 Ver no Azure DevOps →
            </a>
          </div>

          <div className="work-item-details-list">
            {/* Ordem conforme especificado pelo usuário */}
            
            {/* 1. Work Item ID = System.Title (já exibido no header) */}
            {/* 2. Número de Proposta */}
            {workItem.fields['Custom.NumeroProposta'] && (
              <div className="detail-row">
                <span className="icon">📄</span>
                <strong>Número de Proposta:</strong>
                <span>{workItem.fields['Custom.NumeroProposta']}</span>
              </div>
            )}
            
            {/* 3. Parent = texto após última barra do Area Path */}
            {workItem.fields['System.AreaPath'] && (
              <div className="detail-row">
                <span className="icon">📁</span>
                <strong>Parent:</strong>
                <span>{workItem.fields['System.AreaPath'].split('\\').pop() || workItem.fields['System.AreaPath'].split('/').pop()}</span>
              </div>
            )}
            
            {/* 4. Responsável Técnico */}
            {getResponsavelTecnico() && (
              <div className="detail-row">
                <span className="icon">👤</span>
                <strong>Responsável Técnico:</strong>
                <span>{getResponsavelTecnico()}</span>
              </div>
            )}
            
            {/* 5. Horas do Projeto */}
            {workItem.fields['Custom.Horas Projeto'] && (
              <div className="detail-row">
                <span className="icon">⏱️</span>
                <strong>Horas do Projeto:</strong>
                <span>{workItem.fields['Custom.Horas Projeto']}</span>
              </div>
            )}
            
            {/* 6. Data Fim Original */}
            {workItem.fields['Microsoft.VSTS.Scheduling.TargetDate'] && (
              <div className="detail-row">
                <span className="icon">📅</span>
                <strong>Data Fim Original:</strong>
                <span>{formatDate(workItem.fields['Microsoft.VSTS.Scheduling.TargetDate'])}</span>
              </div>
            )}
            
            {/* 7. Criado Por */}
            {getCriadoPor() && (
              <div className="detail-row">
                <span className="icon">✍️</span>
                <strong>Criado Por:</strong>
                <span>{getCriadoPor()}</span>
              </div>
            )}
            
            {/* 8. Criticidade */}
            {workItem.fields['Custom.Criticidade'] && (
              <div className="detail-row">
                <span className="icon">⚠️</span>
                <strong>Criticidade:</strong>
                <span>{workItem.fields['Custom.Criticidade']}</span>
              </div>
            )}
            
            {/* 9. Pendência */}
            {workItem.fields['Custom.SituacaoPendenteList'] && (
              <div className="detail-row">
                <span className="icon">📌</span>
                <strong>Pendência:</strong>
                <span>{workItem.fields['Custom.SituacaoPendenteList']}</span>
              </div>
            )}
            
            {/* 10. Data Liberada para Homologação */}
            {workItem.fields['Custom.DataLiberadaHomologacao'] && (
              <div className="detail-row">
                <span className="icon">✅</span>
                <strong>Data Liberada para Homologação:</strong>
                <span>{formatDate(workItem.fields['Custom.DataLiberadaHomologacao'])}</span>
              </div>
            )}
            
            {/* 11. User Story = Quantidade */}
            <div className="detail-row">
              <span className="icon">📚</span>
              <strong>User Story:</strong>
              <span>{analysisResult?.user_stories?.length || 0}</span>
            </div>
            
            {/* 12. Task = Quantidade total (aninhadas + diretas) */}
            <div className="detail-row">
              <span className="icon">✓</span>
              <strong>Task:</strong>
              <span>
                {(analysisResult?.user_stories?.reduce((acc: number, us: any) => acc + (us.tasks?.length || 0), 0) || 0) + 
                 (analysisResult?.tasks?.length || 0)}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* User Stories com suas Tasks em formato hierárquico */}
      {analysisResult && analysisResult.user_stories && analysisResult.user_stories.length > 0 && (
        <div className="related-items-section glass-card">
          <h3>📚 User Stories ({analysisResult.user_stories.length})</h3>
          <div className="items-list">
            {analysisResult.user_stories.map((us: any) => (
              <div key={us.id} className="item-card user-story-card">
                <div className="item-header">
                  <span className="item-id">#{us.id}</span>
                  <span className="item-title">{us.title || us.name || 'Sem título'}</span>
                  {us.state && (
                    <span className={`status-badge status-${us.state?.toLowerCase().replace(/\s+/g, '-')}`}>
                      {us.state}
                    </span>
                  )}
                </div>
                
                {/* Informações adicionais da User Story */}
                {(us.assigned_to || us.start_date || us.target_date) && (
                  <div className="item-details">
                    {us.assigned_to && (
                      <div className="item-detail">
                        <span className="icon">👤</span>
                        <strong>Atribuído a:</strong> {us.assigned_to.nome || us.assigned_to.displayName || us.assigned_to.email}
                      </div>
                    )}
                    {us.start_date && (
                      <div className="item-detail">
                        <span className="icon">📅</span>
                        <strong>Início:</strong> {formatDate(us.start_date)}
                      </div>
                    )}
                    {us.target_date && (
                      <div className="item-detail">
                        <span className="icon">📅</span>
                        <strong>Fim:</strong> {formatDate(us.target_date)}
                      </div>
                    )}
                  </div>
                )}
                
                {/* Tasks filhas desta User Story - formato hierárquico */}
                {us.tasks && us.tasks.length > 0 && (
                  <div className="tasks-container">
                    <div className="tasks-header">
                      <span className="icon">✓</span>
                      <strong>Tasks ({us.tasks.length}):</strong>
                    </div>
                    <div className="tasks-list nested-tasks-list">
                      {us.tasks.map((task: any) => (
                        <div key={task.id} className="task-item nested-task-card">
                          <div className="task-header">
                            <span className="task-id">#{task.id}</span>
                            <span className="task-title">{task.title || task.name || 'Sem título'}</span>
                            {task.state && (
                              <span className={`status-badge status-${task.state?.toLowerCase().replace(/\s+/g, '-')}`}>
                                {task.state}
                              </span>
                            )}
                          </div>
                          {(task.assigned_to || task.start_date || task.target_date) && (
                            <div className="task-details">
                              {task.assigned_to && (
                                <div className="task-detail">
                                  <span className="icon">👤</span>
                                  <strong>Atribuído a:</strong> {task.assigned_to.nome || task.assigned_to.displayName || task.assigned_to.email}
                                </div>
                              )}
                              {task.start_date && (
                                <div className="task-detail">
                                  <span className="icon">📅</span>
                                  <strong>Início:</strong> {formatDate(task.start_date)}
                                </div>
                              )}
                              {task.target_date && (
                                <div className="task-detail">
                                  <span className="icon">📅</span>
                                  <strong>Fim:</strong> {formatDate(task.target_date)}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tasks */}
      {analysisResult && analysisResult.tasks && analysisResult.tasks.length > 0 && (
        <div className="related-items-section glass-card">
          <h3>Tasks ({analysisResult.tasks.length})</h3>
          <div className="items-list">
            {analysisResult.tasks.map((task: any) => (
              <div key={task.id} className="item-card">
                <div className="item-header">
                  <span className="item-id">#{task.id}</span>
                  <span className="item-title">{task.title || task.name}</span>
                  {task.state && (
                    <span className={`status-badge status-${task.state?.toLowerCase().replace(/\s+/g, '-')}`}>
                      {task.state}
                    </span>
                  )}
                </div>
                {task.assigned_to && (
                  <div className="item-detail">
                    <strong>Atribuído a:</strong> {task.assigned_to.nome || task.assigned_to.displayName || task.assigned_to.email}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {workItem && analysisResult && 
       (!analysisResult.user_stories || analysisResult.user_stories.length === 0) &&
       (!analysisResult.tasks || analysisResult.tasks.length === 0) && (
        <div className="empty-state glass-card">
          <p>Nenhuma User Story ou Task relacionada encontrada</p>
        </div>
      )}

      {/* Resultado da sincronização */}
      {syncResult && (
        <div className="glass-card" style={{ marginTop: '1rem' }}>
          <h3>Sincronização Concluída</h3>
          <div style={{ marginTop: '1rem' }}>
            {syncResult.created_user_stories > 0 && (
              <p>✓ {syncResult.created_user_stories} User Stories criadas</p>
            )}
            {syncResult.created_tasks > 0 && (
              <p>✓ {syncResult.created_tasks} Tasks criadas</p>
            )}
            {(syncResult.updated_user_stories || 0) > 0 && (
              <p>✓ {syncResult.updated_user_stories} User Stories atualizadas</p>
            )}
            {(syncResult.updated_tasks || 0) > 0 && (
              <p>✓ {syncResult.updated_tasks} Tasks atualizadas</p>
            )}
            {syncResult.skipped_user_stories > 0 && (
              <p>⊘ {syncResult.skipped_user_stories} User Stories já existiam (mantidas)</p>
            )}
            {syncResult.skipped_tasks > 0 && (
              <p>⊘ {syncResult.skipped_tasks} Tasks já existiam (mantidas)</p>
            )}
            {syncResult.errors && syncResult.errors.length > 0 && (
              <div style={{ marginTop: '1rem', color: '#d32f2f' }}>
                <strong>Erros:</strong>
                <ul>
                  {syncResult.errors.map((err, idx) => (
                    <li key={idx}>{err}</li>
                  ))}
                </ul>
              </div>
            )}
            {syncResult.created_user_stories === 0 && 
             syncResult.created_tasks === 0 && 
             (syncResult.updated_user_stories || 0) === 0 && 
             (syncResult.updated_tasks || 0) === 0 && 
             syncResult.skipped_user_stories === 0 && 
             syncResult.skipped_tasks === 0 && (
              <p>Nenhum item para sincronizar. Todos os itens do arquivo .mpp já existem no Azure DevOps.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

