import { useState, useEffect } from 'react';
import FileUpload from './components/FileUpload';
import MPPDataView from './components/MPPDataView';
import WorkItemDetailsView from './components/WorkItemDetailsView';
import ProjectView from './components/ProjectView';
import SyncView from './components/SyncView';
import { UploadResponse } from './services/api';
import './App.css';

function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [activeTab, setActiveTab] = useState<'upload' | 'verify' | 'workitems' | 'projects' | 'sync'>('upload');
  const [uploadedFile, setUploadedFile] = useState<UploadResponse | null>(null);

  // Carrega arquivo do localStorage ao iniciar
  useEffect(() => {
    const savedFile = localStorage.getItem('uploadedFile');
    if (savedFile) {
      try {
        const parsed = JSON.parse(savedFile);
        setUploadedFile(parsed);
      } catch (e) {
        console.error('Erro ao carregar arquivo do localStorage:', e);
      }
    }
  }, []);

  // Salva arquivo no localStorage quando muda
  useEffect(() => {
    if (uploadedFile) {
      localStorage.setItem('uploadedFile', JSON.stringify(uploadedFile));
    } else {
      localStorage.removeItem('uploadedFile');
    }
  }, [uploadedFile]);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    document.body.className = newTheme;
  };

  return (
    <div className={`app ${theme}`}>
      <header className="app-header">
        <div className="header-content">
          <h1>MPP to Azure DevOps Converter</h1>
          <button className="theme-toggle" onClick={toggleTheme}>
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
        </div>
        <nav className="app-nav">
          <button
            className={activeTab === 'upload' ? 'active' : ''}
            onClick={() => setActiveTab('upload')}
          >
            Upload File .MPP
          </button>
          {uploadedFile && (
            <button
              className={activeTab === 'verify' ? 'active' : ''}
              onClick={() => setActiveTab('verify')}
            >
              Microsoft Project Verify
            </button>
          )}
          <button
            className={activeTab === 'workitems' ? 'active' : ''}
            onClick={() => setActiveTab('workitems')}
          >
            Azure DevOps User Stories and Task's
          </button>
          <button
            className={activeTab === 'projects' ? 'active' : ''}
            onClick={() => setActiveTab('projects')}
          >
            Projects in Azure DevOps
          </button>
          {uploadedFile && (
            <button
              className={activeTab === 'sync' ? 'active' : ''}
              onClick={() => setActiveTab('sync')}
            >
              Sync .MPP ↔ DevOps
            </button>
          )}
        </nav>
      </header>

      <main className="app-main">
        {activeTab === 'upload' && (
          <div className="tab-content">
            <FileUpload 
              uploadedFile={uploadedFile}
              onUploadSuccess={(fileId, uploadResponse) => {
                setUploadedFile(uploadResponse);
              }} 
            />
          </div>
        )}
        {activeTab === 'verify' && uploadedFile && (
          <div className="tab-content">
            <MPPDataView 
              fileId={uploadedFile.file_id} 
              parsedData={uploadedFile.parsed_data}
            />
          </div>
        )}
        {activeTab === 'workitems' && (
          <div className="tab-content">
            <WorkItemDetailsView uploadedFile={uploadedFile} />
          </div>
        )}
        {activeTab === 'projects' && (
          <div className="tab-content">
            <ProjectView />
          </div>
        )}
        {activeTab === 'sync' && uploadedFile && (
          <div className="tab-content">
            <SyncView
              fileId={uploadedFile.file_id}
              filename={uploadedFile.filename}
              workItemId={uploadedFile.work_item_id}
              parsedData={uploadedFile.parsed_data}
            />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;

