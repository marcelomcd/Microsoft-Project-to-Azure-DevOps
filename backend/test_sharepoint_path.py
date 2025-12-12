#!/usr/bin/env python3
"""
Script para descobrir o caminho correto da pasta no SharePoint.

Este script:
1. Conecta ao SharePoint usando as credenciais configuradas
2. Lista todas as pastas disponíveis na raiz
3. Busca arquivos .mpp em diferentes níveis
4. Mostra o caminho correto a ser usado na variável SHAREPOINT_FOLDER_PATH
"""
import sys
import os
from pathlib import Path

# Adiciona o diretório backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.services.sharepoint_files import SharePointFileService
from app.services.sharepoint_auth import SharePointAuthService

def print_section(title: str):
    """Imprime um título de seção"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def list_folders_and_files(service: SharePointFileService, folder_path: str = ""):
    """
    Lista pastas e arquivos .mpp em um caminho específico.
    
    Args:
        service: Serviço do SharePoint
        folder_path: Caminho da pasta (vazio para raiz)
    """
    import requests
    
    try:
        # Obtém IDs necessários
        site_id = service._get_site_id()
        drive_id = service._get_drive_id(site_id)
        
        # Obtém folder_id
        if folder_path:
            folder_id = service._get_folder_id(drive_id, folder_path)
            if not folder_id:
                print(f"❌ Pasta não encontrada: {folder_path}")
                return
            print(f"✅ Pasta encontrada: {folder_path}")
        else:
            folder_id = "root"
            print("📁 Listando conteúdo da raiz:")
        
        # Lista conteúdo
        access_token = service.auth_service.get_access_token()
        url = f"{service.graph_base_url}/drives/{drive_id}/items/{folder_id}/children"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        params = {
            "$select": "id,name,size,lastModifiedDateTime,webUrl,file,folder"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        items = data.get("value", [])
        
        # Separa pastas e arquivos
        folders = [item for item in items if item.get("folder") is not None]
        files = [item for item in items if item.get("file") is not None]
        mpp_files = [f for f in files if f.get("name", "").lower().endswith(".mpp")]
        
        # Mostra pastas
        if folders:
            print(f"\n📁 Pastas encontradas ({len(folders)}):")
            for folder in folders:
                name = folder.get("name", "")
                print(f"   - {name}")
        
        # Mostra arquivos .mpp
        if mpp_files:
            print(f"\n📄 Arquivos .mpp encontrados ({len(mpp_files)}):")
            for file in mpp_files:
                name = file.get("name", "")
                size = file.get("size", 0)
                size_mb = size / (1024 * 1024) if size else 0
                modified = file.get("lastModifiedDateTime", "")
                print(f"   - {name} ({size_mb:.2f} MB) - Modificado: {modified}")
        else:
            print(f"\n⚠️  Nenhum arquivo .mpp encontrado neste nível")
        
        # Mostra outros arquivos (não .mpp)
        other_files = [f for f in files if not f.get("name", "").lower().endswith(".mpp")]
        if other_files:
            print(f"\n📄 Outros arquivos encontrados ({len(other_files)}):")
            for file in other_files[:10]:  # Limita a 10
                name = file.get("name", "")
                print(f"   - {name}")
            if len(other_files) > 10:
                print(f"   ... e mais {len(other_files) - 10} arquivos")
        
        return folders, mpp_files
        
    except Exception as e:
        print(f"❌ Erro ao listar conteúdo: {e}")
        import traceback
        traceback.print_exc()
        return [], []

def search_mpp_files_recursive(service: SharePointFileService, folder_path: str = "", depth: int = 0, max_depth: int = 3):
    """
    Busca arquivos .mpp recursivamente em todas as pastas.
    
    Args:
        service: Serviço do SharePoint
        folder_path: Caminho da pasta atual
        depth: Profundidade atual
        max_depth: Profundidade máxima
    """
    if depth > max_depth:
        return []
    
    folders, mpp_files = list_folders_and_files(service, folder_path)
    
    all_mpp_files = []
    
    # Se encontrou arquivos .mpp, adiciona à lista
    if mpp_files:
        for file in mpp_files:
            full_path = f"{folder_path}/{file.get('name', '')}" if folder_path else file.get('name', '')
            all_mpp_files.append({
                "path": folder_path,
                "name": file.get('name', ''),
                "full_path": full_path,
                "size": file.get("size", 0),
                "modified": file.get("lastModifiedDateTime", "")
            })
    
    # Busca recursivamente nas subpastas
    for folder in folders:
        folder_name = folder.get("name", "")
        new_path = f"{folder_path}/{folder_name}" if folder_path else folder_name
        
        print(f"\n🔍 Buscando em: {new_path}")
        subfolder_mpp = search_mpp_files_recursive(service, new_path, depth + 1, max_depth)
        all_mpp_files.extend(subfolder_mpp)
    
    return all_mpp_files

def main():
    """Função principal"""
    print_section("🔍 DESCOBRINDO CAMINHO CORRETO DO SHAREPOINT")
    
    # Valida configuração
    print("📋 Validando configuração...")
    
    if not settings.USE_SHAREPOINT:
        print("❌ USE_SHAREPOINT não está configurado como True")
        print("   Configure no arquivo .env ou variáveis de ambiente:")
        print("   USE_SHAREPOINT=True")
        return 1
    
    if not settings.SHAREPOINT_SITE_URL:
        print("❌ SHAREPOINT_SITE_URL não está configurado")
        return 1
    
    if not settings.SHAREPOINT_CLIENT_ID:
        print("❌ SHAREPOINT_CLIENT_ID não está configurado")
        return 1
    
    if not settings.SHAREPOINT_CLIENT_SECRET:
        print("❌ SHAREPOINT_CLIENT_SECRET não está configurado")
        return 1
    
    if not settings.SHAREPOINT_TENANT_ID:
        print("❌ SHAREPOINT_TENANT_ID não está configurado")
        return 1
    
    print("✅ Configuração validada")
    print(f"   Site URL: {settings.SHAREPOINT_SITE_URL}")
    print(f"   Folder Path: {settings.SHAREPOINT_FOLDER_PATH or '(não configurado)'}")
    
    # Inicializa serviço
    print("\n🔌 Conectando ao SharePoint...")
    try:
        service = SharePointFileService()
        print("✅ Conectado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Lista conteúdo da raiz
    print_section("📁 CONTEÚDO DA RAIZ")
    folders, mpp_files = list_folders_and_files(service, "")
    
    # Se encontrou arquivos .mpp na raiz
    if mpp_files:
        print_section("✅ RESULTADO")
        print("🎯 Arquivos .mpp encontrados na RAIZ!")
        print("\n💡 Configure a variável SHAREPOINT_FOLDER_PATH como:")
        print("   (deixe vazio ou não configure)")
        return 0
    
    # Busca recursivamente
    print_section("🔍 BUSCANDO ARQUIVOS .MPP RECURSIVAMENTE")
    print("Buscando em todas as pastas (máximo 3 níveis de profundidade)...\n")
    
    all_mpp_files = search_mpp_files_recursive(service, "", 0, 3)
    
    # Mostra resultados
    print_section("📊 RESULTADOS DA BUSCA")
    
    if not all_mpp_files:
        print("❌ Nenhum arquivo .mpp encontrado em nenhuma pasta")
        print("\n💡 Verifique:")
        print("   1. Se há arquivos .mpp no SharePoint")
        print("   2. Se as permissões do App Registration estão corretas")
        print("   3. Se o caminho do site está correto")
        return 1
    
    # Agrupa por pasta
    from collections import defaultdict
    files_by_folder = defaultdict(list)
    
    for file_info in all_mpp_files:
        folder = file_info["path"] or "(raiz)"
        files_by_folder[folder].append(file_info)
    
    print(f"✅ Encontrados {len(all_mpp_files)} arquivo(s) .mpp em {len(files_by_folder)} pasta(s):\n")
    
    for folder_path, files in files_by_folder.items():
        print(f"📁 Pasta: {folder_path or '(raiz)'}")
        print(f"   Arquivos .mpp: {len(files)}")
        for file_info in files:
            size_mb = file_info["size"] / (1024 * 1024) if file_info["size"] else 0
            print(f"      - {file_info['name']} ({size_mb:.2f} MB)")
        print()
    
    # Recomenda caminho
    print_section("💡 RECOMENDAÇÃO")
    
    # Se todos os arquivos estão na mesma pasta
    if len(files_by_folder) == 1:
        folder_path = list(files_by_folder.keys())[0]
        if folder_path == "(raiz)":
            print("✅ Todos os arquivos estão na RAIZ")
            print("\n📝 Configure a variável SHAREPOINT_FOLDER_PATH como:")
            print("   (deixe vazio ou não configure)")
        else:
            print(f"✅ Todos os arquivos estão na pasta: {folder_path}")
            print("\n📝 Configure a variável SHAREPOINT_FOLDER_PATH como:")
            print(f"   {folder_path}")
    else:
        print("⚠️  Arquivos .mpp encontrados em múltiplas pastas:")
        for folder_path in files_by_folder.keys():
            count = len(files_by_folder[folder_path])
            print(f"   - {folder_path or '(raiz)'}: {count} arquivo(s)")
        print("\n💡 Escolha a pasta que contém a maioria dos arquivos .mpp")
        print("   ou configure para processar todas as pastas (requer ajuste no código)")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

