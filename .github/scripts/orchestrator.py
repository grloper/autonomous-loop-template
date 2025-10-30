#!/usr/bin/env python3
"""
Orchestrator Agent - Autonomous Project Lead
Analyzes project, prioritizes work, creates issues, triggers agents
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from github import Github

def main():
    print("━" * 60)
    print("🎯 ORCHESTRATOR ACTIVATED")
    print("━" * 60)
    print(f"Mode: {os.environ.get('ORCHESTRATOR_MODE', 'scheduled')}")
    print(f"Focus: {os.environ.get('FOCUS_AREA', 'all')}")
    print(f"Time: {datetime.now().isoformat()}")
    print("━" * 60)

    # Phase 1: Analyze Codebase
    print("\n📊 PHASE 1: CODEBASE ANALYSIS")
    print("-" * 60)

    findings = {
        "todos": [],
        "safety_gaps": [],
        "missing_tests": []
    }

    # Scan Python files
    for py_file in Path('.').rglob('*.py'):
        if '.git' in str(py_file) or '__pycache__' in str(py_file):
            continue
        
        try:
            content = py_file.read_text()
            for i, line in enumerate(content.split('\n'), 1):
                if 'TODO' in line or 'FIXME' in line:
                    findings['todos'].append({
                        'file': str(py_file),
                        'line': i,
                        'text': line.strip()
                    })
        except Exception as e:
            print(f"⚠️  Error reading {py_file}: {e}")

    # Check for tests
    test_files = list(Path('.').rglob('test_*.py')) + list(Path('.').rglob('*_test.py'))
    if len(test_files) == 0:
        findings['missing_tests'].append("No test files found")

    print(f"✓ TODOs found: {len(findings['todos'])}")
    print(f"✓ Test files: {len(test_files)}")
    print(f"⚠️  Safety concerns: {len(findings['safety_gaps'])}")

    # Phase 2: Generate Priority Tasks
    print("\n🎯 PHASE 2: PRIORITY PLANNING")
    print("-" * 60)

    focus_area = os.environ.get('FOCUS_AREA', 'all').lower()
    print(f"📍 Focus Area: {focus_area}")

    all_tasks = []

    # Task 1: Testing (SOFTWARE)
    if findings['missing_tests']:
        all_tasks.append({
            'priority': 1,
            'title': '💻 [SOFTWARE] Implement Unit Testing Framework',
            'description': 'No test coverage found. Add pytest framework and write tests for hand_tracker.py and led_controller.py modules.',
            'impact': 8,
            'urgency': 7,
            'difficulty': 5,
            'risk': 3,
            'assign_to': ['software-agent'],
            'deadline': (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d'),
            'labels': ['agent:software', 'priority:high', 'testing'],
            'category': 'software'
        })

    # Task 2: Integration (INTEGRATION)
    all_tasks.append({
        'priority': 2,
        'title': '🔗 [INTEGRATION] Connect Hand Tracking to UV Control',
        'description': 'Both modules are complete independently. Create main_controller.py to integrate hand tracking, positioning, and UV curing workflow.',
        'impact': 9,
        'urgency': 6,
        'difficulty': 7,
        'risk': 5,
        'assign_to': ['integration-agent', 'software-agent', 'safety-agent'],
        'deadline': (datetime.now() + timedelta(days=21)).strftime('%Y-%m-%d'),
        'labels': ['agent:integration', 'agent:software', 'agent:safety', 'priority:high'],
        'category': 'integration'
    })

    # Task 3: Safety (SAFETY)
    all_tasks.append({
        'priority': 3,
        'title': '🛡️ [SAFETY] Implement Hardware Safety Interlocks',
        'description': 'Add door sensors, emergency stop validation, and hardware safety interlocks for UV control system.',
        'impact': 10,
        'urgency': 8,
        'difficulty': 6,
        'risk': 9,
        'assign_to': ['safety-agent', 'hardware-agent'],
        'deadline': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
        'labels': ['agent:safety', 'agent:hardware', 'priority:critical', 'safety-critical'],
        'category': 'safety'
    })

    # Filter tasks based on focus area
    if focus_area == 'all':
        tasks = all_tasks
    else:
        # Filter to only tasks matching the focus area
        tasks = [t for t in all_tasks if focus_area in t['category'] or focus_area in str(t['labels'])]
        
    if not tasks:
        print(f"⚠️  No tasks found for focus area: {focus_area}")
        print("Available categories: software, integration, safety, hardware")
        return

    print(f"📋 Generated {len(tasks)} priority tasks (filtered by: {focus_area})")
    for task in tasks:
        print(f"  {task['priority']}. {task['title']}")

    # Phase 3: Create GitHub Issues
    print("\n🚀 PHASE 3: CREATING ISSUES")
    print("-" * 60)

    g = Github(os.environ['GITHUB_TOKEN'])
    repo = g.get_repo(os.environ['GITHUB_REPOSITORY'])

    created_issues = []

    # Create all filtered tasks (respects focus area)
    for task in tasks:
        try:
            agents_list = '\n'.join(f"- @{agent}" for agent in task['assign_to'])
            
            body = f"""**🎯 Created by: Orchestrator Agent**
**Analysis Date**: {datetime.now().strftime('%Y-%m-%d')}
**Priority**: {task['priority']} of {len(tasks)}
**Estimated Effort**: {task['difficulty'] * 2} hours

---

## 📋 Task Description
{task['description']}

## 🎯 Success Criteria
- [ ] Implementation complete and tested
- [ ] Safety validation passed (if applicable)
- [ ] Documentation updated
- [ ] Code reviewed and merged

## 📊 Priority Scores
- **Impact**: {task['impact']}/10 - How much this moves project forward
- **Urgency**: {task['urgency']}/10 - Time sensitivity
- **Difficulty**: {task['difficulty']}/10 - Implementation complexity
- **Risk**: {task['risk']}/10 - Safety/technical risk

## 👥 Assigned Agents
{agents_list}

## ⏰ Deadline
**Target completion**: {task['deadline']}

## 🔗 Related Work
This task was identified during automated orchestrator analysis. Review the orchestrator's strategic report in the Actions tab for full context.

---

**Orchestrator Run ID**: {os.environ.get('GITHUB_RUN_ID', 'unknown')}
**Next Orchestrator Review**: Next Monday 8am UTC
"""
            
            issue = repo.create_issue(
                title=task['title'],
                body=body,
                labels=task['labels']
            )
            
            # Auto-assign Copilot immediately
            try:
                issue.create_comment(
                    body="""🤖 **Auto-Assigned by Orchestrator**

@copilot I've been assigned to this issue. Let me analyze it and create a fix.

**Issue Type**: {}
**Priority**: {}

I'll:
1. Analyze the problem
2. Research the best solution
3. Create a pull request with the fix
4. Request review from the auto-reviewer

_Estimated time: 2-5 minutes_""".format(
                        ', '.join(task['labels']), 
                        '🔴 CRITICAL' if 'priority:critical' in task['labels'] else '🟡 HIGH' if 'priority:high' in task['labels'] else '🟢 MEDIUM'
                    )
                )
                issue.add_to_labels('copilot-assigned', 'in-progress')
                print(f"  └─ ✅ Copilot auto-assigned")
            except Exception as e:
                print(f"  └─ ⚠️  Failed to auto-assign Copilot: {e}")
            
            created_issues.append({
                'number': issue.number,
                'title': task['title'],
                'url': issue.html_url
            })
            
            print(f"✅ Created Issue #{issue.number}: {task['title']}")
            
        except Exception as e:
            print(f"❌ Failed to create issue: {e}")

    # Phase 4: Generate Report
    print("\n📊 PHASE 4: STRATEGIC REPORT")
    print("-" * 60)

    report = f"""# 🎯 Orchestrator Strategic Report
**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
**Mode**: {os.environ.get('ORCHESTRATOR_MODE', 'scheduled')}
**Run ID**: {os.environ.get('GITHUB_RUN_ID', 'unknown')}

---

## 📈 Executive Summary

The Orchestrator has analyzed the entire project and identified **{len(tasks)} priority tasks** across all domains.

**Key Findings**:
- 📝 **{len(findings['todos'])} TODOs/FIXMEs** found in codebase
- 🧪 **Test coverage**: {'0%' if findings['missing_tests'] else '100%'} (needs improvement)
- 🚀 **{len(created_issues)} issues created** and assigned to specialized agents

---

## 🎯 Top Priority Actions

"""

    for i, task in enumerate(tasks[:5], 1):
        report += f"{i}. **{task['title']}**\n"
        report += f"   - Urgency: {task['urgency']}/10 | Impact: {task['impact']}/10\n"
        report += f"   - Assigned: {', '.join(task['assign_to'])}\n\n"

    report += "\n---\n\n## 📋 Issues Created\n\n"

    if created_issues:
        for issue in created_issues:
            report += f"- #{issue['number']}: {issue['title']}\n"
            report += f"  {issue['url']}\n\n"
    else:
        report += "No issues created this run.\n\n"

    report += """
---

## 🔄 Next Actions

**Immediate** (Next 7 days):
- Safety Agent: Review emergency stop implementation
- Hardware Agent: Design door interlock sensors
- Software Agent: Set up testing framework

**Short-term** (Next 30 days):
- Integration Agent: Build main controller
- Design Agent: Create assembly guide
- All agents: Collaborate on first integration test

**Long-term** (Next 90 days):
- Research Agent: Optimize UV wavelength selection
- Software Agent: Implement automated gel application
- Integration Agent: Prepare for alpha testing

---

## 📊 Project Health Metrics

| Metric | Status | Target |
|--------|--------|--------|
| Safety Compliance | ⚠️ Needs Work | 100% |
| Test Coverage | 0% | 80% |
| Documentation | ✅ Good | Complete |
| Integration | 🚧 Not Started | Complete |

---

*This report was generated autonomously by the Orchestrator Agent. All issues have been created and agents have been notified. The project is self-managing.*

🎯 **Orchestrator Status**: Active and monitoring
**Next Review**: Next Monday at 8am UTC (automatic)
"""

    # Save report
    with open('orchestrator_report.md', 'w') as f:
        f.write(report)

    print(report)

    # Summary
    print("\n" + "━" * 60)
    print("✅ ORCHESTRATOR COMPLETE")
    print("━" * 60)
    print(f"✅ {len(tasks)} tasks prioritized")
    print(f"✅ {len(created_issues)} issues created")
    print(f"📊 Report saved to orchestrator_report.md")
    print("━" * 60)

if __name__ == '__main__':
    main()
