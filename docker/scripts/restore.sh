#!/usr/bin/env bash
# restore.sh — OntoFuel Data Restore Automation Script
# Waits for PostgreSQL, runs schema init, restores ontology data from JSON.
# Usage: restore.sh [PATH_TO_ONTOLOGY_JSON]
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

ONTOLOGY_JSON="${1:-${PROJECT_ROOT}/memory/trustgraph-fix/material_ontology_enhanced.json}"

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
DB_NAME="${DB_NAME:-postgres}"

SCHEMA_SQL="${PROJECT_ROOT}/docker/supabase/init/01_schema.sql"

export PGPASSWORD="${DB_PASSWORD}"
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

# ---------------------------------------------------------------------------
# Step 1: Wait for PostgreSQL to be ready (max 60 seconds)
# ---------------------------------------------------------------------------
echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT} ..."
elapsed=0
until pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -q; do
    if [ "$elapsed" -ge 60 ]; then
        echo "ERROR: PostgreSQL not ready after 60 seconds" >&2
        exit 1
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done
echo "PostgreSQL is ready (${elapsed}s)."

# ---------------------------------------------------------------------------
# Step 2: Run schema init SQL (idempotent — uses IF NOT EXISTS)
# ---------------------------------------------------------------------------
echo "Running schema init: ${SCHEMA_SQL}"
psql "${DATABASE_URL}" -f "${SCHEMA_SQL}" -q
echo "Schema initialised."

# ---------------------------------------------------------------------------
# Step 3: Restore data from ontology JSON via Python + psycopg2
# ---------------------------------------------------------------------------
echo "Restoring data from: ${ONTOLOGY_JSON}"

python3 -c "
import json, sys, os
import psycopg2

ONTOLOGY_PATH = os.environ.get('ONTOLOGY_JSON_PATH', '${ONTOLOGY_JSON}')
DATABASE_URL  = '${DATABASE_URL}'

# --- Load ontology JSON ---
with open(ONTOLOGY_PATH, 'r') as f:
    ontology = json.load(f)

individuals = ontology.get('individuals', {})
if not individuals:
    print('WARNING: No individuals found in ontology JSON')
    sys.exit(0)

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
cur = conn.cursor()

try:
    # --- Idempotent: clear existing data (respect FK order) ---
    cur.execute('DELETE FROM material_properties')
    cur.execute('DELETE FROM material_composition')
    cur.execute('DELETE FROM irradiation_behavior')
    cur.execute('DELETE FROM literature_sources')
    cur.execute('DELETE FROM materials')
    conn.commit()
    print('Cleared existing data.')

    # --- Restore individuals ---
    material_count = 0
    property_count = 0

    for name, data in individuals.items():
        ind_type = data.get('type', '')
        # Extract short type name from URI
        if '#' in ind_type:
            ind_type = ind_type.split('#')[-1]

        # Insert material record
        cur.execute(
            'INSERT INTO materials (name, material_type) VALUES (%s, %s) ON CONFLICT (name) DO UPDATE SET material_type = EXCLUDED.material_type RETURNING id',
            (name, ind_type)
        )
        row = cur.fetchone()
        if row is None:
            continue
        material_id = row[0]
        material_count += 1

        # Insert data properties (numeric and string values, skip URI/type fields)
        skip_keys = {'uri', 'type'}
        for prop_name, prop_value in data.items():
            if prop_name in skip_keys:
                continue
            # Determine value type
            if isinstance(prop_value, (int, float)):
                cur.execute(
                    'INSERT INTO material_properties (material_id, property_name, property_value) VALUES (%s, %s, %s)',
                    (material_id, prop_name, float(prop_value))
                )
            elif isinstance(prop_value, str):
                # Try to parse as float
                try:
                    fv = float(prop_value)
                    cur.execute(
                        'INSERT INTO material_properties (material_id, property_name, property_value) VALUES (%s, %s, %s)',
                        (material_id, prop_name, fv)
                    )
                except ValueError:
                    cur.execute(
                        'INSERT INTO material_properties (material_id, property_name, value_string) VALUES (%s, %s, %s)',
                        (material_id, prop_name, prop_value)
                    )
            else:
                # Store complex values as JSON string
                cur.execute(
                    'INSERT INTO material_properties (material_id, property_name, value_string) VALUES (%s, %s, %s)',
                    (material_id, prop_name, json.dumps(prop_value))
                )
            property_count += 1

    conn.commit()
    print(f'Restored {material_count} materials, {property_count} properties.')

except Exception as e:
    conn.rollback()
    print(f'ERROR during restore: {e}', file=sys.stderr)
    sys.exit(1)
finally:
    cur.close()
    conn.close()
"

echo "Restore complete."
exit 0
