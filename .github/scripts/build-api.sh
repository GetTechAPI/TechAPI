#!/usr/bin/env bash
# Validate the data, then regenerate the static API (site/public/v1 and
# site/public/openapi.json) and the verification aggregate
# (data/_verify/status.json) with the pinned TechEngine, and check the result.
# pages.yml runs this before publishing.
#
# Needs the TechEngine submodule checked out (never recursively) and its
# dependencies installed: python -m pip install -e ./TechEngine
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export TECHAPI_DATA_DIR="$PWD/data"

# Engine steps run with every proxy pointed at a closed local port, so a
# future engine change cannot make this job reach third-party sites.
offline() {
  local p=http://127.0.0.1:9
  HTTP_PROXY=$p HTTPS_PROXY=$p ALL_PROXY=$p http_proxy=$p https_proxy=$p all_proxy=$p \
    NO_PROXY= no_proxy= "$@"
}

echo "::group::Bundled validator"
python -m app.validate
echo "::endgroup::"

# From the repository root, TechAPI's own app/ package would shadow the engine's.
cd TechEngine

echo "::group::Engine validator and integrity gate"
offline python -m app.validate
offline python integrity_check.py ../data --strict
echo "::endgroup::"

echo "::group::Generate the API"
# Start from an empty v1/ except the hand-made games pointer, so the output is
# exactly what this data produces, whatever git still tracks. A leftover
# techapi.db would make the dump stale: seeding only inserts new slugs.
mkdir -p ../site/public/v1
find ../site/public/v1 -mindepth 1 -maxdepth 1 ! -name games -exec rm -rf {} +
rm -f ../site/public/openapi.json techapi.db
offline python -m app.verify status --output ../data/_verify/status.json
offline python -m app.dump --output ../site/public
echo "::endgroup::"

offline python ../.github/scripts/check_dump.py ../site/public ../data
