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
import requests

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

def search_mpp_files_recursive(service: SharePointFileService, folder_path: str = "", depth: int = 0, max_depth: int = 5):
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
            # Normaliza o caminho (remove "Documentos Compartilhados/" se presente)
            normalized_path = folder_path
            if normalized_path.startswith("Documentos Compartilhados/"):
                normalized_path = normalized_path.replace("Documentos Compartilhados/", "", 1)
            
            all_mpp_files.append({
                "path": folder_path,
                "normalized_path": normalized_path,
                "name": file.get('name', ''),
                "size": file.get("size", 0),
                "modified": file.get("lastModifiedDateTime", ""),
                "web_url": file.get("webUrl", "")
            })
    
    # Busca recursivamente nas subpastas
    for folder in folders:
        folder_name = folder.get("name", "")
        new_path = f"{folder_path}/{folder_name}" if folder_path else folder_name
        
        indent = "  " * depth
        if depth < 2:  # Só mostra detalhes nos primeiros níveis
            print(f"{indent}🔍 Buscando em: {new_path}")
        
        subfolder_mpp = search_mpp_files_recursive(service, new_path, depth + 1, max_depth)
        all_mpp_files.extend(subfolder_mpp)
        
        # Se encontrou arquivos nesta subpasta, mostra
        if subfolder_mpp and depth < 2:
            print(f"{indent}   ✅ Encontrados {len(subfolder_mpp)} arquivo(s) .mpp nesta pasta!")
    
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
    
    # Testa caminhos específicos baseados no link fornecido
    print_section("🧪 TESTANDO CAMINHOS ESPECÍFICOS")
    
    # Caminhos a testar baseados no link fornecido
    test_paths = [
        "Cronogramas - Project",  # Apenas a subpasta (mais comum)
        "Documentos Compartilhados/Cronogramas - Project",  # Caminho completo
        "Documentações de Projetos/Cronogramas - Project",  # Nome de exibição
        # Tentativa com codificação específica sugerida
        "%252fDocumentos%2bCompartilhados%252fCronogramas%2b-%2bProject",
        # Variações com espaços como +
        "Documentos+Compartilhados/Cronogramas+-+Project",
        "Documentos+Compartilhados/Cronogramas+-+Project",
    ]
    
    # Adiciona o caminho configurado se existir
    if settings.SHAREPOINT_FOLDER_PATH and settings.SHAREPOINT_FOLDER_PATH not in test_paths:
        test_paths.insert(0, settings.SHAREPOINT_FOLDER_PATH)
    
    site_id = service._get_site_id()
    drive_id = service._get_drive_id(site_id)
    
    print(f"📋 Testando {len(test_paths)} caminho(s) específico(s)...\n")
    
    for test_path in test_paths:
        print(f"🔍 Testando: {test_path}")
        try:
            folder_id = service._get_folder_id(drive_id, test_path)
            
            if folder_id:
                print(f"   ✅ Pasta encontrada! ID: {folder_id[:30]}...")
                # Lista arquivos nesta pasta
                folders_test, mpp_files_test = list_folders_and_files(service, test_path)
                if mpp_files_test:
                    print(f"   ✅✅✅ SUCESSO! Encontrados {len(mpp_files_test)} arquivo(s) .mpp nesta pasta!")
                    print(f"\n📝 O caminho CORRETO é:")
                    print(f"   {test_path}")
                    print(f"\n💡 Configure a variável SHAREPOINT_FOLDER_PATH como:")
                    print(f"   {test_path}")
                    
                    # Mostra alguns arquivos encontrados
                    print(f"\n📄 Arquivos encontrados (primeiros 5):")
                    for file_info in mpp_files_test[:5]:
                        size_mb = file_info.get("size", 0) / (1024 * 1024) if file_info.get("size") else 0
                        print(f"   - {file_info.get('name', 'N/A')} ({size_mb:.2f} MB)")
                    if len(mpp_files_test) > 5:
                        print(f"   ... e mais {len(mpp_files_test) - 5} arquivo(s)")
                    
                    return 0
                else:
                    print(f"   ⚠️  Pasta encontrada, mas nenhum arquivo .mpp encontrado nela.")
            else:
                print(f"   ❌ Pasta não encontrada com este caminho.")
        except Exception as e:
            print(f"   ❌ Erro ao testar caminho: {e}")
        print()
    
    print("⚠️  Nenhum dos caminhos específicos funcionou. Continuando busca em todas as pastas...\n")
    
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
    
    # Lista todas as bibliotecas de documentos disponíveis
    print_section("📚 BIBLIOTECAS DE DOCUMENTOS DISPONÍVEIS")
    try:
        site_id = service._get_site_id()
        access_token = service.auth_service.get_access_token()
        url = f"{service.graph_base_url}/sites/{site_id}/drives"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        drives_data = response.json()
        drives = drives_data.get("value", [])
        
        if len(drives) > 1:
            print(f"✅ Encontradas {len(drives)} biblioteca(s) de documentos:\n")
            for i, drive in enumerate(drives, 1):
                drive_name = drive.get("name", "Sem nome")
                print(f"   {i}. {drive_name}")
            print("\n💡 Usando a primeira biblioteca (padrão). Se os arquivos estiverem em outra, será necessário ajustar o código.\n")
        else:
            drive_name = drives[0].get("name", "Biblioteca padrão") if drives else "N/A"
            print(f"✅ Biblioteca de documentos: {drive_name}\n")
    except Exception as e:
        print(f"⚠️  Não foi possível listar bibliotecas: {e}\n")
    
    # Busca recursivamente
    print_section("🔍 BUSCANDO ARQUIVOS .MPP RECURSIVAMENTE")
    print("Buscando em todas as pastas (máximo 5 níveis de profundidade)...\n")
    
    all_mpp_files = search_mpp_files_recursive(service, "", 0, 5)
    
    # Mostra resultados
    print_section("📊 RESULTADOS DA BUSCA")
    
    if not all_mpp_files:
        print("❌ Nenhum arquivo .mpp encontrado em nenhuma pasta")
        print("\n💡 Possíveis causas:")
        print("   1. Os arquivos .mpp estão em uma subpasta mais profunda (busca até 5 níveis)")
        print("   2. Os arquivos estão em uma biblioteca de documentos diferente")
        print("   3. As permissões do App Registration não permitem ver os arquivos")
        print("   4. O caminho do site está incorreto")
        print("\n🔍 Próximos passos:")
        print("   1. Verifique manualmente no SharePoint onde estão os arquivos .mpp")
        print("   2. Use o caminho completo da pasta na variável SHAREPOINT_FOLDER_PATH")
        print("   3. Exemplo: Se os arquivos estão em 'Quali IT/Projetos/MPP', use esse caminho")
        return 1
    
    # Agrupa por pasta
    from collections import defaultdict
    files_by_folder = defaultdict(list)
    files_by_normalized_folder = defaultdict(list)
    
    for file_info in all_mpp_files:
        folder = file_info["path"] or "(raiz)"
        normalized_folder = file_info.get("normalized_path", folder) or "(raiz)"
        files_by_folder[folder].append(file_info)
        files_by_normalized_folder[normalized_folder].append(file_info)
    
    print(f"✅ Encontrados {len(all_mpp_files)} arquivo(s) .mpp em {len(files_by_folder)} pasta(s):\n")
    
    for folder_path, files in files_by_folder.items():
        print(f"📁 Pasta: {folder_path or '(raiz)'}")
        print(f"   Arquivos .mpp: {len(files)}")
        for file_info in files[:5]:  # Mostra apenas os 5 primeiros
            size_mb = file_info["size"] / (1024 * 1024) if file_info["size"] else 0
            print(f"      - {file_info['name']} ({size_mb:.2f} MB)")
        if len(files) > 5:
            print(f"      ... e mais {len(files) - 5} arquivo(s)")
        print()
    
    # Recomenda caminho
    print_section("💡 RECOMENDAÇÃO PARA SHAREPOINT_FOLDER_PATH")
    
    # Se todos os arquivos estão na mesma pasta
    if len(files_by_normalized_folder) == 1:
        folder_path = list(files_by_normalized_folder.keys())[0]
        original_path = list(files_by_folder.keys())[0]
        
        if folder_path == "(raiz)":
            print("✅ Todos os arquivos estão na RAIZ da biblioteca de documentos")
            print("\n📝 Configure a variável SHAREPOINT_FOLDER_PATH como:")
            print("   (deixe vazio ou não configure)")
            print("\n   Ou se preferir ser explícito:")
            print("   (não configure a variável)")
        else:
            print(f"✅ Todos os arquivos estão na pasta: {original_path}")
            print(f"\n📝 Configure a variável SHAREPOINT_FOLDER_PATH como:")
            print(f"   {folder_path}")
            print(f"\n   Ou o caminho completo (se necessário):")
            print(f"   {original_path}")
            
            # Testa se o caminho funciona
            print(f"\n🧪 Testando se o caminho funciona...")
            try:
                site_id = service._get_site_id()
                drive_id = service._get_drive_id(site_id)
                test_folder_id = service._get_folder_id(drive_id, folder_path)
                if test_folder_id:
                    print(f"✅ Caminho testado e funcionando: {folder_path}")
                else:
                    # Tenta o caminho completo
                    test_folder_id = service._get_folder_id(drive_id, original_path)
                    if test_folder_id:
                        print(f"✅ Caminho completo funciona: {original_path}")
                        print(f"   Use este valor: {original_path}")
                    else:
                        print(f"⚠️  Caminho não encontrado. Verifique manualmente.")
            except Exception as e:
                print(f"⚠️  Erro ao testar caminho: {e}")
    else:
        print("⚠️  Arquivos .mpp encontrados em múltiplas pastas:")
        print()
        for folder_path in sorted(files_by_normalized_folder.keys()):
            count = len(files_by_normalized_folder[folder_path])
            original_path = [k for k in files_by_folder.keys() if files_by_folder[k][0].get("normalized_path") == folder_path][0] if files_by_normalized_folder[folder_path] else folder_path
            print(f"   📁 {folder_path or '(raiz)'}: {count} arquivo(s)")
            if original_path != folder_path:
                print(f"      (caminho completo: {original_path})")
        
        # Encontra a pasta com mais arquivos
        best_folder = max(files_by_normalized_folder.items(), key=lambda x: len(x[1]))
        best_path = best_folder[0]
        best_count = len(best_folder[1])
        best_original = [k for k in files_by_folder.keys() if files_by_folder[k][0].get("normalized_path") == best_path][0] if best_folder[1] else best_path
        
        print(f"\n💡 RECOMENDAÇÃO: Use a pasta com mais arquivos:")
        print(f"   📁 {best_path or '(raiz)'} ({best_count} arquivo(s))")
        print(f"\n📝 Configure a variável SHAREPOINT_FOLDER_PATH como:")
        if best_path == "(raiz)":
            print("   (deixe vazio ou não configure)")
        else:
            print(f"   {best_path}")
            if best_original != best_path:
                print(f"\n   Ou o caminho completo:")
                print(f"   {best_original}")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

