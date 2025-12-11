"""Script para profiling de código e identificação de gargalos."""
import cProfile
import pstats
import io
from pathlib import Path
import sys
from typing import Dict, Any

# Adiciona backend ao path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.services.devops_client import AzureDevOpsClient
from app.services.mpp_parser import MPPParser
from app.services.mapper_service import MapperService


def profile_list_projects() -> Dict[str, Any]:
    """Profiling do método list_projects."""
    print("=" * 80)
    print("PROFILING: list_projects")
    print("=" * 80)
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    try:
        client = AzureDevOpsClient()
        # Usa limite pequeno para não demorar muito
        projects = client.list_projects(limit=5, use_cache=False)
        print(f"Projetos encontrados: {len(projects)}")
    except Exception as e:
        print(f"Erro durante profiling: {e}")
    
    profiler.disable()
    
    # Analisa resultados
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.sort_stats('cumulative')
    ps.print_stats(20)  # Top 20 funções
    
    print(s.getvalue())
    
    return {
        "total_calls": ps.total_calls,
        "total_time": ps.total_tt
    }


def profile_parse_file(file_path: str) -> Dict[str, Any]:
    """Profiling do método parse_file."""
    print("=" * 80)
    print(f"PROFILING: parse_file - {file_path}")
    print("=" * 80)
    
    if not Path(file_path).exists():
        print(f"Arquivo não encontrado: {file_path}")
        return {}
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    try:
        parser = MPPParser()
        result = parser.parse_file(file_path)
        print(f"User Stories: {len(result.user_stories)}")
        print(f"Tasks: {len(result.tasks)}")
    except Exception as e:
        print(f"Erro durante profiling: {e}")
    
    profiler.disable()
    
    # Analisa resultados
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.sort_stats('cumulative')
    ps.print_stats(20)
    
    print(s.getvalue())
    
    return {
        "total_calls": ps.total_calls,
        "total_time": ps.total_tt
    }


def profile_convert_to_devops(parsed_data, feature_id: int) -> Dict[str, Any]:
    """Profiling do método convert_to_devops."""
    print("=" * 80)
    print("PROFILING: convert_to_devops")
    print("=" * 80)
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    try:
        mapper = MapperService()
        result = mapper.convert_to_devops(
            parsed_data,
            parent_feature_id=feature_id,
            skip_duplicates=True,
            update_existing=False
        )
        print(f"User Stories criadas: {result.created_user_stories}")
        print(f"Tasks criadas: {result.created_tasks}")
    except Exception as e:
        print(f"Erro durante profiling: {e}")
    
    profiler.disable()
    
    # Analisa resultados
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.sort_stats('cumulative')
    ps.print_stats(20)
    
    print(s.getvalue())
    
    return {
        "total_calls": ps.total_calls,
        "total_time": ps.total_tt
    }


def profile_memory_usage():
    """Profiling de uso de memória."""
    try:
        from memory_profiler import profile
        import tracemalloc
        
        print("=" * 80)
        print("PROFILING: Memory Usage")
        print("=" * 80)
        
        tracemalloc.start()
        
        # Executa operações
        client = AzureDevOpsClient()
        projects = client.list_projects(limit=10, use_cache=False)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        print(f"Memória atual: {current / 1024 / 1024:.2f} MB")
        print(f"Memória pico: {peak / 1024 / 1024:.2f} MB")
        
        return {
            "current_mb": current / 1024 / 1024,
            "peak_mb": peak / 1024 / 1024
        }
    except ImportError:
        print("memory_profiler não instalado. Instale com: pip install memory-profiler")
        return {}


def main():
    """Função principal de profiling."""
    print("\n" + "=" * 80)
    print("PROFILING DO CÓDIGO - Análise de Performance")
    print("=" * 80 + "\n")
    
    results = {}
    
    # 1. Profiling de list_projects
    try:
        results["list_projects"] = profile_list_projects()
    except Exception as e:
        print(f"Erro no profiling de list_projects: {e}")
    
    # 2. Profiling de parse_file (se houver arquivo de teste)
    workspace_root = Path(__file__).parent.parent.parent
    test_files = list(workspace_root.glob("*.mpp"))
    if test_files:
        test_file = test_files[0]
        try:
            results["parse_file"] = profile_parse_file(str(test_file))
        except Exception as e:
            print(f"Erro no profiling de parse_file: {e}")
    else:
        print("Nenhum arquivo .mpp encontrado para teste")
    
    # 3. Profiling de memória
    try:
        results["memory"] = profile_memory_usage()
    except Exception as e:
        print(f"Erro no profiling de memória: {e}")
    
    # Resumo
    print("\n" + "=" * 80)
    print("RESUMO DO PROFILING")
    print("=" * 80)
    for key, value in results.items():
        print(f"{key}: {value}")
    
    # Salva resultados em arquivo
    output_file = backend_path / "logs" / "profiling_results.txt"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("RESULTADOS DO PROFILING\n")
        f.write("=" * 80 + "\n\n")
        for key, value in results.items():
            f.write(f"{key}:\n")
            f.write(f"  {value}\n\n")
    
    print(f"\nResultados salvos em: {output_file}")


if __name__ == "__main__":
    main()

