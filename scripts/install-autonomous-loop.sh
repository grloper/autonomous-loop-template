#!/bin/bash
# 🔄 Autonomous Development Loop - One-Line Installer
# Usage: curl -sL <url> | bash

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 AUTONOMOUS DEVELOPMENT LOOP INSTALLER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install git first."
    exit 1
fi

if ! command -v gh &> /dev/null; then
    echo "⚠️  GitHub CLI (gh) not found. Installing is recommended for full features."
    echo "   Install from: https://cli.github.com/"
fi

# Check if we're in a git repo
if [ ! -d .git ]; then
    echo "❌ Not a git repository. Please run from your project root."
    exit 1
fi

echo "✅ Prerequisites check passed"
echo ""

# Download template files
echo "📥 Downloading automation files..."

REPO_URL="https://github.com/grloper/autonomous-loop-template"
TEMP_DIR=$(mktemp -d)

# Clone just the .github directory
git clone --depth 1 --filter=blob:none --sparse "$REPO_URL" "$TEMP_DIR"
cd "$TEMP_DIR"
git sparse-checkout set .github

echo "✅ Files downloaded"
echo ""

# Copy to project
echo "📂 Installing automation files..."

cd - > /dev/null

# Create .github if it doesn't exist
mkdir -p .github/{workflows,scripts}

# Copy workflows
cp "$TEMP_DIR/.github/workflows/orchestrator.yml" .github/workflows/
cp "$TEMP_DIR/.github/workflows/copilot-automation.yml" .github/workflows/
cp "$TEMP_DIR/.github/workflows/workflow-doctor.yml" .github/workflows/
cp "$TEMP_DIR/.github/workflows/manual-pr-review.yml" .github/workflows/

# Copy scripts
cp "$TEMP_DIR/.github/scripts/orchestrator.py" .github/scripts/
cp "$TEMP_DIR/.github/scripts/auto_reviewer.py" .github/scripts/
cp "$TEMP_DIR/.github/scripts/workflow_doctor.py" .github/scripts/

# Copy documentation
cp "$TEMP_DIR/.github/PR-REVIEW-FLOW.md" .github/ 2>/dev/null || true

# Create copilot-instructions.md if it doesn't exist
if [ ! -f .github/copilot-instructions.md ]; then
    echo "📝 Creating template copilot-instructions.md..."
    cat > .github/copilot-instructions.md << 'EOF'
# Copilot Instructions - YOUR_PROJECT_NAME

## Project Overview
[Describe what your project does - e.g., "A web app for managing X"]

## Tech Stack
- **Language:** [e.g., Python 3.11, TypeScript, etc.]
- **Framework:** [e.g., Next.js, Django, React Native]
- **Database:** [e.g., PostgreSQL, MongoDB, etc.]
- **Infrastructure:** [e.g., AWS, Docker, Kubernetes]

## Architecture Patterns
1. [Pattern 1 - e.g., "Use dependency injection"]
2. [Pattern 2 - e.g., "Prefer composition over inheritance"]
3. [Pattern 3 - e.g., "Keep components under 200 lines"]

## Critical Files (Never auto-merge)
- `path/to/auth/*` - Authentication logic
- `path/to/payments/*` - Payment processing
- `.github/workflows/*` - CI/CD pipelines

## Testing Requirements
- Unit tests for all business logic
- Integration tests for APIs
- E2E tests for critical user flows
- Minimum 80% code coverage

## Safety Rules
❌ Never commit secrets or API keys
❌ Never disable security features
❌ Never bypass authentication
❌ Never use eval() or similar dangerous functions

## Development Workflow
1. All changes go through PRs
2. PRs must pass CI checks
3. PRs require at least 1 approval (or auto-approval for safe changes)
4. Use conventional commits (feat:, fix:, docs:, etc.)

---
**This file helps the Autonomous Loop understand your project.**
**Customize it for better AI-generated code!**
EOF
    echo "✅ Created .github/copilot-instructions.md (PLEASE CUSTOMIZE THIS!)"
fi

# Check/create requirements.txt for Python deps
if [ ! -f requirements.txt ]; then
    echo "📦 Creating requirements.txt..."
    cat > requirements.txt << 'EOF'
# Autonomous Loop dependencies
PyGithub>=2.1.1
requests>=2.31.0
pyyaml>=6.0

# Add your project dependencies below
EOF
    echo "✅ Created requirements.txt"
fi

# Cleanup
rm -rf "$TEMP_DIR"

echo "✅ Installation complete"
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 INSTALLED FILES:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  .github/"
echo "  ├── workflows/"
echo "  │   ├── orchestrator.yml          ← 🎯 The brain"
echo "  │   ├── copilot-automation.yml    ← 🤖 Auto-assign"
echo "  │   ├── workflow-doctor.yml       ← 🏥 Self-heal"
echo "  │   └── manual-pr-review.yml      ← ⚙️  Manual control"
echo "  ├── scripts/"
echo "  │   ├── orchestrator.py           ← Analysis engine"
echo "  │   ├── auto_reviewer.py          ← PR validator"
echo "  │   └── workflow_doctor.py        ← Diagnostics"
echo "  └── copilot-instructions.md       ← ⚠️  CUSTOMIZE THIS!"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚙️  NEXT STEPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. 📝 CUSTOMIZE YOUR PROJECT CONTEXT:"
echo "   nano .github/copilot-instructions.md"
echo ""
echo "2. 🔧 OPTIONAL: Adjust critical files and thresholds:"
echo "   nano .github/scripts/auto_reviewer.py"
echo ""
echo "3. 💾 COMMIT THE AUTOMATION:"
echo "   git add .github/"
echo "   git commit -m 'feat: Add autonomous development loop 🔄'"
echo "   git push"
echo ""
echo "4. 🚀 TRIGGER FIRST RUN:"
echo "   gh workflow run orchestrator.yml"
echo "   # Or wait for Monday 8am UTC (automatic)"
echo ""
echo "5. 📊 MONITOR PROGRESS:"
echo "   gh run list --workflow=orchestrator.yml"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 DOCUMENTATION:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Template Repo:    https://github.com/grloper/autonomous-loop-template"
echo "  Full Setup Guide: https://github.com/grloper/autonomous-loop-template/blob/main/AUTONOMOUS-LOOP-SETUP.md"
echo "  PR Review Flow:   .github/PR-REVIEW-FLOW.md"
echo "  Quick Start:      https://github.com/grloper/autonomous-loop-template/blob/main/QUICKSTART.md"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Your repository is now AUTONOMOUS! ✨"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "The system will:"
echo "  ✅ Automatically find work to do"
echo "  ✅ Create prioritized issues"
echo "  ✅ Assign AI agents to implement"
echo "  ✅ Review and merge safe code"
echo "  ✅ Heal itself when things break"
echo "  ✅ Run forever without you"
echo ""
echo "🎮 Trigger it now: gh workflow run orchestrator.yml"
echo ""
