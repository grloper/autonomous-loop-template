# 🚀 Autonomous Loop - Quick Reference

## ⚡ One-Line Commands

```bash
# Install in any repo
curl -sL https://raw.githubusercontent.com/grloper/gel-nails-machine/main/scripts/install-autonomous-loop.sh | bash

# Trigger orchestrator
gh workflow run orchestrator.yml

# Check status
gh run list --workflow=orchestrator.yml --limit 5

# View latest report
gh run view $(gh run list --workflow=orchestrator.yml --json databaseId --jq '.[0].databaseId' --limit 1)

# List AI-assigned issues
gh issue list --label "copilot-assigned"

# Manual PR merge
gh workflow run manual-pr-review.yml -f pr_number=42 -f action=approve-and-merge
```

---

## 🎯 The Flow (What Happens)

```
YOU              SYSTEM                       RESULT
─────────────────────────────────────────────────────────────
                                              
Press            Orchestrator runs      →     3-5 issues created
"THE BUTTON"     (20 seconds)                 with priorities
                                              
                 ↓                             
                                              
                 Copilot auto-assigned  →     @copilot tagged
                 (immediate)                   on each issue
                                              
                 ↓                             
                                              
                 Coding agent starts    →     [WIP] PR created
                 (2-5 minutes)                 with implementation plan
                                              
                 ↓                             
                                              
                 Code implemented       →     PR updated
                 (10-30 minutes)               status: Ready for review
                                              
                 ↓                             
                                              
                 Auto-reviewer checks   →     Decision:
                 (5 seconds)                   • Safe → AUTO-MERGE (30s)
                                              • Code → APPROVE (you merge)
                                              • Risky → COMMENT (you review)
                                              
                 ↓                             
                                              
You click        PR merged             →     Issue auto-closed
"Merge"          (if needed)                   ✅ Task complete
(optional)                                    
                                              
                 ↓                             
                                              
                 Loop restarts         →     Finds next work
                 (Monday 8am or manual)        ♻️  Forever
```

---

## 📁 File Structure

```
.github/
├── workflows/                          # GitHub Actions
│   ├── orchestrator.yml               # 🎯 Brain (main loop)
│   ├── copilot-automation.yml         # 🤖 Auto-assign + review
│   ├── workflow-doctor.yml            # 🏥 Self-healing
│   └── manual-pr-review.yml           # ⚙️  Manual controls
│
├── scripts/                            # Python automation
│   ├── orchestrator.py                # Analysis engine
│   ├── auto_reviewer.py               # PR safety validator
│   └── workflow_doctor.py             # Failure diagnostics
│
├── copilot-instructions.md            # ⚠️  CUSTOMIZE THIS!
└── PR-REVIEW-FLOW.md                  # Documentation
```

---

## ⚙️ Key Files to Customize

### 1. **`.github/copilot-instructions.md`** ← START HERE
Your project context for AI. Defines:
- Tech stack
- Architecture patterns
- Critical files
- Safety rules

### 2. **`orchestrator.py` (lines 45-70)**
What to scan for:
```python
PRIORITY_PATTERNS = {
    'security': [r'TODO.*security', ...],
    'performance': [r'TODO.*optimize', ...],
    # Add your patterns
}
```

### 3. **`auto_reviewer.py` (lines 20-50)**
Critical files that need human review:
```python
CRITICAL_FILES = {
    'src/auth/': ['authentication'],
    'src/payments/': ['payment processing'],
    # Add your paths
}
```

---

## 🎛️ Automation Levels

| Level | Auto-Merge | Auto-Approve | Use Case |
|-------|------------|--------------|----------|
| **Observer** | ❌ | ❌ | Just learning, want full control |
| **Assistant** | Docs only | ✅ | Most teams (recommended) |
| **Autonomous** | ✅ | ✅ | Mature teams, high confidence |

Configure in `.github/workflows/copilot-automation.yml`

---

## 🔧 Common Customizations

### Add New Scan Pattern
```python
# orchestrator.py
PRIORITY_PATTERNS['api'] = [
    r'TODO.*endpoint',
    r'FIXME.*API',
    r'# Missing rate limit',
]
```

### Change Auto-Merge Threshold
```python
# auto_reviewer.py
SAFETY_THRESHOLDS = {
    'max_files_for_auto_merge': 5,    # Default: 3
    'max_lines_changed': 150,          # Default: 100
}
```

### Add Custom Priority Logic
```python
# orchestrator.py - calculate_priority()
if 'payment' in task['category']:
    return {'urgency': 10, 'impact': 10, 'risk': 9}
```

### Exclude Directories from Scanning
```python
# orchestrator.py
EXCLUDE_DIRS = [
    'node_modules/',
    'venv/',
    'dist/',
    'build/',
    '__pycache__/',
    # Add yours
]
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| **Orchestrator doesn't create issues** | Lower `MIN_PRIORITY_SCORE` in orchestrator.py |
| **Copilot doesn't create PRs** | Check `@copilot` mention in issue, verify Copilot access |
| **PRs not auto-merging** | Check if file is in CRITICAL_FILES, or reduce thresholds |
| **Too many issues created** | Raise `MIN_PRIORITY_SCORE` or adjust PRIORITY_PATTERNS |
| **Workflow Doctor spamming** | Fix root cause workflow failure, or disable self-healing temporarily |

---

## 📊 Metrics to Track

```bash
# Weekly summary
gh run list --workflow=orchestrator.yml --limit 4  # Last month of runs

# Issues resolved
gh issue list --state closed --label "copilot-assigned" --json closedAt,title

# PR stats
gh pr list --state merged --label "automated-fix" --json mergedAt,additions,deletions

# Automation rate
echo "Auto-merged: $(gh pr list --search 'Auto-merged' --state merged | wc -l)"
echo "Total PRs: $(gh pr list --state merged | wc -l)"
```

---

## 🎮 Pro Tips

1. **Start Conservative**: Use Observer mode first week, increase gradually
2. **Customize copilot-instructions.md**: Better context = better PRs
3. **Review Auto-Reviewer Decisions**: Check why PRs were/weren't auto-merged
4. **Use Labels**: Add custom labels to issues for better organization
5. **Monitor Trends**: Track which types of tasks the system finds most
6. **Iterate on Patterns**: Refine PRIORITY_PATTERNS based on what's useful
7. **Set Critical Files Correctly**: Balance safety vs automation

---

## 🔗 Resources

- **Full Guide**: [AUTONOMOUS-LOOP-SETUP.md](./AUTONOMOUS-LOOP-SETUP.md)
- **PR Flow**: [PR-REVIEW-FLOW.md](./.github/PR-REVIEW-FLOW.md)
- **Example Repo**: [gel-nails-machine](https://github.com/grloper/gel-nails-machine)
- **Issues/Support**: [GitHub Issues](https://github.com/grloper/gel-nails-machine/issues)

---

## 💡 Quick Wins (First Week)

1. ✅ Install system
2. ✅ Customize copilot-instructions.md
3. ✅ Run orchestrator once manually
4. ✅ Review 1-2 PRs to understand flow
5. ✅ Adjust one threshold based on results
6. ✅ Let it run automatically for a week
7. ✅ Measure time saved vs week before

**Goal**: Save 5+ hours/week within 2 weeks

---

**Your repo is now self-managing! 🚀**

Next: `gh workflow run orchestrator.yml`
