# Workflow: Pipeline Completo de Transcripción

## Descripción
Orquesta el flujo end-to-end desde archivo de texto hasta ingestión en KB y feed a GEM.

## Agentes Involucrados
1. **utf8-validator**: Valida encoding y repara corrupción
2. **duplicate-detector**: Detecta duplicados semánticos
3. **security-guardian**: Valida seguridad zero-trust
4. **kb-ingestor**: Ingresa datos a Knowledge Base
5. **gem-feeder**: Alimenta modelo GEM con datos validados
6. **qa-validator**: Ejecuta tests de regresión
7. **doc-guardian**: Sincroniza documentación
8. **orchestrator**: Coordina todo el pipeline

## DAG (Directed Acyclic Graph)
```
[START]
   ↓
[utf8-validator] ──(REJECT)──→ [ERROR_HANDLER] → [END_FAIL]
   ↓ (PASS/REPAIRED)
[duplicate-detector] ──(DUPLICATE)──→ [SKIP_LOG] → [END_SKIP]
   ↓ (UNIQUE)
[security-guardian] ──(VIOLATION)──→ [SECURITY_ALERT] → [END_HALT]
   ↓ (COMPLIANT)
[kb-ingestor] ──(ERROR)──→ [ROLLBACK_KB] → [END_FAIL]
   ↓ (SUCCESS)
[gem-feeder] ──(ERROR)──→ [ROLLBACK_GEM] → [END_FAIL]
   ↓ (SUCCESS)
[qa-validator] ──(FAIL)──→ [BLOCK_DEPLOY] → [END_REJECTED]
   ↓ (PASS)
[doc-guardian] ──(OUT_OF_SYNC)──→ [BLOCK_MERGE] → [END_PENDING]
   ↓ (SYNCED)
[orchestrator: SCORING]
   ↓ (Score ≥ 70)
[DEPLOY_APPROVED] → [PUSH_TO_PROD] → [END_SUCCESS]
   ↓ (Score < 70)
[DEPLOY_REJECTED] → [ROLLBACK] → [END_FAIL]
```

## Estados del Pipeline
| Estado | Descripción | Acción |
|--------|-------------|--------|
| IDLE | Esperando input | - |
| VALIDATING | Validación UTF-8 | Auto-repair o reject |
| HASHING | Generando hash semántico | Comparar con KB |
| SECURITY_CHECK | Validación zero-trust | Allow o block |
| KB_INGEST | Ingresando a KB | Transaction commit |
| GEM_FEED | Alimentando GEM | Update embeddings |
| QA_VALIDATION | Tests de regresión | Pass o fail |
| DOC_SYNC | Sincronizando docs | Approve o block |
| SCORING | Calculando score | Go o no-go |
| COMPLETE | Éxito total | Deploy a prod |
| FAILED | Error crítico | Rollback + alert |

## Configuración de Reintentos
```yaml
retry_policy:
  max_attempts: 3
  backoff: exponential
  initial_delay_ms: 1000
  max_delay_ms: 30000
  jitter: true
  retryable_errors:
    - TEMP_DB_LOCK
    - NETWORK_TIMEOUT
    - RATE_LIMIT_EXCEEDED
  non_retryable_errors:
    - CORRUPTION_HIGH
    - SECURITY_VIOLATION
    - DUPLICATE_EXACT
```

## Métricas del Pipeline
- **Throughput**: Transcripciones procesadas por minuto
- **Latencia**: Tiempo promedio end-to-end (p50, p95, p99)
- **Error Rate**: Porcentaje de transacciones fallidas
- **Success Rate**: Porcentaje de deploy aprobados
- **Rollback Rate**: Frecuencia de rollbacks automáticos

## Logs y Trazabilidad
- Cada transacción tiene UUID único
- Logs estructurados en JSON por agente
- Trace ID propagado a través de todo el pipeline
- Export a sistema de monitoreo centralizado
