#!/usr/bin/env python3
"""
Auto-Reviewer - Automated PR Review System

Analyzes pull requests and determines if they're safe to auto-merge.
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Tuple
from github import Github


class AutoReviewer:
    """Automatically review PRs for safety and quality"""
    
    # Files that require human review
    CRITICAL_FILES = [
        'docs/SAFETY.md',
        '.github/workflows/',
        'requirements.txt',
        'software/uv_control/led_controller.py',  # UV control is safety-critical
    ]
    
    # Patterns that require human review
    CRITICAL_PATTERNS = [
        'emergency_stop',
        'max_continuous_time',
        'UV',
        'safety',
        'GPIO',
        'permissions',
    ]
    
    # Safe file patterns that can be auto-merged
    SAFE_FILE_PATTERNS = [
        '.md',  # Documentation
        '.txt',  # Text files
        '.yml',  # Workflow files (unless in CRITICAL_FILES)
        '.yaml',
    ]
    
    def __init__(self, repo_name: str, pr_number: int):
        self.repo_name = repo_name
        self.pr_number = pr_number
        self.github = Github(os.environ['GITHUB_TOKEN'])
        self.repo = self.github.get_repo(repo_name)
        self.pr = self.repo.get_pull(pr_number)
        
        # Analysis results
        self.verdict = "COMMENT"  # APPROVE, REQUEST_CHANGES, COMMENT
        self.auto_merge = False
        self.summary = ""
        self.issues = []
        self.required_changes = []
        self.critical_files_found = []
    
    def analyze(self) -> bool:
        """Analyze the PR and determine verdict"""
        print(f"🔍 Analyzing PR #{self.pr_number}: {self.pr.title}")
        
        try:
            # Get PR details
            files_changed = list(self.pr.get_files())
            labels = [label.name for label in self.pr.labels]
            
            print(f"  Files changed: {len(files_changed)}")
            print(f"  Labels: {', '.join(labels)}")
            
            # Check 1: Is this an automated fix?
            is_automated = any(label in labels for label in ['automated-fix', 'workflow-doctor'])
            
            # Check 2: Analyze changed files
            critical_files = []
            safe_files = []
            
            for file in files_changed:
                filename = file.filename
                print(f"    Checking: {filename}")
                
                # Check if critical file
                is_critical = any(critical in filename for critical in self.CRITICAL_FILES)
                if is_critical:
                    critical_files.append(filename)
                    print(f"      ⚠️ Critical file detected")
                elif any(filename.endswith(pattern) for pattern in self.SAFE_FILE_PATTERNS):
                    safe_files.append(filename)
                    print(f"      ✅ Safe file")
                else:
                    critical_files.append(filename)
                    print(f"      ⚠️ Unknown file type, treating as critical")
            
            self.critical_files_found = critical_files
            
            # Check 3: Analyze PR content for critical patterns
            critical_patterns_found = []
            pr_body = self.pr.body or ""
            pr_title = self.pr.title or ""
            
            for pattern in self.CRITICAL_PATTERNS:
                if pattern.lower() in pr_body.lower() or pattern.lower() in pr_title.lower():
                    critical_patterns_found.append(pattern)
            
            # Check 4: Size check (small PRs are safer)
            total_changes = sum(f.additions + f.deletions for f in files_changed)
            is_small = total_changes < 100
            
            print(f"\n  Analysis:")
            print(f"    Automated: {is_automated}")
            print(f"    Critical files: {len(critical_files)}")
            print(f"    Safe files: {len(safe_files)}")
            print(f"    Critical patterns: {len(critical_patterns_found)}")
            print(f"    Total changes: {total_changes} lines")
            print(f"    Is small: {is_small}")
            
            # Decision logic - More permissive for productivity
            
            # TIER 1: Safe + Small = Auto-merge
            if len(critical_files) == 0 and is_small and len(safe_files) > 0:
                self.verdict = "APPROVE"
                self.auto_merge = True
                self.summary = f"✅ Safe changes: {len(safe_files)} documentation/config files, {total_changes} lines. Auto-merging."
                print(f"\n  Verdict: ✅ APPROVE + AUTO-MERGE (safe files only)")
            
            # TIER 2: Mostly safe + Small = Approve but manual merge
            elif len(critical_files) <= 1 and is_small:
                self.verdict = "APPROVE"
                self.auto_merge = False
                self.summary = f"✅ Looks good: {len(critical_files)} critical file(s), {total_changes} lines. Approved, please merge manually."
                print(f"\n  Verdict: ✅ APPROVE (manual merge recommended)")
            
            # TIER 3: Documentation only = Fast approve + auto-merge
            elif all(f.endswith('.md') for f in [file.filename for file in files_changed]) and is_small:
                self.verdict = "APPROVE"
                self.auto_merge = True
                self.summary = f"✅ Documentation changes only ({total_changes} lines). Safe to auto-merge."
                print(f"\n  Verdict: ✅ APPROVE + AUTO-MERGE (docs only)")
            
            # TIER 4: Critical files but small = Approve, no auto-merge
            elif len(critical_files) <= 2 and is_small:
                self.verdict = "APPROVE"
                self.auto_merge = False
                self.summary = f"✅ Small changes to {len(critical_files)} critical file(s). Approved, but please review and merge manually."
                print(f"\n  Verdict: ✅ APPROVE (critical files, manual merge)")
            
            # TIER 5: Too many critical files = Human review
            elif len(critical_files) > 2:
                self.verdict = "COMMENT"
                self.auto_merge = False
                self.summary = f"⚠️ Multiple critical files modified ({len(critical_files)} files). Please review carefully before merging."
                print(f"\n  Verdict: 💬 COMMENT (too many critical files)")
            
            # TIER 6: Too large = Human review
            elif not is_small:
                self.verdict = "COMMENT"
                self.auto_merge = False
                self.summary = f"⚠️ Large PR ({total_changes} lines changed). Please review carefully before merging."
                print(f"\n  Verdict: 💬 COMMENT (too large)")
            
            # DEFAULT: Approve but manual merge (be helpful, not blocking)
            else:
                self.verdict = "APPROVE"
                self.auto_merge = False
                self.summary = f"✅ Changes look safe but manual merge recommended for caution."
                print(f"\n  Verdict: ✅ APPROVE (manual merge)")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during analysis: {e}")
            self.verdict = "COMMENT"
            self.auto_merge = False
            self.summary = f"⚠️ Analysis error: {str(e)}. Manual review required."
            return False
    
    def output_results(self):
        """Output results in GitHub Actions format"""
        # Prepare outputs
        critical_files_str = '\n'.join([f"- `{f}`" for f in self.critical_files_found]) or "None"
        issues_str = '\n'.join([f"- {i}" for i in self.issues]) or "None"
        required_changes_str = '\n'.join([f"- {c}" for c in self.required_changes]) or "None"
        
        # Write to GITHUB_OUTPUT
        if 'GITHUB_OUTPUT' in os.environ:
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write(f"verdict={self.verdict}\n")
                f.write(f"auto_merge={str(self.auto_merge).lower()}\n")
                f.write(f"summary={self.summary}\n")
                f.write(f"critical_files<<EOF\n{critical_files_str}\nEOF\n")
                f.write(f"issues<<EOF\n{issues_str}\nEOF\n")
                f.write(f"required_changes<<EOF\n{required_changes_str}\nEOF\n")
        
        # Also print for debugging
        print(f"\n📊 Results:")
        print(f"  Verdict: {self.verdict}")
        print(f"  Auto-merge: {self.auto_merge}")
        print(f"  Summary: {self.summary}")


def main():
    parser = argparse.ArgumentParser(description='Auto-Reviewer - Automated PR review')
    parser.add_argument('--repo', required=True, help='Repository name (owner/repo)')
    parser.add_argument('--pr-number', required=True, type=int, help='Pull request number')
    
    args = parser.parse_args()
    
    print("🤖 Auto-Reviewer Starting...")
    print(f"  Repository: {args.repo}")
    print(f"  PR Number: {args.pr_number}")
    print()
    
    reviewer = AutoReviewer(args.repo, args.pr_number)
    
    # Analyze the PR
    if not reviewer.analyze():
        print("❌ Analysis failed")
        sys.exit(1)
    
    # Output results
    reviewer.output_results()
    
    print("\n✅ Auto-Reviewer completed")


if __name__ == '__main__':
    main()
