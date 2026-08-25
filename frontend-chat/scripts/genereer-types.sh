#!/usr/bin/env bash
# Genereert frontend-chat/generated/types.ts uit api/generated/openapi.json (zelfde patroon als
# frontend/scripts/genereer-types.sh, werkwijze-ADR-0017).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

SCHEMA="../api/generated/openapi.json"

if [ ! -f "$SCHEMA" ]; then
  echo "Schema niet gevonden: $SCHEMA — draai eerst api/scripts/genereer-types.sh" >&2
  exit 1
fi

mkdir -p generated

npx --yes openapi-typescript "$SCHEMA" -o generated/types.ts

echo "Geschreven: frontend-chat/generated/types.ts"
