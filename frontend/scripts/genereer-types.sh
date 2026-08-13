#!/usr/bin/env bash
# Genereert frontend/generated/types.ts uit api/generated/openapi.json (werkwijze-ADR-0017,
# stack-profiel.md §Contractgeneratie).
#
# Leest via een relatief pad rechtstreeks het schema van de `api`-service, zolang beide
# services in dezelfde monorepo staan (ADR-0017 "Schema-toegang"). Draai eerst
# `api/scripts/genereer-types.sh` als het schema nog niet (opnieuw) is weggeschreven. Bewerk
# `generated/types.ts` nooit met de hand.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

SCHEMA="../api/generated/openapi.json"

if [ ! -f "$SCHEMA" ]; then
  echo "Schema niet gevonden: $SCHEMA — draai eerst api/scripts/genereer-types.sh" >&2
  exit 1
fi

mkdir -p generated

npx --yes openapi-typescript "$SCHEMA" -o generated/types.ts

echo "Geschreven: frontend/generated/types.ts"
