# Regen Full-Stack Test Environment
# Used for manual and automated testing of code generation capabilities with KOI MCP.
#
# Includes: Go, Rust, Python, Node.js.
# Repos (e.g., regen-ledger) are cloned on first container create (see setup-repos).

FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install base dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    pkg-config \
    libssl-dev \
    jq \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# Go 1.22 (for regen-ledger / NU-01 tests)
# ============================================
ENV GO_VERSION=1.22.0
RUN wget -q https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz \
    && rm go${GO_VERSION}.linux-amd64.tar.gz
ENV PATH=$PATH:/usr/local/go/bin:/root/go/bin
ENV GOPATH=/root/go

# ============================================
# Rust + wasm32 target (for CosmWasm / SC-01 tests)
# ============================================
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH=$PATH:/root/.cargo/bin
RUN /root/.cargo/bin/rustup target add wasm32-unknown-unknown

# ============================================
# Python 3 (for VC-01, CA-01 tests)
# ============================================
RUN apt-get update && apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/bin/python

# ============================================
# Node.js 20 LTS (for MCP tools if needed)
# ============================================
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# Verification commands (run at container start)
# ============================================
RUN echo '#!/bin/bash\n\
\n\
echo \"=== Environment Verification ===\"\n\
\n\
if command -v git >/dev/null 2>&1; then\n\
  echo \"Git: $(git --version | head -1)\"\n\
else\n\
  echo \"Git: missing\"\n\
fi\n\
\n\
if command -v go >/dev/null 2>&1; then\n\
  echo \"Go: $(go version)\"\n\
else\n\
  echo \"Go: missing\"\n\
fi\n\
\n\
if command -v rustc >/dev/null 2>&1; then\n\
  echo \"Rust: $(rustc --version)\"\n\
else\n\
  echo \"Rust: missing\"\n\
fi\n\
\n\
if command -v cargo >/dev/null 2>&1; then\n\
  echo \"Cargo: $(cargo --version)\"\n\
else\n\
  echo \"Cargo: missing\"\n\
fi\n\
\n\
if command -v python3 >/dev/null 2>&1; then\n\
  echo \"Python: $(python3 --version)\"\n\
elif command -v python >/dev/null 2>&1; then\n\
  echo \"Python: $(python --version)\"\n\
else\n\
  echo \"Python: missing\"\n\
fi\n\
\n\
if command -v node >/dev/null 2>&1; then\n\
  echo \"Node: $(node --version)\"\n\
else\n\
  echo \"Node: missing\"\n\
fi\n\
\n\
if [ -d /workspaces/regen-ledger/.git ]; then\n\
  echo \"regen-ledger: OK ($(git -C /workspaces/regen-ledger rev-parse --short HEAD 2>/dev/null || echo unknown))\"\n\
else\n\
  echo \"regen-ledger: missing (run: setup-repos)\"\n\
fi\n\
\n\
echo \"================================\"\n\
' > /usr/local/bin/verify-env && chmod +x /usr/local/bin/verify-env

# ============================================
# Repo bootstrap (run at container create)
# ============================================
RUN echo '#!/bin/bash\n\
set -euo pipefail\n\
\n\
LEDGER_DIR=\"/workspaces/regen-ledger\"\n\
\n\
mkdir -p /workspaces\n\
\n\
if [ -d \"${LEDGER_DIR}/.git\" ]; then\n\
  echo \"regen-ledger already present at ${LEDGER_DIR}\"\n\
  exit 0\n\
fi\n\
\n\
echo \"Cloning regen-ledger into ${LEDGER_DIR}...\"\n\
git clone --depth 1 https://github.com/regen-network/regen-ledger.git \"${LEDGER_DIR}\"\n\
' > /usr/local/bin/setup-repos && chmod +x /usr/local/bin/setup-repos

# Default command
CMD ["bash"]
