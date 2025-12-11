"""Sistema de cache otimizado para Azure DevOps e parsing de arquivos"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import threading
import hashlib
from pathlib import Path


class SmartCache:
    """Cache em memória otimizado com TTL configurável por tipo de dado"""
    
    def __init__(self, default_ttl_minutes: int = 30):
        """
        Args:
            default_ttl_minutes: TTL padrão em minutos
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl_minutes = default_ttl_minutes
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Obtém item do cache se ainda válido"""
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            item = self.cache[key]
            expires_at = item.get('expires_at')
            
            if expires_at and datetime.now() > expires_at:
                # Cache expirado
                del self.cache[key]
                self.misses += 1
                return None
            
            self.hits += 1
            return item.get('data')
    
    def set(self, key: str, data: Any, ttl_minutes: Optional[int] = None) -> None:
        """Armazena item no cache"""
        with self.lock:
            ttl = ttl_minutes or self.default_ttl_minutes
            expires_at = datetime.now() + timedelta(minutes=ttl)
            self.cache[key] = {
                'data': data,
                'expires_at': expires_at,
                'created_at': datetime.now()
            }
    
    def clear(self, key: Optional[str] = None) -> None:
        """Limpa cache específico ou todo o cache"""
        with self.lock:
            if key:
                if key in self.cache:
                    del self.cache[key]
            else:
                self.cache.clear()
                self.hits = 0
                self.misses = 0
    
    def clear_expired(self) -> None:
        """Remove itens expirados do cache"""
        with self.lock:
            now = datetime.now()
            keys_to_remove = [
                key for key, item in self.cache.items()
                if item.get('expires_at') and item['expires_at'] < now
            ]
            for key in keys_to_remove:
                del self.cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        with self.lock:
            self.clear_expired()
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            return {
                'total_items': len(self.cache),
                'keys': list(self.cache.keys()),
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': f"{hit_rate:.2f}%"
            }


class ProjectCache(SmartCache):
    """Cache específico para projetos (TTL: 60 minutos)"""
    def __init__(self):
        super().__init__(default_ttl_minutes=60)


class WorkItemCache(SmartCache):
    """Cache específico para Work Items (TTL: 30 minutos)"""
    def __init__(self):
        super().__init__(default_ttl_minutes=30)


class ParsingCache(SmartCache):
    """Cache específico para parsing de arquivos (TTL: 120 minutos)"""
    def __init__(self):
        super().__init__(default_ttl_minutes=120)
    
    def _get_file_hash(self, file_path: str) -> str:
        """Gera hash do arquivo para usar como chave de cache"""
        try:
            file = Path(file_path)
            if not file.exists():
                return ""
            # Usa tamanho + data de modificação como hash simples
            stat = file.stat()
            hash_input = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
            return hashlib.md5(hash_input.encode()).hexdigest()
        except Exception:
            return ""
    
    def get_by_file(self, file_path: str) -> Optional[Any]:
        """Obtém cache baseado no arquivo"""
        file_hash = self._get_file_hash(file_path)
        if not file_hash:
            return None
        return self.get(f"file_{file_hash}")
    
    def set_by_file(self, file_path: str, data: Any) -> None:
        """Armazena cache baseado no arquivo"""
        file_hash = self._get_file_hash(file_path)
        if file_hash:
            self.set(f"file_{file_hash}", data)


# Instâncias globais de cache
project_cache = ProjectCache()
work_item_cache = WorkItemCache()
parsing_cache = ParsingCache()

