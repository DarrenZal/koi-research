# Regen Full-Stack Test Environment
# Used for automated testing of code generation capabilities with KOI MCP
#
# Includes: Go, Rust, Python, Node.js, regen-ledger clone
# Designed for Claude Code CLI automated test runs

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
# Python 3.11 (for VC-01, CA-01 tests)
# ============================================
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.11 /usr/bin/python

# ============================================
# Node.js 20 LTS (for MCP tools if needed)
# ============================================
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# Clone regen-ledger (for NU-01 tests)
# ============================================
RUN git clone --depth 1 https://github.com/regen-network/regen-ledger.git /workspaces/regen-ledger

# ============================================
# Create workspace and scratch directories
# ============================================
WORKDIR /workspaces/koi-research
RUN mkdir -p /workspaces/koi-research/scratch

# ============================================
# Verification commands (run at container start)
# ============================================
RUN echo '#!/bin/bash\n\
echo "=== Environment Verification ==="\n\
echo "Go: $(go version)"\n\
echo "Rust: $(rustc --version)"\n\
echo "Cargo: $(cargo --version)"\n\
echo "Python: $(python --version)"\n\
echo "Node: $(node --version)"\n\
echo "regen-ledger: $(ls /workspaces/regen-ledger 2>/dev/null && echo "OK" || echo "MISSING")"\n\
echo "================================"\n\
' > /usr/local/bin/verify-env && chmod +x /usr/local/bin/verify-env

# Default command
CMD ["bash"]
