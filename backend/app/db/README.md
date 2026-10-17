# db/ — Persistencia (Dev B)

Modelos SQLAlchemy, sesión, repositorios y `migrations/` (Alembic). Entidades y campos: `docs/DATA_MODEL.md`.

- Los repositorios **implementan las interfaces de `ports`** (sección Ports de `docs/DATA_MODEL.md`).
- `DATABASE_URL` decide SQLite (local) o Postgres/Neon (producción): el mismo código para ambos; probar migraciones en los dos.
- `decisions` es **append-only**: sin update ni delete.
- "Gasto del periodo" = suma de `amount_base_currency` de facturas con estado efectivo `paid` o `approved`.
- Debe existir seed (empresa ficticia + dataset) y reset.
- Solo Dev B crea revisiones de Alembic.
