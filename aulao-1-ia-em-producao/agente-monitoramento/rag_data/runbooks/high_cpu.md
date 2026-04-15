# Runbook: High CPU Usage

## Sintomas
- CPU usage > 80% por mais de 5 minutos
- Aumento de latência (p99 > 500ms)
- Possível throttling de containers

## Causas Comuns
1. **Carga elevada legítima** — pico de tráfego (Black Friday, campanhas)
2. **Loop infinito ou regex catastrófica** — deploy recente com bug
3. **GC thrashing** — JVM ou Python com heap mal configurado
4. **Cron job pesado** — job de background competindo com tráfego

## Diagnóstico
```bash
# Verificar top processes
kubectl top pods -n production --sort-by=cpu

# Verificar se houve deploy recente
kubectl rollout history deployment/<service>

# Flame graph (se pprof habilitado)
go tool pprof http://localhost:6060/debug/pprof/profile
```

## Ações de Mitigação
1. **Imediata**: Scale up horizontal (HPA ou manual)
   ```bash
   kubectl scale deployment/<service> --replicas=<N+2>
   ```
2. **Se deploy recente**: Rollback
   ```bash
   kubectl rollout undo deployment/<service>
   ```
3. **Se cron job**: Pausar ou reescalonar job
4. **Longo prazo**: Profiling, otimização de código, ajuste de limites

## Escalação
- P1 (> 95% CPU, latência degradada): Escalar para SRE on-call
- P2 (> 80% CPU, sem impacto visível): Monitorar por 15 min, escalar se persistir
