# Runbook: Memory Leak / OOMKilled

## Sintomas
- Container reiniciando com status OOMKilled
- Uso de memória crescente e constante (sem platô)
- RSS crescendo mas heap estável (leak nativo)
- Latência degradando gradualmente antes do OOM

## Causas Comuns
1. **Memory leak em código** — objetos não liberados, caches sem TTL
2. **Connection pool crescendo** — conexões DB/Redis não fechadas
3. **Buffer acumulando** — streaming sem backpressure
4. **Deploy com regressão** — nova versão consumindo mais memória
5. **Dados grandes em memória** — query sem LIMIT, arquivo grande em memória

## Diagnóstico
```bash
# Verificar OOMKilled events
kubectl describe pod <pod-name> | grep -A5 "Last State"

# Memory usage ao longo do tempo
kubectl top pods -n production --sort-by=memory

# Heap dump (Java)
jmap -dump:live,format=b,file=heap.hprof <pid>

# Memory profiling (Python)
# Adicionar: import tracemalloc; tracemalloc.start()
```

## Ações de Mitigação
1. **Imediata**: Aumentar memory limit do container
   ```yaml
   resources:
     limits:
       memory: "2Gi"  # dobrar do atual
   ```
2. **Se deploy recente**: Rollback para versão anterior
3. **Restart programado**: CronJob para restart pods periodicamente (paliativo)
4. **Longo prazo**: Profiling de memória, adicionar métricas de heap

## Escalação
- OOMKilled repetido (> 3x em 1h): P1 — escalar para SRE + Dev owner
- Crescimento lento: P2 — ticket para investigação
