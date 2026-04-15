# Runbook: Spike de Erros 5xx

## Sintomas
- Taxa de erros 5xx > 1% do tráfego
- Aumento súbito em logs de erro
- Alertas de SLO/SLA disparando
- Usuários reportando "erro interno"

## Causas Comuns
1. **Deploy com bug** — novo código com null pointer, tipo errado, etc.
2. **Dependência fora** — banco de dados, cache, serviço downstream
3. **Rate limiting / throttling** — API externa retornando 429→502
4. **Certificado expirado** — TLS handshake falhando
5. **Configuração errada** — env var ausente, feature flag incorreto

## Diagnóstico
```bash
# Taxa de erro por serviço (últimos 15 min)
# No BigQuery/Logs Explorer:
SELECT service, COUNT(*) as errors
FROM logs
WHERE status >= 500 AND timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
GROUP BY service ORDER BY errors DESC

# Verificar deploy recente
kubectl rollout history deployment/checkout

# Verificar dependências
curl -s http://payments-service:8080/health
curl -s http://inventory-service:8080/health
```

## Ações de Mitigação
1. **Se deploy recente (< 30 min)**: Rollback imediato
   ```bash
   kubectl rollout undo deployment/<service>
   ```
2. **Se dependência fora**: Ativar circuit breaker, retornar fallback
3. **Se rate limiting**: Implementar backoff, redistribuir carga
4. **Se certificado**: Renovar certificado, verificar cert-manager

## SLO Impact
- Error budget: cada minuto com > 1% errors consome ~2h de budget mensal
- Se error budget < 20%: congelar deploys até estabilizar

## Escalação
- > 5% errors: P1 — all hands, war room
- > 1% errors: P2 — on-call investiga, notifica team lead
- < 1% errors: P3 — monitorar, investigar no próximo dia útil
