"""Step 6: explanation built by template from the checks. It never changes the outcome."""

from app.schemas import CheckStatus, EngineResult, ExtractedInvoice, Outcome

SOURCE_LABELS = {
    "groq": "Groq",
    "openrouter": "OpenRouter",
    "cache": "una lectura guardada",
    "local": "el lector local (sin IA)",
    "stored": "los datos ya registrados de la factura (reevaluación con las reglas actuales)",
}

HEADINGS = {
    Outcome.pay: "Pago simulado: todas las reglas se cumplen.",
    Outcome.block: "Frenada: incumple una regla que no admite excepciones automáticas.",
    Outcome.escalate: "Pendiente de aprobación: una persona debe revisarla antes de pagar.",
}


def explain(result: EngineResult, invoice: ExtractedInvoice | None, source: str, error: str | None) -> str:
    lines = [HEADINGS[result.outcome]]
    failed = [c for c in result.checks if c.status == CheckStatus.failed]
    for check in failed:
        detail = f" (visto: {check.observed}; esperado: {check.expected})" if check.observed and check.expected else ""
        lines.append(f"• {check.rule_id} · {check.message}{detail}")
    passed = sum(1 for c in result.checks if c.status == CheckStatus.passed)
    lines.append(f"Reglas comprobadas: {passed} cumplidas, {len(failed)} incumplidas, "
                 f"{len(result.checks) - passed - len(failed)} sin aplicar.")
    if invoice is None:
        lines.append("No se pudieron leer los datos de la factura" + (f" ({error})." if error else "."))
    else:
        label = f"Gemini ({source})" if source.startswith("gemini") else SOURCE_LABELS.get(source, source)
        lines.append(f"Datos leídos con {label}.")
    lines.append("No se movió dinero real: los pagos de esta demo son simulados.")
    return "\n".join(lines)
