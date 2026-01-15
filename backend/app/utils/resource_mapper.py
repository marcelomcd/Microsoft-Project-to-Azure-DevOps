"""Mapeamento de nomes de recursos para emails"""
from typing import Dict, Optional

# Mapeamento de nomes para emails - Lista atualizada
RESOURCE_EMAIL_MAP: Dict[str, str] = {
    "Alessandra Pardin": "alessandra.pardin@qualiit.com.br",
    "Arthur Nagae": "arthur.nagae@qualiit.com.br",
    "Cristiane Bortollo": "cristiane.bortollo@qualiit.com.br",
    "Cristiano Baierski": "cristiano.baierski@qualiit.com.br",    
    "Daniel Bragion": "daniel.bragion@qualiit.com.br",
    "Daniel Souza": "daniel.souza@qualiit.com.br",
    "Daniela": "daniela@qualiit.com.br",
    "Denilson Maia": "denilson.maia@qualiit.com.br",
    "Emely Pereira Souza": "emely.souza@qualiit.com.br",
    "Fernando Dandalo": "fernando.dandalo@qualiit.com.br",
    "Filipe Amorim": "filipe.amorim@qualiit.com.br",
    "Flavio Kussunoki": "flavio.kussunoki@qualiit.com.br",
    "Flavio Silveira": "flavio.silveira@qualiit.com.br",
    "Germano Schreiber": "germano.schreiber@qualiit.com.br",
    "Hagleyson Leite": "hagleyson.leite@qualiit.com.br",
    "Heber Carmo": "heber.carmo@qualiit.com.br",
    "Hendri Rodrigues": "hendri.rodrigues@qualiit.com.br",
    "Henrique Favarin": "henrique.favarin@qualiit.com.br",
    "Italo Sanches": "italo.sanches@qualiit.com.br",
    "Jeferson Boso": "jeferson.boso@qualiit.com.br",
    "Jessica Barbosa": "jessica.barbosa@qualiit.com.br",
    "Josias Afelis": "josias.afelis@qualiit.com.br",
    "Kayque Santos": "kayque.santos@qualiit.com.br",
    "Lucas Mendes": "lucas.mendes@qualiit.com.br",
    "Luis Eduardo Lima": "luis.lima@qualiit.com.br",
    "Luiz Sousa": "luiz.sousa@qualiit.com.br",
    "Marcelo Macedo": "marcelo.macedo@qualiit.com.br",
    "Marcelo Severo": "marcelo.severo@qualiit.com.br",
    "Marcio Sacramoni": "marcio.sacramoni@qualiit.com.br",
    "Matheus Cristofolini": "matheus.cristofolini@qualiit.com.br",
    "Matheus Malara": "matheus.malara@qualiit.com.br",
    "Miguel Abreu": "miguel.abreu@qualiit.com.br",
    "Nanci Rocha": "nanci.rocha@qualiit.com.br",
    "Paulo Pazin": "paulo.pazin@qualiit.com.br",
    "Pedro Pilz - Quali IT": "pedro.pilz@qualiit.com.br",
    "Thatiane Carrijo": "thatiane.carrijo@qualiit.com.br",
    "Tiago Oliveira": "tiago.oliveira@qualiit.com.br",
    "Vanessa Monteiro": "vanessa.monteiro@qualiit.com.br",
    "Victor Alves": "victor.alves@qualiit.com.br",
    "Vinicius Fava": "vinicius.fava@qualiit.com.br",
    "Wilson Santos": "wilson.santos@qualiit.com.br",
    # Variações comuns
    "Cliente": None,  # Cliente não tem email específico
    "Cliente[1]": None,
}

def get_email_by_resource_name(resource_name: str) -> Optional[str]:
    """
    Retorna o email associado ao nome do recurso.
    
    Suporta variações comuns como:
    - "Nome[%]" (ex: "Jessica Barbosa[50%]")
    - "Nome[1]" (ex: "Cliente[1]")
    - Busca case-insensitive
    
    Args:
        resource_name: Nome do recurso do arquivo .mpp (pode incluir [%] ou [número])
        
    Returns:
        Email do recurso ou None se não encontrado
    """
    if not resource_name or not resource_name.strip():
        return None
    
    # Remove variações como [50%], [1], etc.
    clean_name = resource_name.strip()
    if '[' in clean_name:
        clean_name = clean_name.split('[')[0].strip()
    
    # Busca exata
    if clean_name in RESOURCE_EMAIL_MAP:
        email = RESOURCE_EMAIL_MAP[clean_name]
        return email if email else None
    
    # Busca case-insensitive
    clean_name_lower = clean_name.lower()
    for name, email in RESOURCE_EMAIL_MAP.items():
        if name.lower() == clean_name_lower:
            return email if email else None
    
    return None

def get_all_resources() -> Dict[str, str]:
    """Retorna todos os mapeamentos de recursos"""
    return RESOURCE_EMAIL_MAP.copy()

