#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2020 CERN.
# SPDX-FileCopyrightText: 2022 Graz University of Technology.
# SPDX-License-Identifier: MIT

# Quit on errors
set -o errexit

# Quit on unbound symbols
set -o nounset

# Always bring down docker services
function cleanup() {
    eval "$(docker-services-cli down --env)"
}
trap cleanup EXIT


python -m sphinx.cmd.build -qnN docs docs/_build/html
eval "$(docker-services-cli up --db ${DB:-postgresql} --search ${SEARCH:-opensearch} --env)"
python -m pytest
tests_exit_code=$?
exit "$tests_exit_code"
