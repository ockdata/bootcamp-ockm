# Runbook de Incidentes de Seguranca

## Severidades

- Sev 1: vazamento em andamento, indisponibilidade critica ou risco regulatorio alto.
- Sev 2: comportamento suspeito com impacto relevante, mas contido.
- Sev 3: investigacao preventiva sem impacto confirmado.

## Passos iniciais

1. Abrir incidente no canal `#war-room`.
2. Identificar owner tecnico e owner de negocio.
3. Preservar evidencias e impedir destruicao de logs.
4. Revogar credenciais comprometidas e rotacionar segredos se necessario.

## Comunicacao

Incidentes Sev 1 exigem atualizacao executiva a cada 30 minutos. O time juridico deve ser acionado quando houver suspeita de exposicao de dados pessoais.

## Encerramento

Todo incidente fechado precisa gerar postmortem com linha do tempo, causa raiz, impacto, acoes corretivas e plano de prevencao.
