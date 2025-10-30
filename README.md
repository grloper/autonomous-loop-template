# 🔄 Autonomous Development Loop

> **Make any GitHub repository self-managing in 5 minutes**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/grloper/autonomous-loop-template?style=social)](https://github.com/grloper/autonomous-loop-template)
[![Install](https://img.shields.io/badge/install-one--line-brightgreen)](https://github.com/grloper/autonomous-loop-template#-one-line-install)

**Your repository that:**
- ✅ Finds work automatically (TODOs, bugs, missing tests)
- ✅ Creates prioritized GitHub issues
- ✅ Assigns AI agents to implement fixes
- ✅ Reviews and merges safe code
- ✅ Heals itself when workflows break
- ✅ Runs forever without human intervention

**Result:** Save 6+ hours/week per developer. Your repo evolves while you sleep. 😴

---

## 🎬 See It In Action

**Live Example:** [gel-nails-machine](https://github.com/grloper/gel-nails-machine)
- [Orchestrator Runs](https://github.com/grloper/gel-nails-machine/actions/workflows/orchestrator.yml)
- [Auto-Created Issues](https://github.com/grloper/gel-nails-machine/issues?q=is%3Aissue+author%3Agithub-actions)
- [AI-Generated PRs](https://github.com/grloper/gel-nails-machine/pulls?q=is%3Apr+author%3Acopilot-swe-agent)
- [Self-Healing in Action](https://github.com/grloper/gel-nails-machine/issues?q=label%3Aworkflow-failure)

---

## ⚡ One-Line Install

```bash
curl -sL https://raw.githubusercontent.com/grloper/autonomous-loop-template/main/scripts/install-autonomous-loop.sh | bash
```

That's it! Your repo is now autonomous. 🎉

---

## 🎯 What Gets Installed

```
your-project/
├── .github/
│   ├── workflows/
│   │   ├── orchestrator.yml          # 🎯 The brain - analyzes & prioritizes
│   │   ├── copilot-automation.yml    # 🤖 Auto-assigns AI agents
│   │   ├── workflow-doctor.yml       # 🏥 Self-heals failures
│   │   └── manual-pr-review.yml      # ⚙️  Manual controls (backup)
│   │
│   ├── scripts/
│   │   ├── orchestrator.py           # Analysis engine (274 lines)
│   │   ├── auto_reviewer.py          # PR safety validator (200+ lines)
│   │   └── workflow_doctor.py        # Diagnostics engine (150+ lines)
│   │
│   └── copilot-instructions.md       # 📖 AI context (customize this!)
│
└── requirements.txt                   # Python dependencies
```

**Total:** ~700 lines of battle-tested automation code

---

## 🚀 Quick Start (3 Steps)

### 1️⃣ Install

```bash
# From your project root
curl -sL https://raw.githubusercontent.com/grloper/autonomous-loop-template/main/scripts/install-autonomous-loop.sh | bash
```

### 2️⃣ Customize

```bash
# Edit project context for AI
nano .github/copilot-instructions.md

# Define critical files (won't auto-merge)
nano .github/scripts/auto_reviewer.py
```

### 3️⃣ Activate

```bash
# Commit the automation
git add .github/
git commit -m "feat: Add autonomous development loop 🔄"
git push

# Trigger first run
gh workflow run orchestrator.yml
```

**Done!** Your repo now manages itself. Check back in 30 minutes. 🎉

---

## 🔄 How It Works

```
┌──────────────┐
│ Orchestrator │ ← Runs weekly (or on-demand via "THE BUTTON")
│  (Analyzer)  │   Scans: TODOs, FIXMEs, missing tests, security
└──────┬───────┘
       ↓
┌──────────────┐
│ Prioritizer  │   Scores by: Impact × Urgency ÷ Risk
└──────┬───────┘
       ↓
┌──────────────┐
│Issue Creator │   Creates GitHub issues with:
│              │   • Detailed requirements
└──────┬───────┘   • Success criteria
       ↓            • Priority labels
┌──────────────┐
│Auto-Assigner │   Tags @copilot immediately
└──────┬───────┘
       ↓
┌──────────────┐
│Coding Agent  │   Analyzes + implements + creates PR
└──────┬───────┘   [WIP] Draft with checklist
       ↓
┌──────────────┐
│Auto-Reviewer │   6-tier safety decision:
│  (Validator) │   • Docs → AUTO-MERGE (30s delay)
└──────┬───────┘   • Code → APPROVE (you merge)
       ↓            • Risky → COMMENT (full review)
┌──────────────┐
│  Integrator  │   Merges + closes issues
└──────┬───────┘
       │
       └─────────┐
                 ↓
       ┌─────────────────┐
       │Workflow Doctor  │ ← Self-heals failures
       │ (Self-Healer)   │   Creates diagnostic issues
       └─────────┬───────┘   Triggers fix loop
                 │
                 └──────→ Back to Orchestrator
                          ♻️  INFINITE LOOP
```

---

## 🎛️ Automation Levels

Choose how much control you want to keep:

| Level | Auto-Merge | Auto-Approve | Who Merges | Best For |
|-------|:----------:|:------------:|------------|----------|
| **Observer** | ❌ | ❌ | You | Learning, high-risk projects |
| **Assistant** | Docs only | ✅ | You (1-click) | **Most teams** ⭐ |
| **Autonomous** | ✅ | ✅ | System | Mature teams, high trust |

Configure in `.github/workflows/copilot-automation.yml`

---

## 📊 ROI Calculator

**Time Investment:**
- Initial setup: 30 min
- Customization: 1-2 hrs
- Learning: 2-3 hrs
- **Total:** ~4 hours

**Time Saved (per week):**
- Issue triage: 2 hrs → 0 hrs
- Code review: 3 hrs → 30 min
- Bug hunting: 1 hr → 20 min
- Workflow debugging: 1 hr → 0 hrs
- **Total:** ~6.5 hrs/week

**Payback:** <1 week

**Yearly benefit:** 6.5 hrs/wk × 50 wks = **325 hours** (~$32,500 at $100/hr)

---

## 🔧 Use Cases

### 🌐 Web App (Next.js, React, Vue)
```bash
# Scans for:
- Unprotected API routes
- Missing input validation  
- Hardcoded secrets
- Unused dependencies
- Missing tests

# Auto-fixes:
- Adds Zod validation
- Implements rate limiting
- Extracts to env vars
- Removes dead code
- Creates test suites
```

### 🐍 Python (Django, FastAPI, Data Science)
```bash
# Scans for:
- SQL injection risks
- Missing type hints
- No error handling
- Brittle transforms
- Poor test coverage

# Auto-fixes:
- Parameterizes queries
- Adds type annotations
- Implements try/except
- Adds data validation
- Creates pytest suites
```

### 📱 Mobile (React Native, Flutter)
```bash
# Scans for:
- Unoptimized images
- Missing offline mode
- Memory leaks
- Accessibility gaps
- Hardcoded strings

# Auto-fixes:
- Compresses assets
- Adds caching layer
- Implements cleanup
- Adds a11y labels
- Extracts to i18n
```

---

## 🎓 Real-World Examples

**Before Autonomous Loop:**
- 😫 "What should I work on next?" → 30 min deciding
- 📝 Manual issue creation → 10 min/issue
- 👀 PR review process → 2-4 hours
- 🐛 Workflow failures → 1 hour debugging
- **Total:** 8-10 hrs/week overhead

**After Autonomous Loop:**
- ✅ Work prioritized automatically → 0 min
- ✅ Issues created while you sleep → 0 min
- ✅ Safe PRs auto-merge → 0 min
- ✅ Workflows self-heal → 0 min
- 👤 You only review critical changes → 30 min
- **Total:** 30 min/week → **7.5 hrs saved!**

---

## 🛠️ Customization Guide

### Define Your Critical Files

Edit `.github/scripts/auto_reviewer.py`:

```python
CRITICAL_FILES = {
    # Your authentication code
    'src/auth/': ['authentication logic'],
    
    # Payment processing
    'src/api/payments/': ['payment flow'],
    
    # Infrastructure
    'terraform/': ['infrastructure as code'],
    '.github/workflows/': ['CI/CD pipelines'],
    
    # Add yours...
}
```

### Adjust Scan Patterns

Edit `.github/scripts/orchestrator.py`:

```python
PRIORITY_PATTERNS = {
    'security': [
        r'TODO.*security',
        r'FIXME.*auth',
        r'XXX.*password',
    ],
    'your_domain': [
        r'TODO.*your_keyword',
        # Add your patterns
    ],
}
```

### Set Thresholds

```python
# auto_reviewer.py
SAFETY_THRESHOLDS = {
    'max_files_for_auto_merge': 3,    # Adjust for your team
    'max_lines_changed': 100,          # More conservative = lower
}
```

---

## 📚 Documentation

- **[Complete Setup Guide](./AUTONOMOUS-LOOP-SETUP.md)** - 500+ lines, every detail
- **[Quick Reference](./QUICKSTART.md)** - Cheat sheet, common commands
- **[PR Review Flow](./.github/PR-REVIEW-FLOW.md)** - How auto-merge works

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| **"Workflow not found"** | Wait 30 seconds after pushing `.github/workflows/`, then try again |
| **Orchestrator doesn't create issues** | 1. Check if there are TODOs in code<br>2. Lower `MIN_PRIORITY_SCORE` in `orchestrator.py`<br>3. Run manually: `gh workflow run orchestrator.yml` |
| **"PyGithub not found" error** | Workflows auto-install deps. If failing, check `requirements.txt` is present |
| **Copilot doesn't create PRs** | 1. Verify GitHub Copilot access enabled<br>2. Check `@copilot` mention in issue comments<br>3. Ensure issue has proper labels |
| **PRs not auto-merging** | 1. Check `CRITICAL_FILES` in `auto_reviewer.py`<br>2. Reduce `max_files_for_auto_merge` threshold<br>3. Verify PR passes all checks |
| **Too many issues created** | 1. Use `focus_area` parameter when triggering<br>2. Raise `MIN_PRIORITY_SCORE` in orchestrator<br>3. Clean up TODOs/FIXMEs in code |
| **"Permission denied" errors** | Verify repository has correct permissions in Settings → Actions → General → Workflow permissions (Read & Write) |
| **Workflows show "action_required"** | Normal for draft PRs. Mark PR as "Ready for review" to trigger auto-review |
| **Installer script fails** | 1. Check `git` and `gh` CLI installed<br>2. Ensure you're in git repository root<br>3. Run with `bash` not `sh` |

### 🔍 **Common First-Time Issues**

**"Nothing happens after install"**
- Workflows don't run automatically until you trigger them or wait for schedule
- Trigger manually: `gh workflow run orchestrator.yml`

**"Auto-review approves everything"**
- Update `CRITICAL_FILES` in `.github/scripts/auto_reviewer.py`
- Add your security-critical paths

**"System creates issues but no PRs"**
- Check GitHub Copilot is enabled for your organization
- Verify `@copilot` has access to your repository
- Issues need time (~2-5 minutes) for Copilot to respond

[Full troubleshooting guide →](./AUTONOMOUS-LOOP-SETUP.md#-troubleshooting)

---

## 🤝 Contributing

Contributions welcome! This template improves as more teams use it.

**Ways to contribute:**
- 🐛 Report bugs or edge cases
- 💡 Suggest new scan patterns
- 📖 Improve documentation
- 🎨 Add examples for new frameworks
- ⭐ Star the repo to help others find it

---

## 📜 License

MIT License - Use freely in any project (personal or commercial)

---

## 🌟 Success Stories

> "Reduced code review backlog from 40 PRs to 5 PRs in 2 weeks. The system handles all the boring stuff."  
> — *Developer at Series A startup*

> "Our test coverage went from 45% to 78% automatically. The orchestrator found gaps we didn't even know existed."  
> — *Engineering Lead at healthcare company*

> "Best part: I came back from vacation and the repo had fixed itself. 6 issues resolved, 0 fires to put out."  
> — *Solo founder*

---

## 🚀 Get Started

```bash
# 1. Install (5 seconds)
curl -sL https://raw.githubusercontent.com/grloper/autonomous-loop-template/main/scripts/install-autonomous-loop.sh | bash

# 2. Customize (5 minutes)
nano .github/copilot-instructions.md

# 3. Activate (10 seconds)
git add .github/ && git commit -m "feat: Add autonomous loop 🔄" && git push

# 4. Trigger (5 seconds)
gh workflow run orchestrator.yml

# 5. Check back in 30 minutes
gh pr list  # PRs auto-created and reviewed!
```

**Your repo is now self-managing.** Go grab a coffee. ☕

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/grloper/autonomous-loop-template/issues)
- **Discussions:** [GitHub Discussions](https://github.com/grloper/autonomous-loop-template/discussions)
- **Example:** [Live Implementation](https://github.com/grloper/gel-nails-machine)

---

<div align="center">

**Made with ❤️ by developers who hate boring work**

[⭐ Star this repo](https://github.com/grloper/autonomous-loop-template) · [🐛 Report Bug](https://github.com/grloper/autonomous-loop-template/issues) · [💡 Request Feature](https://github.com/grloper/autonomous-loop-template/issues)

</div>
