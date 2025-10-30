# 🔄 Autonomous Development Loop - Setup Guide

## 🎯 What is This?

A **self-managing development system** that:
- ✅ Automatically finds work that needs doing
- ✅ Creates issues with priorities
- ✅ Assigns AI agents to implement
- ✅ Reviews and merges safe code
- ✅ Heals itself when things break
- ✅ Runs forever without human intervention

**Think of it as:** DevOps + AI + Continuous Everything = Your repo manages itself

---

## 🚀 Quick Start (5 Minutes)

### **Option 1: One-Line Install**

```bash
# From your project root
curl -sL https://raw.githubusercontent.com/grloper/gel-nails-machine/main/scripts/install-autonomous-loop.sh | bash
```

This will:
1. Copy all automation files to `.github/`
2. Create a template `copilot-instructions.md`
3. Run initial orchestrator analysis
4. Display setup status

### **Option 2: Manual Installation**

```bash
# 1. Clone the template files
git clone https://github.com/grloper/autonomous-loop-template.git temp-loop
cp -r temp-loop/.github .
rm -rf temp-loop

# 2. Configure for your project
nano .github/copilot-instructions.md  # Add your project context
nano .github/scripts/orchestrator.py  # Customize patterns (optional)
nano .github/scripts/auto_reviewer.py  # Set critical files (optional)

# 3. Commit and activate
git add .github/
git commit -m "feat: Add autonomous development loop 🔄"
git push

# 4. Trigger first run
gh workflow run orchestrator.yml
```

---

## 📦 What Gets Installed

```
your-project/
├── .github/
│   ├── workflows/
│   │   ├── orchestrator.yml          # 🎯 The brain - analyzes & prioritizes
│   │   ├── copilot-automation.yml    # 🤖 Auto-assigns Copilot to issues
│   │   ├── workflow-doctor.yml       # 🏥 Self-heals workflow failures
│   │   └── manual-pr-review.yml      # ⚙️  Backup manual controls
│   │
│   ├── scripts/
│   │   ├── orchestrator.py           # Analysis engine (274 lines)
│   │   ├── auto_reviewer.py          # PR safety validator (200+ lines)
│   │   └── workflow_doctor.py        # Failure diagnostics (150+ lines)
│   │
│   ├── copilot-instructions.md       # 📖 AI context for your project
│   └── PR-REVIEW-FLOW.md             # 📚 Documentation
│
└── requirements.txt                   # Python deps (if not exists)
```

**Total:** ~800 lines of Python + ~400 lines of YAML = **Your repo is now autonomous**

---

## ⚙️ Configuration (Customize for Your Project)

### **Step 1: Define Your Project Context**

Edit `.github/copilot-instructions.md`:

```markdown
# Project: YourAwesomeApp

## What We're Building
[Brief description - e.g., "A SaaS platform for X" or "Mobile app for Y"]

## Tech Stack
- **Frontend:** React 18 + TypeScript + Tailwind
- **Backend:** Node.js + Express + PostgreSQL
- **Infra:** AWS (Lambda, RDS, S3)
- **CI/CD:** GitHub Actions

## Architecture Rules
1. All API routes must have rate limiting
2. Database migrations must be reversible
3. Environment variables must be validated at startup
4. Every feature needs unit + integration tests

## Critical Files (NEVER auto-merge)
- `src/auth/*` - Authentication logic
- `src/api/payments/*` - Payment processing
- `terraform/*` - Infrastructure code
- `.github/workflows/*` - CI/CD pipelines

## Coding Standards
- Use async/await, not callbacks
- Prefer functional components over class components
- All API errors must return consistent JSON structure
- Use Zod for runtime validation

## Safety Rules
❌ Never commit secrets or API keys
❌ Never disable CORS in production
❌ Never bypass authentication checks
❌ Never use `eval()` or `dangerouslySetInnerHTML`
```

### **Step 2: Customize Scanning Patterns**

Edit `.github/scripts/orchestrator.py` (lines 45-70):

```python
# Add your domain-specific patterns
PRIORITY_PATTERNS = {
    'security': [
        r'TODO.*security',
        r'FIXME.*auth',
        r'XXX.*password',
        r'# Security risk:',
        r'HACK.*crypto',
    ],
    'performance': [
        r'TODO.*optimize',
        r'FIXME.*slow',
        r'N\+1 query',
        r'# Performance issue',
    ],
    'api': [
        r'TODO.*endpoint',
        r'FIXME.*API',
        r'# API breaking change',
    ],
    'database': [
        r'TODO.*migration',
        r'FIXME.*schema',
        r'# DB optimization needed',
    ],
    'testing': [
        r'TODO.*test',
        r'FIXME.*coverage',
        r'# Needs tests',
    ],
}

# Customize priority calculation
def calculate_priority(task):
    category = task.get('category', '')
    
    # Your business logic
    if 'security' in category or 'auth' in category:
        return {'urgency': 10, 'impact': 10, 'risk': 9}
    elif 'payment' in category or 'billing' in category:
        return {'urgency': 9, 'impact': 9, 'risk': 8}
    elif 'api' in category:
        return {'urgency': 7, 'impact': 8, 'risk': 6}
    elif 'performance' in category:
        return {'urgency': 6, 'impact': 7, 'risk': 5}
    elif 'testing' in category:
        return {'urgency': 5, 'impact': 8, 'risk': 3}
    else:
        return {'urgency': 5, 'impact': 5, 'risk': 4}
```

### **Step 3: Define Critical Files**

Edit `.github/scripts/auto_reviewer.py` (lines 20-50):

```python
# Files that require human review (won't auto-merge)
CRITICAL_FILES = {
    # Authentication & Security
    'src/auth/': ['authentication', 'authorization', 'JWT handling'],
    'src/middleware/auth.ts': ['auth middleware'],
    'src/utils/crypto.ts': ['encryption utilities'],
    
    # Payment & Money
    'src/api/payments/': ['payment processing'],
    'src/services/stripe/': ['Stripe integration'],
    'src/models/Transaction.ts': ['transaction model'],
    
    # Database
    'migrations/': ['database schema changes'],
    'src/db/schema.ts': ['database schema'],
    'prisma/schema.prisma': ['Prisma schema'],
    
    # Infrastructure
    'terraform/': ['infrastructure as code'],
    'k8s/': ['Kubernetes manifests'],
    'docker-compose.yml': ['container orchestration'],
    '.github/workflows/': ['CI/CD workflows'],
    
    # Core Business Logic
    'src/core/': ['core business logic'],
    'src/services/': ['critical services'],
}

# Adjust thresholds for your team
SAFETY_THRESHOLDS = {
    'max_files_for_auto_merge': 3,      # Max files in a PR to auto-merge
    'max_lines_changed': 100,            # Max total lines changed
    'max_critical_files': 1,             # Max critical files touched
    'auto_merge_delay_seconds': 30,      # Human override window
}
```

### **Step 4: Set Automation Level**

Edit `.github/workflows/copilot-automation.yml` (lines 100-120):

```yaml
# Choose your automation level

# LEVEL 1: Observer Mode (safest)
auto_merge_enabled: false
auto_approve_enabled: false
auto_issue_creation: true
# Result: System creates issues only, you control everything else

# LEVEL 2: Assistant Mode (recommended for most teams)
auto_merge_enabled: true  # Only docs/configs
auto_approve_enabled: true  # Code PRs need manual merge
auto_issue_creation: true
# Result: System approves, you click "Merge" button (5 seconds)

# LEVEL 3: Autonomous Mode (for mature teams)
auto_merge_enabled: true  # Everything under threshold
auto_approve_enabled: true
auto_issue_creation: true
critical_files_require_human: true  # Safety brake
# Result: System handles 80% automatically
```

---

## 🎮 How to Use

### **The Main Button: Orchestrator**

```bash
# Trigger analysis manually
gh workflow run orchestrator.yml

# Or wait for Monday 8am UTC (automatic weekly run)
```

**What happens:**
1. ⏱️  ~20 seconds: Scans entire codebase
2. 📋 Creates 3-5 prioritized issues
3. 🤖 Auto-assigns Copilot to each
4. 💻 Copilot creates PRs (Draft)
5. 🔍 Auto-reviewer validates
6. ✅ Safe PRs auto-merge (30s delay)
7. 👤 Risky PRs wait for you

### **Monitor Progress**

```bash
# Check orchestrator runs
gh run list --workflow=orchestrator.yml --limit 5

# View latest report
gh run view $(gh run list --workflow=orchestrator.yml --limit 1 --json databaseId --jq '.[0].databaseId')

# List active issues
gh issue list --label "copilot-assigned"

# Check PRs awaiting review
gh pr list --label "automated-fix"
```

### **Manual Controls**

```bash
# Approve and merge a PR (if auto-reviewer only approved)
gh workflow run manual-pr-review.yml -f pr_number=42 -f action=approve-and-merge

# Just approve (let someone else merge)
gh workflow run manual-pr-review.yml -f pr_number=42 -f action=approve-only

# Emergency: Request changes
gh workflow run manual-pr-review.yml -f pr_number=42 -f action=request-changes
```

### **Pause the Loop**

```bash
# Disable orchestrator schedule
gh workflow disable orchestrator.yml

# Re-enable when ready
gh workflow enable orchestrator.yml
```

---

## 🔧 Troubleshooting

### **Issue: Orchestrator runs but doesn't create issues**

```bash
# Check logs
gh run view --log

# Common causes:
# 1. No TODOs/FIXMEs found → Add some or lower thresholds
# 2. Permissions issue → Check workflow has 'issues: write'
# 3. API rate limit → Wait or add PAT with higher limits
```

**Fix:** Edit `orchestrator.py` line 85:

```python
# Lower threshold to create issues more aggressively
MIN_PRIORITY_SCORE = 3  # Was 5, now creates more issues
```

### **Issue: Copilot doesn't create PRs**

```bash
# Check if Copilot coding agent is enabled
gh api repos/:owner/:repo/copilot

# Verify issue has @copilot mention
gh issue view 42 --json body
```

**Fix:** Manually trigger for existing issues:

```bash
# Re-tag Copilot
gh issue comment 42 --body "@copilot please work on this"
```

### **Issue: PRs not auto-merging**

```bash
# Check auto-reviewer decision
gh pr view 42 --json reviews

# View review comment with reasoning
```

**Common reasons:**
- ❌ Touches critical files (intentional safety)
- ❌ Too many lines changed (>100)
- ❌ No "Resolves #X" in PR body

**Fix:** Either:
1. Use manual merge workflow
2. Lower thresholds in `auto_reviewer.py`
3. Remove file from CRITICAL_FILES list

### **Issue: Workflow Doctor keeps creating issues**

This means workflows are failing repeatedly.

```bash
# Check which workflow is failing
gh run list --status failure --limit 10

# View failure logs
gh run view <run-id> --log
```

**Fix:** The Workflow Doctor should create diagnostic issues. Review and fix the root cause.

---

## 📊 Metrics & Observability

### **Dashboard (GitHub Insights)**

Create `.github/workflows/metrics-dashboard.yml`:

```yaml
name: "📊 Metrics Dashboard"

on:
  workflow_run:
    workflows: ["🎯 Orchestrator - Autonomous Project Lead"]
    types: [completed]

jobs:
  metrics:
    runs-on: ubuntu-latest
    steps:
      - name: Calculate Metrics
        uses: actions/github-script@v7
        with:
          script: |
            const startDate = new Date();
            startDate.setDate(startDate.getDate() - 7);
            
            // Issues created by Orchestrator
            const { data: issues } = await github.rest.issues.listForRepo({
              owner: context.repo.owner,
              repo: context.repo.repo,
              creator: 'github-actions[bot]',
              since: startDate.toISOString()
            });
            
            // PRs auto-merged
            const { data: prs } = await github.rest.pulls.list({
              owner: context.repo.owner,
              repo: context.repo.repo,
              state: 'closed',
              sort: 'updated',
              direction: 'desc'
            });
            
            const autoMerged = prs.filter(pr => 
              pr.merged_at && 
              pr.body.includes('Auto-merged by')
            );
            
            // Generate report
            const summary = `## 📊 Weekly Automation Report
            
            **Issues Created:** ${issues.length}
            **PRs Auto-Merged:** ${autoMerged.length}
            **PRs Requiring Review:** ${prs.length - autoMerged.length}
            **Automation Rate:** ${Math.round((autoMerged.length / prs.length) * 100)}%
            
            **Time Saved:** ~${autoMerged.length * 15} minutes (est.)
            `;
            
            console.log(summary);
            core.summary.addRaw(summary).write();
```

### **Key Metrics to Track**

```python
# Add to your orchestrator_report.md
weekly_metrics = {
    # Productivity
    'issues_created': 12,
    'prs_auto_merged': 8,
    'prs_needing_review': 4,
    'automation_rate': '66%',  # 8/12
    
    # Quality
    'test_coverage_increase': '+5%',
    'bugs_found': 2,
    'security_issues_fixed': 1,
    
    # Efficiency
    'avg_issue_to_pr_time': '45 minutes',
    'avg_pr_to_merge_time': '2 hours',
    'human_review_time_saved': '3 hours',
    
    # Health
    'workflow_failures': 1,
    'self_healing_success_rate': '100%',
    'stale_issues': 0,
}
```

---

## 🎓 Advanced Patterns

### **Pattern 1: Multi-Stage Rollout**

Start conservative, increase automation gradually:

```yaml
# Week 1: Observer Mode
auto_merge: false
notify_only: true

# Week 2: Auto-approve docs only
auto_merge: true
auto_merge_patterns: ['*.md', '*.json', 'README*']

# Week 3: Auto-approve code (manual merge)
auto_approve: true
auto_merge: false

# Week 4: Full autonomous (with critical file safety)
auto_approve: true
auto_merge: true
critical_files_block: true
```

### **Pattern 2: Domain-Specific Agents**

Create specialized orchestrators:

```yaml
# .github/workflows/security-orchestrator.yml
name: "🔒 Security Scanner"
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  scan:
    steps:
      - run: python .github/scripts/security_scanner.py
      # Creates high-priority security issues
      # Auto-assigns to security team + Copilot
```

### **Pattern 3: Integration with Other Tools**

```yaml
# Connect to Slack, Jira, Linear, etc.
- name: Notify Slack
  if: steps.analyze.outputs.critical_issues > 0
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "🚨 Orchestrator found ${{ steps.analyze.outputs.critical_issues }} critical issues",
        "blocks": [...]
      }
```

---

## 🚀 Real-World Examples

### **Example 1: Web App (Next.js + Prisma)**

```bash
# Scans for:
- Missing API input validation
- Database queries without indexes
- Unprotected API routes
- Missing error boundaries
- Unused dependencies

# Auto-fixes:
- Adds input validation schemas
- Creates database indexes
- Adds rate limiting
- Wraps components in error boundaries
```

### **Example 2: Python Data Pipeline**

```bash
# Scans for:
- Missing data validation
- Brittle hardcoded transforms
- No retry logic
- Missing monitoring/alerts
- Unhandled edge cases

# Auto-fixes:
- Adds Pydantic schemas
- Parameterizes transforms
- Implements exponential backoff
- Adds logging + metrics
```

### **Example 3: Mobile App (React Native)**

```bash
# Scans for:
- Unoptimized images
- Missing offline handling
- Memory leaks
- Accessibility issues
- Hardcoded strings (i18n)

# Auto-fixes:
- Compresses images
- Adds AsyncStorage caching
- Implements cleanup in useEffect
- Adds accessibility labels
- Extracts to translation files
```

---

## 🎯 ROI Calculator

**Time Investment:**
- Initial setup: 30 minutes
- Customization: 1-2 hours
- Learning/testing: 2-3 hours
- **Total:** ~4 hours

**Time Saved (per week):**
- Manual issue triage: 2 hours → 0 hours
- Code review (safe changes): 3 hours → 30 minutes
- Bug hunting: 1 hour → 20 minutes
- Workflow debugging: 1 hour → 0 hours (self-healing)
- **Total saved:** ~6.5 hours/week

**Payback:** <1 week for a single developer, <1 day for a team

**Yearly benefit:** 6.5 hrs/week × 50 weeks = **325 hours saved** (~$32,500 at $100/hr)

---

## 🛟 Support & Community

- **Issues/Bugs:** [GitHub Issues](https://github.com/grloper/gel-nails-machine/issues)
- **Discussions:** [GitHub Discussions](https://github.com/grloper/gel-nails-machine/discussions)
- **Examples:** [Showcase Repos](https://github.com/topics/autonomous-development-loop)
- **Original Implementation:** [gel-nails-machine](https://github.com/grloper/gel-nails-machine)

---

## 📜 License

MIT - Use freely in any project (personal or commercial)

---

## 🙏 Credits

Built with:
- GitHub Actions
- GitHub Copilot Coding Agent
- Python + PyGithub
- Love for automation ❤️

Inspired by: Unix pipes, DevOps, Self-healing systems, The dream of autonomous software

---

**Ready to make your repo self-managing?** Run the install command above! 🚀
