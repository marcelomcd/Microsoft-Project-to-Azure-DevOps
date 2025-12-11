import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para log de erros
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export interface UploadResponse {
  file_id: string;
  filename: string;
  project_name: string;
  work_item_id: string | number | null;
  user_stories_count: number;
  tasks_count: number;
  parsed_data: any;
  work_item_data?: any;
}

export interface WorkItem {
  id: number;
  rev: number;
  fields: Record<string, any>;
  relations?: any[];
  url: string;
}

export interface ProjectInfo {
  id: string;
  name: string;
  description?: string;
  url: string;
  area_path?: string;
  iteration_path?: string;
  work_item_id?: string | number;
  numero_proposta?: string;
  responsavel_tecnico?: any;
  horas_projeto?: any;
  target_date?: string;
  created_by?: any;
  criticidade?: string;
  situacao_pendente?: string;
  data_liberada_homologacao?: string;
  parent?: string;
  user_stories_count?: number;
  tasks_count?: number;
}

export interface ConversionResult {
  project_name: string;
  created_user_stories: number;
  created_tasks: number;
  updated_user_stories?: number;
  updated_tasks?: number;
  skipped_user_stories: number;
  skipped_tasks: number;
  errors: string[];
  work_items: WorkItem[];
}

export const apiService = {
  // Upload
  uploadFile: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post<UploadResponse>('/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getParsedFile: async (fileId: string): Promise<any> => {
    const response = await api.get(`/upload/${fileId}`);
    return response.data;
  },

  // Work Items
  getWorkItem: async (workItemId: number): Promise<WorkItem> => {
    const response = await api.get<WorkItem>(`/workitems/${workItemId}`);
    return response.data;
  },

  analyzeWorkItem: async (workItemId: number): Promise<any> => {
    const response = await api.get(`/workitems/${workItemId}/analyze`);
    return response.data;
  },

  searchWorkItems: async (
    title: string,
    workItemType?: string,
    areaPath?: string
  ): Promise<WorkItem[]> => {
    const params: any = { title };
    if (workItemType) params.work_item_type = workItemType;
    if (areaPath) params.area_path = areaPath;
    const response = await api.get<WorkItem[]>('/workitems/', { params });
    return response.data;
  },

  // Projects
  listProjects: async (limit?: number): Promise<ProjectInfo[]> => {
    const params: any = {};
    if (limit) params.limit = limit;
    const response = await api.get<ProjectInfo[]>('/projects/', { params });
    return response.data;
  },

  getProjectWorkItems: async (projectId: string): Promise<WorkItem[]> => {
    const response = await api.get<WorkItem[]>(`/projects/${projectId}/workitems`);
    return response.data;
  },

  // Conversion
  convertToDevOps: async (
    fileId: string,
    areaPath?: string,
    iterationPath?: string,
    skipDuplicates: boolean = true,
    parentFeatureId?: number,
    updateExisting: boolean = false
  ): Promise<ConversionResult> => {
    const response = await api.post<ConversionResult>('/convert/', {
      file_id: fileId,
      area_path: areaPath,
      iteration_path: iterationPath,
      skip_duplicates: skipDuplicates,
      parent_feature_id: parentFeatureId,
      update_existing: updateExisting,
    });
    return response.data;
  },

  // Sync from DevOps
  syncFromDevOps: async (
    workItemId: number,
    includeClosed: boolean = true
  ): Promise<any> => {
    const response = await api.post('/convert/sync-from-devops', {
      work_item_id: workItemId,
      include_closed: includeClosed,
    });
    return response.data;
  },

  // Raw file data
  getRawFileData: async (fileId: string): Promise<any> => {
    const response = await api.get(`/upload/${fileId}/raw-data`);
    return response.data;
  },
};

export default api;

