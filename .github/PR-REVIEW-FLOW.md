# 🔄 Complete PR Review & Merge Flow

## How Your System Works Now

### The Automatic Flow (∞ Loop)

```
1. Issue Created (by Orchestrator or manually)
   ↓
2. Auto-Copilot Assignment
   - Detects labels: workflow-failure, bug, enhancement
   - Adds comment to trigger Copilot
   - Adds labels: copilot-assigned, in-progress
   ↓
3. Human/Copilot Creates PR
   - You create PR manually, OR
   - Copilot suggests fix in issue comments
   ↓
4. Auto-Labeling
   - Workflow detects PR keywords
   - Auto-adds labels: automated-fix, bug-fix, workflow, docs
   ↓
5. Auto-Reviewer Analyzes
   - Checks file types (docs vs code)
   - Counts critical files
   - Measures PR size
   - Calculates safety score
   ↓
6. Auto-Review Decision:
   
   ✅ APPROVE + AUTO-MERGE (30s delay)
   - Documentation only (.md files)
   - Safe files only (no critical files)
   - Small size (< 100 lines)
   
   ✅ APPROVE (manual merge needed)
   - 1-2 critical files
   - Small size
   - OR any PR you want reviewed
   
   💬 COMMENT (needs human review)
   - 3+ critical files
   - Large PR (> 100 lines)
   - Complex changes
```

---

## When PRs Auto-Merge (30 Second Override)

### Tier 1: Instant Auto-Merge ✅

These merge automatically after 30 seconds:

| Condition | Example |
|-----------|---------|
| **Docs only** | README updates, guide changes |
| **Safe files only** | .txt, .md, .yml (non-critical) |
| **Small + safe** | < 100 lines, no code changes |

**Override**: Comment "STOP" or remove `automated-fix` label within 30 seconds

---

## When PRs Need Manual Merge 🖱️

### Tier 2: Approved But Manual ✅ (No Auto-Merge)

Auto-reviewer **approves** but doesn't merge:

| Condition | What To Do |
|-----------|------------|
| **1-2 critical files** | Review changes, then merge manually |
| **Workflow changes** | Check YAML syntax, then merge |
| **Small code changes** | Quick review, then merge |

**How to Merge:**

**Option A: GitHub UI**
1. Go to the PR
2. See ✅ "Auto-Review: APPROVED" comment
3. Click "Merge pull request"
4. Done! ✨

**Option B: Manual Workflow**
1. Go to Actions → "✅ Manual PR Review & Merge"
2. Click "Run workflow"
3. Enter PR number
4. Choose "approve-and-merge"
5. Click "Run workflow"
6. Done! ✨

**Option C: Command Line**
```bash
gh pr review <PR_NUMBER> --approve
gh pr merge <PR_NUMBER> --squash
```

---

## When PRs Need Your Review 👀

### Tier 3: Human Review Required 💬

Auto-reviewer adds **comment** (no approval):

| Condition | What To Do |
|-----------|------------|
| **3+ critical files** | Review all changes carefully |
| **Large PR** | > 100 lines, review thoroughly |
| **Safety-critical** | UV control, emergency stop, GPIO |

**How to Review & Merge:**

1. **Review the PR**
   - Read the Auto-Reviewer's analysis
   - Check which critical files changed
   - Review code changes line-by-line

2. **If Good → Approve**
   ```bash
   gh pr review <PR_NUMBER> --approve --body "Looks good!"
   ```
   
3. **Then Merge**
   - Via GitHub UI: Click "Merge pull request"
   - Via workflow: Use "Manual PR Review & Merge" workflow
   - Via CLI: `gh pr merge <PR_NUMBER> --squash`

4. **If Issues → Request Changes**
   ```bash
   gh pr review <PR_NUMBER> --request-changes --body "Please fix X"
   ```

---

## Quick Reference: PR States

| Auto-Reviewer Verdict | Auto-Merge? | What You Do |
|----------------------|-------------|-------------|
| ✅ APPROVE + auto_merge=true | Yes (30s delay) | Nothing (or cancel within 30s) |
| ✅ APPROVE + auto_merge=false | No | Manually merge when ready |
| 💬 COMMENT | No | Review → Approve → Merge |
| ❌ REQUEST_CHANGES | No | Fix issues → Update PR |

---

## The Manual Merge Workflow

### When to Use It

- PR is approved but you want to merge it yourself
- You want to approve + merge in one click
- You're reviewing multiple PRs in bulk

### How to Use It

1. **Go to Actions tab**
2. **Click "✅ Manual PR Review & Merge"**
3. **Click "Run workflow"**
4. **Fill in:**
   - PR number (e.g., `5`)
   - Action: Choose one
     - `approve-and-merge` - Approve + merge together
     - `approve-only` - Just approve, don't merge
     - `just-merge` - Merge without new approval
     - `request-changes` - Ask for changes
5. **Click "Run workflow"**
6. **Wait 10-20 seconds**
7. **Check PR - it's merged!** ✨

### Benefits

- ✅ One-click merge for multiple PRs
- ✅ Auto-closes related issues
- ✅ Adds proper commit messages
- ✅ Audit trail in Actions

---

## Critical Files That Need Extra Review

These files **always** trigger manual review:

### Safety-Critical
- `docs/SAFETY.md` - Safety documentation
- `software/uv_control/led_controller.py` - UV LED control
- Any file with: `emergency_stop`, `GPIO`, `UV`

### Infrastructure
- `.github/workflows/*` - Workflow files
- `requirements.txt` - Python dependencies
- Any Docker/Kubernetes configs

### Why?

- **Safety**: UV control could harm users
- **Security**: Workflows have repo access
- **Stability**: Dependencies affect entire system

---

## Troubleshooting

### "PR not getting reviewed"

**Check:**
1. Is workflow running? Go to Actions → "🤖 Copilot Auto-Assign & Auto-Review"
2. Did it fail? Check logs for errors
3. Is `auto_reviewer.py` installed correctly?

**Fix:**
```bash
# Test the reviewer locally
python .github/scripts/auto_reviewer.py --repo grloper/gel-nails-machine --pr-number <PR#>
```

### "Auto-merge isn't happening"

**Reasons:**
1. PR has critical files → Manual merge needed
2. PR is too large (> 100 lines) → Manual review
3. 30-second window passed → Re-run workflow
4. Merge conflict → Resolve conflicts first

**Force Auto-Merge:**
1. Add label `automated-fix` to PR
2. Make PR small (< 100 lines)
3. Remove critical files from PR
4. Or use "Manual PR Review & Merge" workflow

### "Want to disable auto-merge completely"

Edit `.github/scripts/auto_reviewer.py`:

```python
# Line ~120, change:
self.auto_merge = True

# To:
self.auto_merge = False  # Always manual merge
```

### "Want more aggressive auto-merge"

Edit `.github/scripts/auto_reviewer.py`:

```python
# Line ~106, change:
is_small = total_changes < 100

# To:
is_small = total_changes < 500  # Allow larger PRs
```

---

## Best Practices

### For You

✅ **Let auto-reviewer work** - It's fast and accurate  
✅ **Review critical files manually** - Safety first  
✅ **Use manual workflow for batch merges** - Efficient  
✅ **Check auto-reviewer comments** - Good insights  

❌ **Don't bypass auto-reviewer** - It catches issues  
❌ **Don't ignore critical file warnings** - Safety risk  
❌ **Don't merge without reading summary** - Know what changed  

### For PRs

✅ **Keep PRs small** (< 100 lines) - Faster review  
✅ **Add labels** (automated-fix, bug-fix) - Better routing  
✅ **Reference issues** (#123) - Auto-closes them  
✅ **Write clear titles** - Helps auto-labeling  

❌ **Don't mix docs + code** - Split into 2 PRs  
❌ **Don't include critical + non-critical** - Separate them  
❌ **Don't create huge PRs** (> 500 lines) - Hard to review  

---

## Command Cheat Sheet

```bash
# View all PRs
gh pr list

# View specific PR
gh pr view <PR_NUMBER>

# Approve a PR
gh pr review <PR_NUMBER> --approve

# Merge a PR
gh pr merge <PR_NUMBER> --squash

# Approve + Merge in one command
gh pr review <PR_NUMBER> --approve && gh pr merge <PR_NUMBER> --squash

# Close without merging
gh pr close <PR_NUMBER>

# Reopen a PR
gh pr reopen <PR_NUMBER>

# Check workflow status
gh run list --workflow=copilot-automation.yml --limit 5

# Trigger manual merge workflow
gh workflow run manual-pr-review.yml -f pr_number=5 -f action=approve-and-merge
```

---

## Summary: Your Three Options

### 1. **Fully Automatic** (Default)
- Small, safe PRs merge themselves in 30 seconds
- You do nothing
- Best for: Docs, configs, minor fixes

### 2. **Semi-Automatic** (Common)
- Auto-reviewer approves
- You click "Merge" button (or use workflow)
- Best for: Most code changes

### 3. **Manual** (Safety-Critical)
- You review everything
- You approve + merge
- Best for: Critical files, large changes

**Most PRs will be Semi-Automatic** - Auto-reviewer approves, you just click merge. Fast and safe! ✨

---

## Need Help?

1. Check auto-reviewer's comment on your PR
2. Review `.github/CIRCULAR-ECOSYSTEM.md` for architecture
3. Check workflow logs in Actions tab
4. Adjust thresholds in `auto_reviewer.py` if needed

**The system is designed to be helpful, not blocking. When in doubt, it asks for your review.** 👍
