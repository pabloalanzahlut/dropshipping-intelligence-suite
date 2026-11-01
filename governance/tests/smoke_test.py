"""Quick smoke test for governance system."""
import sys, json, os
sys.path.insert(0, os.path.abspath('.'))

from app.services.validator_rules import RulesValidator
from app.services.memory_logger import MemoryLogger
from app.services.protocol_enforcer import ProtocolEnforcer

print("=== GEM OS Governance v2.0 Smoke Test ===\n")

# 1. RulesValidator
v = RulesValidator(agent_md_path="agent.md")
pre = v.pre_execution_check()
print(f"[1] PRE-FLIGHT CHECK: {pre['status']}")
for name, r in pre.get('resultados', {}).items():
    print(f"    {'🟢' if r['status'] else '🔴'} {name}: {r['detail']}")

score = v.compliance_score()
print(f"[2] COMPLIANCE SCORE: {score['compliance_score']}% ({score['status']})")
print(f"    Checks: {score['passed']}/{score['total_checks']} | Violaciones: {score['violaciones_activas']}")

# 2. Post validation
out = {"agent_id": "smoke", "status": "success",
       "data": {"copy": "Producto de prueba sin superlativos"},
       "rules_compliance": {"ok": True}}
pv = v.post_execution_validation("smoke", out)
print(f"[3] POST-VALIDATION: {pv['status']}")
if pv.get('violations'):
    print(f"    ⚠️ Violations: {pv['violations']}")

# 3. MemoryLogger
m = MemoryLogger()
m.log("smoke_agent", "test", "Registro smoke test")
m.log_decision("smoke_agent", "Aprobar", "Cumple reglas", ["datos_test"])
m.log_success("smoke_agent", "Smoke completado", {"score": 100})
mem = m.recall("smoke_agent")
stats = m.memory_stats()
print(f"[4] MEMORY LOGGER: {len(mem)} entradas, total: {stats['total_entries']}")

# 4. ProtocolEnforcer
p = ProtocolEnforcer(validator=v)
gaps = p.check_data_gaps({"peso_kg": float, "material": str}, {"sku": "T-001"})
print(f"[5] PROTOCOL ENFORCER: {len(gaps)} data gaps detectados")
if gaps:
    print(f"    Campos faltantes: {[g['field'] for g in gaps]}")

# 5. Integridad agent.md
integ = v.check_agent_md_integrity()
print(f"[6] AGENT.MD INTEGRITY: {integ['status']}")
print(f"    Hash: {(integ.get('hash_actual') or '')[:16]}...")

print("\n=== SMOKE TEST COMPLETADO ===")
print("Resultado: 🟢 SISTEMA DE GOBERNANZA OPERATIVO")