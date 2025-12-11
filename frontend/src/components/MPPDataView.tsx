import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import './MPPDataView.css';

interface MPPDataViewProps {
  fileId: string;
  parsedData: any;
}

export default function MPPDataView({ fileId, parsedData }: MPPDataViewProps) {
  const [mppData, setMppData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadMPPData();
  }, [fileId, parsedData]);

  const loadMPPData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Se já temos parsedData, usa ele, senão busca do backend
      let dataToUse = parsedData;
      if (!dataToUse) {
        const data = await apiService.getParsedFile(fileId);
        dataToUse = data.parsed_data || data;
      }
      
      console.log('MPPDataView - loadMPPData - dataToUse:', dataToUse);
      console.log('MPPDataView - loadMPPData - dataToUse.project:', dataToUse?.project);
      console.log('MPPDataView - loadMPPData - dataToUse.project.tasks:', dataToUse?.project?.tasks);
      console.log('MPPDataView - loadMPPData - dataToUse.project.tasks length:', dataToUse?.project?.tasks?.length);
      
      setMppData(dataToUse);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Erro ao carregar dados do arquivo';
      console.error('Erro ao carregar dados do MPP:', err);
      setError(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>Carregando dados do arquivo...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <div className="error">{error}</div>
        <button className="btn" onClick={loadMPPData}>
          Tentar Novamente
        </button>
      </div>
    );
  }

  if (!mppData) {
    return (
      <div className="empty-state glass-card">
        <p>Nenhum dado encontrado no arquivo.</p>
      </div>
    );
  }

  const project = mppData?.project || parsedData?.project || {};
  const projectName = project?.name || 'Projeto Sem Nome';
  
  console.log('MPPDataView - mppData:', mppData);
  console.log('MPPDataView - project:', project);
  console.log('MPPDataView - parsedData:', parsedData);
  console.log('MPPDataView - project.tasks:', project?.tasks);
  console.log('MPPDataView - project.tasks length:', project?.tasks?.length);
  
  // Pega todas as tarefas do projeto (incluindo summary tasks)
  // Prioriza project.tasks que contém a estrutura completa do arquivo .mpp
  let allTasks: any[] = [];
  
  // Tenta diferentes caminhos para encontrar as tarefas
  if (project?.tasks && Array.isArray(project.tasks) && project.tasks.length > 0) {
    allTasks = project.tasks;
    console.log('MPPDataView - Usando project.tasks:', allTasks.length);
  } else if (mppData?.project?.tasks && Array.isArray(mppData.project.tasks) && mppData.project.tasks.length > 0) {
    allTasks = mppData.project.tasks;
    console.log('MPPDataView - Usando mppData.project.tasks:', allTasks.length);
  } else if (parsedData?.project?.tasks && Array.isArray(parsedData.project.tasks) && parsedData.project.tasks.length > 0) {
    allTasks = parsedData.project.tasks;
    console.log('MPPDataView - Usando parsedData.project.tasks:', allTasks.length);
  } else if (mppData?.tasks && Array.isArray(mppData.tasks) && mppData.tasks.length > 0) {
    allTasks = mppData.tasks;
    console.log('MPPDataView - Usando mppData.tasks:', allTasks.length);
  } else if (mppData?.user_stories && Array.isArray(mppData.user_stories) && mppData.user_stories.length > 0) {
    allTasks = mppData.user_stories;
    console.log('MPPDataView - Usando mppData.user_stories:', allTasks.length);
  }
  
  // Se ainda não encontrou, tenta acessar diretamente do parsed_data
  if (allTasks.length === 0 && parsedData) {
    if (parsedData.project?.tasks && Array.isArray(parsedData.project.tasks)) {
      allTasks = parsedData.project.tasks;
      console.log('MPPDataView - Usando parsedData.project.tasks (fallback):', allTasks.length);
    } else if (parsedData.tasks && Array.isArray(parsedData.tasks)) {
      allTasks = parsedData.tasks;
      console.log('MPPDataView - Usando parsedData.tasks (fallback):', allTasks.length);
    } else if (parsedData.user_stories && Array.isArray(parsedData.user_stories)) {
      allTasks = parsedData.user_stories;
      console.log('MPPDataView - Usando parsedData.user_stories (fallback):', allTasks.length);
    }
  }
  
  console.log('MPPDataView - Total de tarefas encontradas:', allTasks.length);
  console.log('MPPDataView - allTasks sample:', allTasks.slice(0, 3));

  // Calcula percentual completo do projeto baseado nas tarefas
  let projectPercentComplete = 0;
  let projectStatus = 'No Prazo';
  let projectStartDate = null;
  let projectFinishDate = null;
  let totalWork = 0;
  
  if (allTasks.length > 0) {
    // Calcula média de percent_complete das tarefas
    const tasksWithPercent = allTasks.filter(t => t.percent_complete !== null && t.percent_complete !== undefined);
    if (tasksWithPercent.length > 0) {
      const sum = tasksWithPercent.reduce((acc, t) => acc + (t.percent_complete || 0), 0);
      projectPercentComplete = Math.round(sum / tasksWithPercent.length);
    }
    
    // Encontra datas mínima e máxima
    const dates = allTasks
      .filter(t => t.start_date || t.finish_date)
      .map(t => ({
        start: t.start_date ? new Date(t.start_date) : null,
        finish: t.finish_date ? new Date(t.finish_date) : null
      }));
    
    if (dates.length > 0) {
      const startDates = dates.map(d => d.start).filter(d => d !== null);
      const finishDates = dates.map(d => d.finish).filter(d => d !== null);
      
      if (startDates.length > 0) {
        projectStartDate = new Date(Math.min(...startDates.map(d => d!.getTime())));
      }
      if (finishDates.length > 0) {
        projectFinishDate = new Date(Math.max(...finishDates.map(d => d!.getTime())));
        
        // Verifica se está atrasado
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        projectFinishDate.setHours(0, 0, 0, 0);
        if (projectFinishDate < today && projectPercentComplete < 100) {
          projectStatus = 'Atrasada';
        } else if (projectPercentComplete === 100) {
          projectStatus = 'Concluída';
        } else if (projectPercentComplete > 0) {
          projectStatus = 'Em Andamento';
        }
      }
    }
    
    // Soma trabalho total
    allTasks.forEach(t => {
      if (t.work_hours) {
        totalWork += parseFloat(t.work_hours) || 0;
      } else if (t.work) {
        const workStr = String(t.work);
        const match = workStr.match(/(\d+\.?\d*)\s*hrs?/i);
        if (match) {
          totalWork += parseFloat(match[1]) || 0;
        }
      }
    });
  }
  
  // Prepara primeira linha = Título/Projeto
  const projectRow = {
    id: '0',
    name: projectName,
    type: 'Projeto',
    status: projectStatus,
    percent_complete: projectPercentComplete,
    start_date: projectStartDate,
    finish_date: projectFinishDate,
    work: totalWork > 0 ? `${totalWork.toFixed(1)} hrs` : '',
    duration: '',
    predecessors: '',
    resource_names: '',
    task_mode: 'Summary',
    level: 0,
    work_item_id: project?.work_item_id || '',
    work_item_title: '',
    work_item_type: '',
    work_item_state: '',
    is_project: true
  };

  // Usa todas as tarefas encontradas (prioriza project.tasks que contém estrutura completa)
  // Se não encontrou, combina user_stories e tasks
  let allTasksToDisplay: any[] = allTasks; // Já foi encontrado acima
  
  // Se ainda está vazio, tenta fallback
  if (allTasksToDisplay.length === 0) {
    // Fallback: combina User Stories e Tasks
    const userStories = mppData?.user_stories || parsedData?.user_stories || [];
    const tasks = mppData?.tasks || parsedData?.tasks || [];
    allTasksToDisplay = [...userStories, ...tasks];
    console.log('MPPDataView - Usando user_stories + tasks (fallback):', allTasksToDisplay.length);
    console.log('MPPDataView - userStories:', userStories.length, 'tasks:', tasks.length);
  } else {
    console.log('MPPDataView - Usando allTasks (estrutura original):', allTasksToDisplay.length);
  }
  
  // Prepara todas as tarefas para exibição mantendo a estrutura original
  const taskItems = allTasksToDisplay.map((task: any, idx: number) => {
    const resourceName = task.resource_name || task.resource_names || '';
    const hasResource = resourceName && resourceName.trim() !== '';
    const isSummary = task.summary || false;
    const percentComplete = task.percent_complete || 0;
    
    // Determina o tipo: se tem resource = Task, se não tem = User Story, se summary = Summary
    let taskType = 'Task';
    if (isSummary) {
      taskType = 'Summary';
    } else if (!hasResource) {
      taskType = 'User Story';
    }
    
    // Calcula status
    let status = 'Tarefa futura';
    if (percentComplete === 100) {
      status = 'Concluída';
    } else if (percentComplete > 0) {
      status = 'Em Andamento';
    } else {
      if (task.finish_date) {
        try {
          const finishDate = new Date(task.finish_date);
          const today = new Date();
          today.setHours(0, 0, 0, 0);
          finishDate.setHours(0, 0, 0, 0);
          if (finishDate < today && percentComplete < 100) {
            status = 'Atrasada';
          }
        } catch (e) {}
      }
    }
    
    return {
      id: task.id || String(idx + 1),
      name: task.name || 'Sem nome',
      type: taskType,
      status: status,
      percent_complete: percentComplete,
      start_date: task.start_date,
      finish_date: task.finish_date || task.end_date,
      work: task.work || task.work_hours || '',
      duration: task.duration || '',
      predecessors: task.predecessors || task.predecessor || '',
      resource_names: resourceName,
      task_mode: isSummary ? 'Summary' : (task.task_mode || 'Fixed Duration'),
      level: task.level || 0,
      work_item_id: task.work_item_id || '',
      work_item_title: task.work_item_title || '',
      work_item_type: task.work_item_type || '',
      work_item_state: task.work_item_state || '',
      is_project: false,
      is_user_story: !hasResource && !isSummary,
      summary: isSummary
    };
  });

  // Combina: Projeto (título) + todas as tarefas na ordem original
  const allItems = [projectRow, ...taskItems];

  const headers = [
    'ID',
    'Modo da Tarefa',
    'Nome da Tarefa',
    'Status',
    '% concl',
    'Início',
    'Término',
    'Trabalho',
    'Duração',
    'Predecessoras',
    'Nomes dos recursos',
    'Tipo',
    'Work Item ID',
    'Work Item Title',
    'Work Item Type',
    'Work Item State'
  ];

  return (
    <div className="mpp-data-view">
      <div className="view-header glass-card">
        <div className="header-content">
          <h2>Microsoft Project - Visualização de Colunas e Linhas</h2>
          <div className="header-stats">
            <span className="stat-badge">Total: {allItems.length} linhas</span>
            <span className="stat-badge">Colunas: {headers.length}</span>
          </div>
        </div>
      </div>

      {allItems.length === 0 ? (
        <div className="empty-state glass-card">
          <p>Nenhuma User Story ou Task encontrada no arquivo.</p>
        </div>
      ) : (
        <div className="table-container glass-card">
          <div className="table-wrapper">
            <table className="mpp-data-table">
              <thead>
                <tr>
                  {headers.map((header, idx) => (
                    <th key={idx}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {allItems.map((item, rowIdx) => {
                  const isProject = item.is_project || rowIdx === 0;
                  const isSummary = isProject || item.type === 'Summary';
                  const indentLevel = isProject ? 0 : (item.level || 0);
                  
                  // Formata data no formato do MS Project: "Sex 28/11/25"
                  const formatDateMS = (dateStr: string | undefined) => {
                    if (!dateStr) return '';
                    try {
                      const date = new Date(dateStr);
                      const weekdays = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
                      const weekday = weekdays[date.getDay()];
                      const day = String(date.getDate()).padStart(2, '0');
                      const month = String(date.getMonth() + 1).padStart(2, '0');
                      const year = String(date.getFullYear()).slice(-2);
                      return `${weekday} ${day}/${month}/${year}`;
                    } catch {
                      return dateStr;
                    }
                  };
                  
                  // Formata trabalho (work) em horas
                  const formatWork = (work: any) => {
                    if (!work) return '';
                    if (typeof work === 'number') {
                      return `${work.toFixed(1)} hrs`;
                    }
                    if (typeof work === 'string') {
                      // Se já está formatado, retorna como está
                      if (work.includes('hrs') || work.includes('hr')) {
                        return work;
                      }
                      // Tenta converter string numérica para horas
                      const num = parseFloat(work);
                      if (!isNaN(num) && num > 0) {
                        return `${num.toFixed(1)} hrs`;
                      }
                      return work;
                    }
                    return String(work);
                  };
                  
                  // Formata duração
                  const formatDuration = (duration: any) => {
                    if (!duration) return '';
                    if (typeof duration === 'string') {
                      // Se já está formatado, retorna como está
                      if (duration.includes('dias') || duration.includes('days') || 
                          duration.includes('dia') || duration.includes('day')) {
                        return duration;
                      }
                      // Tenta converter para dias
                      try {
                        const num = parseFloat(duration);
                        if (!isNaN(num) && num > 0) {
                          if (num === 1) {
                            return '1 dia';
                          }
                          return `${Math.round(num)} dias`;
                        }
                      } catch {}
                      return duration;
                    }
                    if (typeof duration === 'number' && duration > 0) {
                      if (duration === 1) {
                        return '1 dia';
                      }
                      return `${Math.round(duration)} dias`;
                    }
                    return String(duration);
                  };
                  
                  const isUserStory = (item as any).is_user_story || item.type === 'User Story';
                  const isTask = !isProject && !isUserStory && item.type === 'Task';
                  
                  return (
                    <tr 
                      key={rowIdx} 
                      className={
                        isProject ? 'project-row' : 
                        isUserStory ? 'user-story-row' :
                        isTask ? 'task-row' :
                        isSummary ? 'summary-row' : ''
                      }
                    >
                      <td>{item.id}</td>
                      <td>
                        <span className="task-mode-icon">
                          {isProject ? (
                            <span className="project-icon">▼</span>
                          ) : isUserStory ? (
                            <span className="user-story-icon">📋</span>
                          ) : isSummary ? (
                            <span className="summary-icon">▼</span>
                          ) : item.percent_complete === 100 ? (
                            <span className="completed-icon">✓</span>
                          ) : (
                            <span className="task-icon">→</span>
                          )}
                        </span>
                      </td>
                      <td 
                        className={`task-name-cell ${isProject ? 'project-name' : ''} ${isUserStory ? 'user-story-name' : ''} ${isTask ? 'task-name' : ''}`}
                        style={{ paddingLeft: `${indentLevel * 20 + 10}px` }} 
                        title={item.name}
                      >
                        {indentLevel > 0 && !isProject && <span className="indent-marker"></span>}
                        {item.name}
                      </td>
                      <td>
                        <span className={`status-badge status-${item.status?.toLowerCase().replace(/\s+/g, '-')}`}>
                          {item.status}
                        </span>
                      </td>
                      <td className="percent-cell">{item.percent_complete}%</td>
                      <td>{formatDateMS(item.start_date)}</td>
                      <td>{formatDateMS(item.finish_date)}</td>
                      <td className="work-cell">{formatWork(item.work)}</td>
                      <td className="duration-cell">{formatDuration(item.duration)}</td>
                      <td>{item.predecessors || ''}</td>
                      <td title={item.resource_names} className="resource-cell">
                        {item.resource_names || ''}
                      </td>
                      <td>{item.task_mode || 'Duração fixa'}</td>
                      <td>{item.work_item_id || ''}</td>
                      <td title={item.work_item_title}>{item.work_item_title || ''}</td>
                      <td>{item.work_item_type || ''}</td>
                      <td>{item.work_item_state || ''}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

