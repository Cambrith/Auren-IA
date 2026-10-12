#!/usr/bin/env bash
# Isolated upstream dependencies; no system package installation.
set -euo pipefail
cd "$(dirname "$0")/.."
task_runtime="$PWD/.cavren/runtime"
mkdir -p "$task_runtime"
if [ ! -x "$task_runtime/uv" ]; then
  curl -fL https://github.com/astral-sh/uv/releases/download/0.13.0/uv-x86_64-unknown-linux-gnu.tar.gz -o "$task_runtime/uv.tar.gz"
  tar -xzf "$task_runtime/uv.tar.gz" -C "$task_runtime" --strip-components=1
fi
if [ ! -x "$task_runtime/node/bin/node" ]; then
  task_node="node-v22.23.3-linux-x64"
  curl -fL "https://nodejs.org/dist/v22.23.3/$task_node.tar.xz" -o "$task_runtime/$task_node.tar.xz"
  curl -fL https://nodejs.org/dist/v22.23.3/SHASUMS256.txt -o "$task_runtime/node-checksums.txt"
  (cd "$task_runtime"; rg "  $task_node.tar.xz$" node-checksums.txt | sha256sum --check -)
  tar -xJf "$task_runtime/$task_node.tar.xz" -C "$task_runtime"
  ln -s "$task_node" "$task_runtime/node"
fi
export PATH="$task_runtime/node/bin:$PATH"
export CYPRESS_INSTALL_BINARY=0 SHARP_IGNORE_GLOBAL_LIBVIPS=1
npm ci --no-audit --no-fund
"$task_runtime/uv" python install 3.12
if [ ! -x .cavren/venv/bin/python ]; then
  "$task_runtime/uv" venv --python 3.12 .cavren/venv
fi
"$task_runtime/uv" pip install --python .cavren/venv/bin/python --torch-backend cpu -r backend/requirements.txt
NODE_OPTIONS=--max-old-space-size=8192 npm run build
