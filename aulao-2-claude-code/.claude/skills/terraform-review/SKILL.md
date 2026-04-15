---
name: terraform-review
description: 'Reviews Terraform infrastructure code for security issues, best practices, and compliance with project standards. Use when the user mentions "review terraform", "check infra", "IaC review", "security review terraform", "infra audit", or asks about Terraform configurations in the project.'
allowed-tools: Read, Glob, Grep, Bash
---

# Terraform Review — Security & Best Practices

Revisa a infraestrutura Terraform do monorepo ETL.

## Escopo de análise

Foque nos arquivos em `aulao-1-ia-em-producao/etl-monorepo/infra/`:
- `main.tf` — provider e backend
- `variables.tf` — variáveis e locals
- `iam.tf` — service accounts e IAM bindings
- `job_*.tf` — recursos de cada job
- `modules/cloud_run_job/` — módulo reutilizável

## Checklist de segurança

### IAM & Least Privilege
- Service accounts com roles mínimas necessárias?
- Nenhum `roles/editor` ou `roles/owner`?
- Bindings são por service account, não por projeto inteiro?
- Grep por `allUsers` ou `allAuthenticatedUsers` — devem ser zero

### Secrets
- Grep por `password`, `secret`, `token`, `api_key` em arquivos .tf
- Secrets são referenciados via `google_secret_manager_secret_version`?
- Nenhum secret em `env_vars` dos Cloud Run Jobs?

### Rede
- Nenhum `0.0.0.0/0` em firewall rules ou ingress?
- Cloud Run Jobs configurados como `internal` quando possível?

### Estado
- Backend remoto configurado (GCS)?
- State file não está no repositório? (grep por `.tfstate`)

### Módulo
- Módulo `cloud_run_job` é usado consistentemente?
- Todos os job_*.tf seguem o mesmo padrão?
- Variáveis obrigatórias estão sendo passadas?

## Validação adicional

Se possível, execute:
```bash
cd aulao-1-ia-em-producao/etl-monorepo/infra && terraform fmt -check -recursive && terraform validate
```

## Output

```
# Terraform Review Report

## Score: X/10

## Segurança
- [CRITICAL/WARNING/OK] descrição do achado

## Consistência
- [WARNING/OK] descrição do achado

## Recomendações
1. [lista priorizada por severidade]
```
