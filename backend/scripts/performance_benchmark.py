"""Script para benchmark de performance de operações críticas."""
import time
from typing import List, Dict, Any
from pathlib import Path
import sys

# Adiciona backend ao path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.services.devops_client import AzureDevOpsClient
from app.services.mpp_parser import MPPParser


def benchmark_list_projects(iterations: int = 3) -> Dict[str, Any]:
    """Benchmark do método list_projects."""
    print("=" * 80)
    print(f"BENCHMARK: list_projects ({iterations} iterações)")
    print("=" * 80)
    
    client = AzureDevOpsClient()
    times: List[float] = []
    
    for i in range(iterations):
        start = time.time()
        try:
            projects = client.list_projects(limit=10, use_cache=False)
            elapsed = time.time() - start
            times.append(elapsed)
            print(f"Iteração {i+1}: {elapsed:.2f}s - {len(projects)} projetos")
        except Exception as e:
            print(f"Erro na iteração {i+1}: {e}")
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\nTempo médio: {avg_time:.2f}s")
        print(f"Tempo mínimo: {min_time:.2f}s")
        print(f"Tempo máximo: {max_time:.2f}s")
        
        return {
            "iterations": iterations,
            "avg_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "times": times
        }
    
    return {}


def benchmark_parse_file(file_path: str, iterations: int = 3) -> Dict[str, Any]:
    """Benchmark do método parse_file."""
    print("=" * 80)
    print(f"BENCHMARK: parse_file ({iterations} iterações)")
    print("=" * 80)
    
    if not Path(file_path).exists():
        print(f"Arquivo não encontrado: {file_path}")
        return {}
    
    parser = MPPParser()
    times: List[float] = []
    
    for i in range(iterations):
        start = time.time()
        try:
            result = parser.parse_file(file_path)
            elapsed = time.time() - start
            times.append(elapsed)
            print(f"Iteração {i+1}: {elapsed:.2f}s - {len(result.user_stories)} US, {len(result.tasks)} Tasks")
        except Exception as e:
            print(f"Erro na iteração {i+1}: {e}")
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\nTempo médio: {avg_time:.2f}s")
        print(f"Tempo mínimo: {min_time:.2f}s")
        print(f"Tempo máximo: {max_time:.2f}s")
        
        return {
            "iterations": iterations,
            "avg_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "times": times
        }
    
    return {}


def benchmark_cache_effectiveness() -> Dict[str, Any]:
    """Benchmark da eficácia do cache."""
    print("=" * 80)
    print("BENCHMARK: Eficácia do Cache")
    print("=" * 80)
    
    client = AzureDevOpsClient()
    
    # Primeira chamada (sem cache)
    start = time.time()
    projects1 = client.list_projects(limit=10, use_cache=False)
    time_without_cache = time.time() - start
    
    # Segunda chamada (com cache)
    start = time.time()
    projects2 = client.list_projects(limit=10, use_cache=True)
    time_with_cache = time.time() - start
    
    speedup = time_without_cache / time_with_cache if time_with_cache > 0 else 0
    
    print(f"Sem cache: {time_without_cache:.2f}s")
    print(f"Com cache: {time_with_cache:.2f}s")
    print(f"Speedup: {speedup:.2f}x")
    
    return {
        "time_without_cache": time_without_cache,
        "time_with_cache": time_with_cache,
        "speedup": speedup
    }


def main():
    """Função principal de benchmark."""
    print("\n" + "=" * 80)
    print("BENCHMARK DE PERFORMANCE")
    print("=" * 80 + "\n")
    
    results = {}
    
    # 1. Benchmark list_projects
    try:
        results["list_projects"] = benchmark_list_projects(iterations=3)
    except Exception as e:
        print(f"Erro no benchmark de list_projects: {e}")
    
    # 2. Benchmark parse_file
    workspace_root = Path(__file__).parent.parent.parent
    test_files = list(workspace_root.glob("*.mpp"))
    if test_files:
        test_file = test_files[0]
        try:
            results["parse_file"] = benchmark_parse_file(str(test_file), iterations=3)
        except Exception as e:
            print(f"Erro no benchmark de parse_file: {e}")
    
    # 3. Benchmark cache
    try:
        results["cache"] = benchmark_cache_effectiveness()
    except Exception as e:
        print(f"Erro no benchmark de cache: {e}")
    
    # Resumo
    print("\n" + "=" * 80)
    print("RESUMO DO BENCHMARK")
    print("=" * 80)
    for key, value in results.items():
        print(f"\n{key}:")
        if isinstance(value, dict):
            for k, v in value.items():
                if k != "times":  # Não mostra lista de tempos no resumo
                    print(f"  {k}: {v}")
    
    # Salva resultados
    output_file = backend_path / "logs" / "benchmark_results.txt"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("RESULTADOS DO BENCHMARK\n")
        f.write("=" * 80 + "\n\n")
        for key, value in results.items():
            f.write(f"{key}:\n")
            if isinstance(value, dict):
                for k, v in value.items():
                    f.write(f"  {k}: {v}\n")
            f.write("\n")
    
    print(f"\nResultados salvos em: {output_file}")


if __name__ == "__main__":
    main()

