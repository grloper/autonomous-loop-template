#!/bin/bash
# Verification script - Run after installation to check setup

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 AUTONOMOUS LOOP - SETUP VERIFICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ERRORS=0
WARNINGS=0

# Check if in git repo
if [ ! -d .git ]; then
    echo "❌ ERROR: Not a git repository"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ Git repository detected"
fi

# Check GitHub CLI
if ! command -v gh &> /dev/null; then
    echo "⚠️  WARNING: GitHub CLI (gh) not installed"
    echo "   Install from: https://cli.github.com/"
    WARNINGS=$((WARNINGS + 1))
else
    echo "✅ GitHub CLI installed"
fi

# Check workflow files
echo ""
echo "📂 Checking workflow files..."

WORKFLOWS=(
    ".github/workflows/orchestrator.yml"
    ".github/workflows/copilot-automation.yml"
    ".github/workflows/workflow-doctor.yml"
    ".github/workflows/manual-pr-review.yml"
)

for workflow in "${WORKFLOWS[@]}"; do
    if [ -f "$workflow" ]; then
        echo "  ✅ $workflow"
    else
        echo "  ❌ $workflow - MISSING"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check script files
echo ""
echo "🐍 Checking Python scripts..."

SCRIPTS=(
    ".github/scripts/orchestrator.py"
    ".github/scripts/auto_reviewer.py"
    ".github/scripts/workflow_doctor.py"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        echo "  ✅ $script"
    else
        echo "  ❌ $script - MISSING"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check copilot-instructions.md
echo ""
echo "📖 Checking configuration..."

if [ -f ".github/copilot-instructions.md" ]; then
    # Check if it's still the template
    if grep -q "\[YOUR_PROJECT_NAME\]" .github/copilot-instructions.md; then
        echo "  ⚠️  .github/copilot-instructions.md - NEEDS CUSTOMIZATION"
        echo "     Edit this file to describe your project for AI"
        WARNINGS=$((WARNINGS + 1))
    else
        echo "  ✅ .github/copilot-instructions.md (customized)"
    fi
else
    echo "  ❌ .github/copilot-instructions.md - MISSING"
    ERRORS=$((ERRORS + 1))
fi

# Check requirements.txt
if [ -f "requirements.txt" ]; then
    # Check if PyGithub is there
    if grep -q "PyGithub" requirements.txt; then
        echo "  ✅ requirements.txt (has PyGithub)"
    else
        echo "  ⚠️  requirements.txt missing PyGithub dependency"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo "  ⚠️  requirements.txt not found"
    echo "     Workflows will create it automatically, but recommended to have"
    WARNINGS=$((WARNINGS + 1))
fi

# Check if files are committed
echo ""
echo "💾 Checking git status..."

if [ -n "$(git status --porcelain .github/)" ]; then
    echo "  ⚠️  .github/ directory has uncommitted changes"
    echo "     Run: git add .github/ && git commit -m 'feat: Add autonomous loop'"
    WARNINGS=$((WARNINGS + 1))
else
    echo "  ✅ All workflow files committed"
fi

# Check GitHub repo
echo ""
echo "🔗 Checking GitHub integration..."

if command -v gh &> /dev/null; then
    REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)
    if [ -n "$REPO" ]; then
        echo "  ✅ Connected to: $REPO"
        
        # Check if GitHub Actions is enabled
        echo ""
        echo "  Testing GitHub Actions access..."
        if gh workflow list &> /dev/null; then
            WORKFLOW_COUNT=$(gh workflow list 2>/dev/null | wc -l)
            if [ "$WORKFLOW_COUNT" -gt 0 ]; then
                echo "  ✅ GitHub Actions enabled ($WORKFLOW_COUNT workflows detected)"
            else
                echo "  ⚠️  No workflows detected yet"
                echo "     Push your changes and wait 30 seconds"
                WARNINGS=$((WARNINGS + 1))
            fi
        else
            echo "  ⚠️  Cannot access GitHub Actions"
            echo "     May need to push changes first"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        echo "  ❌ Not connected to GitHub repository"
        echo "     Run: gh auth login"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 VERIFICATION SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "🎉 PERFECT! Everything is set up correctly!"
    echo ""
    echo "Next steps:"
    echo "  1. Customize .github/copilot-instructions.md"
    echo "  2. Trigger orchestrator: gh workflow run orchestrator.yml"
    echo "  3. Check back in 5 minutes for your first AI-generated PR!"
    echo ""
elif [ $ERRORS -eq 0 ]; then
    echo "✅ Setup is complete with $WARNINGS warning(s)"
    echo ""
    echo "You can proceed, but consider fixing the warnings above."
    echo ""
    echo "Trigger orchestrator: gh workflow run orchestrator.yml"
    echo ""
else
    echo "❌ Setup has $ERRORS error(s) and $WARNINGS warning(s)"
    echo ""
    echo "Please fix the errors above before proceeding."
    echo ""
    if [ $ERRORS -gt 0 ]; then
        echo "To reinstall, run:"
        echo "  curl -sL https://raw.githubusercontent.com/grloper/autonomous-loop-template/main/scripts/install-autonomous-loop.sh | bash"
    fi
    echo ""
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
