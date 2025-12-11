.PHONY: help install install-dev test test-cov lint format type-check security clean run profile benchmark

help: ## Mostra esta mensagem de ajuda
	@echo "Comandos disponíveis:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Instala dependências de produção
	pip install -r requirements.txt

install-dev: ## Instala dependências de desenvolvimento
	pip install -r requirements-dev.txt
	pre-commit install

test: ## Executa testes
	pytest tests/ -v

test-unit: ## Executa apenas testes unitários
	pytest tests/unit/ -v

test-integration: ## Executa apenas testes de integração
	pytest tests/integration/ -v

test-cov: ## Executa testes com cobertura
	pytest tests/ --cov=app --cov-report=term-missing --cov-report=html

lint: ## Executa linters (Ruff, Flake8)
	ruff check app/
	flake8 app/

format: ## Formata código (Black, Ruff)
	black app/ tests/
	ruff format app/ tests/

format-check: ## Verifica formatação sem alterar arquivos
	black --check app/ tests/
	ruff format --check app/ tests/

type-check: ## Verifica tipos com MyPy
	mypy app/

security: ## Verifica segurança com Bandit
	bandit -r app/ -f json -o bandit-report.json

quality: format lint type-check security ## Executa todas as verificações de qualidade

clean: ## Remove arquivos temporários
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf coverage.xml
	rm -rf dist
	rm -rf build

run: ## Inicia o servidor de desenvolvimento
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Inicia o servidor de produção
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

profile: ## Executa profiling de código
	python scripts/profile_code.py

benchmark: ## Executa benchmark de performance
	python scripts/performance_benchmark.py

ci: ## Executa todas as verificações para CI/CD
	format-check
	lint
	type-check
	security
	test-cov
