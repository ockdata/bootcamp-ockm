# -----------------------------------------------------------------------------
# DETECÇÃO DE SISTEMA OPERACIONAL E CONFIGURAÇÕES
# -----------------------------------------------------------------------------
ifeq ($(OS),Windows_NT)
    VENV_NAME = .venv
    PYTHON = $(VENV_NAME)\Scripts\python
    ACTIVATE_MSG = .venv\Scripts\activate
    PYTHON_BIN = python
else
    VENV_NAME = .venv
    PYTHON = $(VENV_NAME)/bin/python
    ACTIVATE_MSG = source .venv/bin/activate
    PYTHON_BIN = $(shell command -v python3 || command -v python)
endif

# Variáveis do GCP
PROJECT_ID ?= mestrado-insper
REGION     ?= us-central1
REPO_NAME   = data-etl-repo
IMAGE_NAME  = etl-monorepo
REGISTRY_URL = $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(REPO_NAME)

JOB ?= job_template
WF  ?= daily_pipeline

.PHONY: help setup clean run-job docker-build docker-run infra-init infra-plan infra-apply cloud-run init \
        workflow-init workflow-validate workflow-run workflow-status workflow-list test auth-configure deploy

# -----------------------------------------------------------------------------
# AJUDA
# -----------------------------------------------------------------------------
help: ## Mostra esta mensagem de ajuda
	@$(PYTHON) -c "import re; lines = open('Makefile', encoding='utf-8').readlines(); [print(f'\033[36m{m.group(1):<20}\033[0m {m.group(2)}') for l in lines for m in [re.search(r'^([a-zA-Z_-]+):.*?## (.*)$$', l)] if m]"

# -----------------------------------------------------------------------------
# DESENVOLVIMENTO LOCAL
# -----------------------------------------------------------------------------
setup: ## Cria venv e instala dependências
	$(PYTHON_BIN) -m venv $(VENV_NAME)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	@echo "Ambiente configurado! Ative com: $(ACTIVATE_MSG)"

clean: ## Limpa arquivos temporários
	@$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
	@$(PYTHON) -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]"
	@$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['.pytest_cache', '.coverage'] if pathlib.Path(p).exists()]"

run-job: ## Roda job localmente (suporta .env). Ex: make run-job JOB=ingest_lojas
	@$(PYTHON) scripts/run_job.py "$(PYTHON)" "$(JOB)"

test: ## Roda testes unitários
	$(PYTHON) -m pytest tests/ -v

# -----------------------------------------------------------------------------
# DOCKER (Simulação e Deploy Manual)
# -----------------------------------------------------------------------------
auth-configure: ## Configura autenticação do Docker no GCP (rodar 1 vez)
	gcloud auth configure-docker $(REGION)-docker.pkg.dev

docker-build: ## Constrói a imagem Docker localmente
	docker build --platform linux/amd64 -t $(IMAGE_NAME) .

docker-run: ## Roda via Docker (suporta .env). Ex: make docker-run JOB=ingest_lojas
	docker run --rm --env-file .env -e JOB_NAME=$(JOB) -e GCP_PROJECT=$(PROJECT_ID) -v $(HOME)/.config/gcloud:/root/.config/gcloud $(IMAGE_NAME)

deploy: ## Build manual e Push para o Artifact Registry
	@echo "Buildando imagem..."
	docker build --platform linux/amd64 -t $(IMAGE_NAME) .
	@echo "Tagueando..."
	docker tag $(IMAGE_NAME) $(REGISTRY_URL)/$(IMAGE_NAME):latest
	@echo "Enviando para o Google Cloud..."
	docker push $(REGISTRY_URL)/$(IMAGE_NAME):latest
	@echo "Imagem atualizada!"

# -----------------------------------------------------------------------------
# INFRAESTRUTURA (Terraform)
# -----------------------------------------------------------------------------
infra-init: ## Inicializa o Terraform
	cd infra && terraform init

infra-plan: ## Planeja mudanças
	cd infra && terraform plan -var="project_id=$(PROJECT_ID)"

infra-apply: ## Aplica mudanças na nuvem
	cd infra && terraform apply -var="project_id=$(PROJECT_ID)" -auto-approve

# -----------------------------------------------------------------------------
# OPERAÇÃO (Cloud Run)
# -----------------------------------------------------------------------------
cloud-run: ## Dispara o job na nuvem. Ex: make cloud-run JOB=ingest-lojas
	gcloud run jobs execute $(JOB) --region=$(REGION) --project=$(PROJECT_ID)

# -----------------------------------------------------------------------------
# AUTOMAÇÃO (Gerador de Jobs)
# -----------------------------------------------------------------------------
init: ## Cria um novo job do zero. Ex: make init JOB=ingest_marketing
	@$(PYTHON) scripts/init_job.py $(JOB)

# -----------------------------------------------------------------------------
# WORKFLOWS (GCP Workflows)
# -----------------------------------------------------------------------------
workflow-init: ## Cria estrutura de um novo workflow. Ex: make workflow-init WF=daily_sales
	@$(PYTHON) scripts/init_workflow.py $(WF)

workflow-validate: ## Valida todos os arquivos workflow.yaml
	@echo "Validando workflows..."
	@$(PYTHON) scripts/validate_workflow.py

workflow-run: ## Executa workflow no GCP. Ex: make workflow-run WF=daily-ingest
	@echo "Executando workflow $(WF)..."
	gcloud workflows run $(WF) --location=$(REGION) --project=$(PROJECT_ID)

workflow-status: ## Mostra status da ultima execucao. Ex: make workflow-status WF=daily-ingest
	@echo "Status do workflow $(WF):"
	gcloud workflows executions list $(WF) --location=$(REGION) --project=$(PROJECT_ID) --limit=5

workflow-list: ## Lista todos os workflows disponiveis
	@echo "Workflows locais (em /workflows):"
	@$(PYTHON) -c "from pathlib import Path; wfs = list(Path('workflows').iterdir()) if Path('workflows').exists() else []; print('  ' + chr(10).join('  '+p.name for p in wfs) if wfs else '  Nenhum workflow encontrado')"
	@echo ""
	@echo "Workflows no GCP:"
	@gcloud workflows list --location=$(REGION) --project=$(PROJECT_ID) 2>/dev/null || echo "  Nenhum workflow no GCP"
