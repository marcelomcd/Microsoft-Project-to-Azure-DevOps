import { useState, useEffect, useMemo } from 'react';
import { apiService, ProjectInfo } from '../services/api';
import './ProjectView.css';

export default function ProjectView() {
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [filterPMO, setFilterPMO] = useState('');
  const [filterResponsavel, setFilterResponsavel] = useState('');
  const [filterCliente, setFilterCliente] = useState('');

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Carrega todos os projetos (sem limite)
      const data = await apiService.listProjects();
      setProjects(data);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Erro ao carregar projetos';
      console.error('Erro ao carregar projetos:', err);
      setError(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  // Extrai valores únicos para os filtros
  const uniqueValues = useMemo(() => {
    const responsaveis = new Set<string>();
    const clientes = new Set<string>();
    const pmos = new Set<string>();
    
    projects.forEach(project => {
      const responsavel = project.responsavel_tecnico 
        ? (typeof project.responsavel_tecnico === 'object' 
            ? project.responsavel_tecnico.displayName || project.responsavel_tecnico.nome || ''
            : String(project.responsavel_tecnico))
        : '';
      if (responsavel) responsaveis.add(responsavel);
      
      if (project.parent) clientes.add(project.parent);
      
      // PMO pode ser extraído do created_by ou outro campo
      const pmo = project.created_by
        ? (typeof project.created_by === 'object'
            ? project.created_by.displayName || project.created_by.nome || ''
            : String(project.created_by))
        : '';
      if (pmo) pmos.add(pmo);
    });
    
    return {
      responsaveis: Array.from(responsaveis).sort(),
      clientes: Array.from(clientes).sort(),
      pmos: Array.from(pmos).sort()
    };
  }, [projects]);

  // Filtra projetos
  const filteredProjects = useMemo(() => {
    return projects.filter(project => {
      // Busca por termo
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase();
        const matchesSearch = 
          project.name?.toLowerCase().includes(searchLower) ||
          project.numero_proposta?.toLowerCase().includes(searchLower) ||
          project.id?.toLowerCase().includes(searchLower);
        if (!matchesSearch) return false;
      }
      
      // Filtro por Responsável Técnico
      if (filterResponsavel) {
        const responsavel = project.responsavel_tecnico 
          ? (typeof project.responsavel_tecnico === 'object' 
              ? project.responsavel_tecnico.displayName || project.responsavel_tecnico.nome || ''
              : String(project.responsavel_tecnico))
          : '';
        if (responsavel !== filterResponsavel) return false;
      }
      
      // Filtro por Cliente (Parent)
      if (filterCliente) {
        if (project.parent !== filterCliente) return false;
      }
      
      // Filtro por PMO (Created By)
      if (filterPMO) {
        const pmo = project.created_by
          ? (typeof project.created_by === 'object'
              ? project.created_by.displayName || project.created_by.nome || ''
              : String(project.created_by))
          : '';
        if (pmo !== filterPMO) return false;
      }
      
      return true;
    });
  }, [projects, searchTerm, filterPMO, filterResponsavel, filterCliente]);

  if (isLoading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>Carregando projetos...</p>
      </div>
    );
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div className="project-view">
      <div className="view-header glass-card">
        <div className="header-content">
          <div>
            <h2>Detalhes dos Projetos no Azure DevOps</h2>
            <div className="project-counter">
              <span className="counter-badge">
                {filteredProjects.length} {filteredProjects.length === 1 ? 'projeto' : 'projetos'}
                {filteredProjects.length !== projects.length && ` de ${projects.length}`}
              </span>
            </div>
          </div>
          <button className="btn btn-secondary" onClick={loadProjects}>
            Atualizar
          </button>
        </div>
      </div>

      {/* Filtros e Busca */}
      <div className="filters-section glass-card">
        <div className="search-bar">
          <input
            type="text"
            placeholder="🔍 Buscar por título, número de proposta ou ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
        
        <div className="filters-row">
          <div className="filter-group">
            <label>PMO:</label>
            <select
              value={filterPMO}
              onChange={(e) => setFilterPMO(e.target.value)}
              className="filter-select"
            >
              <option value="">Todos</option>
              {uniqueValues.pmos.map(pmo => (
                <option key={pmo} value={pmo}>{pmo}</option>
              ))}
            </select>
          </div>
          
          <div className="filter-group">
            <label>Responsável Técnico:</label>
            <select
              value={filterResponsavel}
              onChange={(e) => setFilterResponsavel(e.target.value)}
              className="filter-select"
            >
              <option value="">Todos</option>
              {uniqueValues.responsaveis.map(resp => (
                <option key={resp} value={resp}>{resp}</option>
              ))}
            </select>
          </div>
          
          <div className="filter-group">
            <label>Cliente:</label>
            <select
              value={filterCliente}
              onChange={(e) => setFilterCliente(e.target.value)}
              className="filter-select"
            >
              <option value="">Todos</option>
              {uniqueValues.clientes.map(cliente => (
                <option key={cliente} value={cliente}>{cliente}</option>
              ))}
            </select>
          </div>
          
          {(filterPMO || filterResponsavel || filterCliente || searchTerm) && (
            <button
              className="btn-clear-filters"
              onClick={() => {
                setSearchTerm('');
                setFilterPMO('');
                setFilterResponsavel('');
                setFilterCliente('');
              }}
            >
              Limpar Filtros
            </button>
          )}
        </div>
      </div>

      {filteredProjects.length === 0 ? (
        <div className="glass-card">
          <p>{projects.length === 0 ? 'Nenhum projeto encontrado.' : 'Nenhum projeto corresponde aos filtros aplicados.'}</p>
        </div>
      ) : (
        <div className="projects-grid">
          {filteredProjects.map((project) => {
            // Extrai informações do responsável técnico
            const responsavelTecnico = project.responsavel_tecnico 
              ? (typeof project.responsavel_tecnico === 'object' 
                  ? project.responsavel_tecnico.displayName || project.responsavel_tecnico.nome || ''
                  : String(project.responsavel_tecnico))
              : '';

            // Extrai informações do criado por
            const criadoPor = project.created_by
              ? (typeof project.created_by === 'object'
                  ? project.created_by.displayName || project.created_by.nome || ''
                  : String(project.created_by))
              : '';

            // Formata data
            const formatDate = (dateStr: string | undefined) => {
              if (!dateStr) return '';
              try {
                return new Date(dateStr).toLocaleDateString('pt-BR');
              } catch {
                return dateStr;
              }
            };

            return (
              <div key={project.id} className="project-card glass-card">
                <div className="project-details-list">
                  <div className="detail-row">
                    <span className="icon">🆔</span>
                    <strong>Work Item ID:</strong>
                    <span>{project.id}</span>
                  </div>
                  
                  <div className="detail-row">
                    <span className="icon">📝</span>
                    <strong>Título:</strong>
                    <span>{project.name}</span>
                  </div>
                  
                  {project.numero_proposta && (
                    <div className="detail-row">
                      <span className="icon">📄</span>
                      <strong>Número de Proposta:</strong>
                      <span>{project.numero_proposta}</span>
                    </div>
                  )}
                  
                  {project.parent && (
                    <div className="detail-row">
                      <span className="icon">📁</span>
                      <strong>Cliente:</strong>
                      <span>{project.parent}</span>
                    </div>
                  )}
                  
                  {responsavelTecnico && (
                    <div className="detail-row">
                      <span className="icon">👤</span>
                      <strong>Responsável Técnico:</strong>
                      <span>{responsavelTecnico}</span>
                    </div>
                  )}
                  
                  {project.horas_projeto && (
                    <div className="detail-row">
                      <span className="icon">⏱️</span>
                      <strong>Horas do Projeto:</strong>
                      <span>{project.horas_projeto}</span>
                    </div>
                  )}
                  
                  {project.target_date && (
                    <div className="detail-row">
                      <span className="icon">📅</span>
                      <strong>Data Fim Original:</strong>
                      <span>{formatDate(project.target_date)}</span>
                    </div>
                  )}
                  
                  {criadoPor && (
                    <div className="detail-row">
                      <span className="icon">✍️</span>
                      <strong>Criado Por:</strong>
                      <span>{criadoPor}</span>
                    </div>
                  )}
                  
                  {project.criticidade && (
                    <div className="detail-row">
                      <span className="icon">⚠️</span>
                      <strong>Criticidade:</strong>
                      <span>{project.criticidade}</span>
                    </div>
                  )}
                  
                  {project.situacao_pendente && (
                    <div className="detail-row">
                      <span className="icon">📌</span>
                      <strong>Pendência:</strong>
                      <span>{project.situacao_pendente}</span>
                    </div>
                  )}
                  
                  {project.data_liberada_homologacao && (
                    <div className="detail-row">
                      <span className="icon">✅</span>
                      <strong>Data Liberada para Homologação:</strong>
                      <span>{formatDate(project.data_liberada_homologacao)}</span>
                    </div>
                  )}
                  
                  <div className="detail-row">
                    <span className="icon">📚</span>
                    <strong>User Story:</strong>
                    <span>{project.user_stories_count || 0}</span>
                  </div>
                  
                  <div className="detail-row">
                    <span className="icon">✓</span>
                    <strong>Task:</strong>
                    <span>{project.tasks_count || 0}</span>
                  </div>
                </div>
                
                <a
                  href={`https://dev.azure.com/qualiit/Quali%20IT%20-%20Inova%C3%A7%C3%A3o%20e%20Tecnologia/_boards/board/t/Quali%20IT%20!%20Gestao%20de%20Projeto/Features?workitem=${project.id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="project-link"
                >
                  🔗 Ver no Azure DevOps →
                </a>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

