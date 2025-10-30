# Agent System Quick Start Guide

## Overview
This project uses a **multi-agent AI collaboration system** where specialized AI agents work autonomously on different domains, share knowledge, and iterate based on collective findings.

## Available Agents

| Agent | Emoji | Expertise | Trigger Label |
|-------|-------|-----------|---------------|
| **Research Agent** | 🔬 | Physics, biology, chemistry, safety standards | `agent:research` |
| **Hardware Agent** | ⚡ | Electronics, circuits, mechanical design | `agent:hardware` |
| **Software Agent** | 💻 | Code, algorithms, computer vision | `agent:software` |
| **Safety Agent** | 🛡️ | Risk assessment, compliance, fail-safes | `agent:safety` |
| **Design Agent** | 🎨 | 3D modeling, UX/UI, product design | `agent:design` |
| **Integration Agent** | 🔗 | System integration, testing, CI/CD | `agent:integration` |

## How to Use Agents

### Method 1: Create an Issue with Agent Template

1. Go to **Issues** → **New Issue**
2. Choose appropriate template:
   - 🔬 **Research Task** - For scientific questions
   - ⚡ **Hardware Task** - For electronics/mechanical
   - 💻 **Software Task** - For code development
   - 🛡️ **Safety Review** - For safety assessments
3. Fill out the template
4. Submit - Agent automatically notified

### Method 2: Add Agent Labels to Existing Issues

Add one or more labels to trigger agents:
```
agent:research
agent:hardware
agent:software
agent:safety
agent:design
agent:integration
```

Agents will automatically comment and begin analysis.

### Method 3: Manual Agent Trigger

Go to **Actions** → **Multi-Agent Collaboration System** → **Run workflow**

Select:
- Which agent to trigger
- Optional task description

### Method 4: Agent Mentions (Future)

In issue comments, mention agents:
```markdown
@research-agent What is the optimal UV wavelength for gel type X?
@hardware-agent Review this circuit design please.
@safety-agent Is this modification safe?
```

## Agent Workflows

### Example 1: Research Question

**Scenario**: You want to know if 365nm or 405nm UV is better

1. Create issue using **🔬 Research Task** template
2. Research Agent is notified automatically
3. Research Agent:
   - Reviews scientific literature
   - Analyzes safety implications
   - Consults other agents if needed
   - Provides evidence-based recommendation
4. Other agents review and comment
5. Consensus reached → Implementation begins

### Example 2: Hardware Design

**Scenario**: Need to design LED driver circuit

1. Create issue using **⚡ Hardware Task** template
2. Hardware Agent analyzes requirements
3. Hardware Agent may consult:
   - Research Agent for UV specifications
   - Software Agent for GPIO requirements
   - Safety Agent for fail-safe design
4. Hardware Agent produces:
   - Circuit schematic
   - Component BOM
   - Wiring diagram
   - Test protocol
5. Safety Agent reviews design
6. Integration Agent coordinates testing

### Example 3: Multi-Agent Collaboration

**Scenario**: Implementing pulsed UV mode

1. **Software Agent** creates implementation plan
2. **Research Agent** validates pulse timing scientifically
3. **Hardware Agent** confirms PWM hardware capability
4. **Safety Agent** reviews temperature implications
5. All agents reach consensus
6. **Software Agent** implements code
7. **Integration Agent** coordinates testing
8. **Safety Agent** validates final implementation

## Agent Communication

### GitHub Issues
- Primary task tracking
- Each agent comments with analysis
- Sub-issues for complex tasks
- Labels for agent assignment

### GitHub Discussions
- Knowledge sharing
- Design decisions
- Trade-off analysis
- Q&A between agents

### Pull Requests
- Code reviews by multiple agents
- Safety Agent reviews all PRs
- Cross-domain validation
- Integration testing

### Project Board
- Kanban visualization
- Agent swimlanes
- Dependency tracking
- Progress monitoring

## Agent Collaboration Principles

### 1. Evidence-Based Decisions
All agents must provide:
- Sources for claims
- Quantified data (not "better", but "30% faster")
- Trade-off analysis
- Confidence levels

### 2. Safety First
- Safety Agent has veto power
- Any agent can raise safety concerns
- Safety features cannot be removed without consensus
- When in doubt, conservative approach

### 3. Cross-Domain Validation
- Hardware changes reviewed by Software Agent
- Software changes reviewed by Safety Agent
- Research validates technical approaches
- Integration Agent ensures compatibility

### 4. Iterative Improvement
- Agents learn from test results
- Failed experiments documented
- Successful patterns promoted
- Continuous knowledge base updates

## Automation

### Scheduled Tasks

**Daily (2 AM UTC)**:
- Research Agent checks for new publications
- Research Agent monitors safety standard updates
- System health check

**On Every PR**:
- Safety Agent reviews changes
- Integration Agent runs tests
- Software Agent checks code quality

**On New Issue**:
- Relevant agents automatically notified
- Agent analysis begins within minutes
- Collaboration thread initiated

### Continuous Integration

```yaml
# Every commit triggers:
1. Software Agent: Code quality check
2. Software Agent: Unit tests
3. Safety Agent: Safety pattern validation
4. Integration Agent: Build verification
```

## Monitoring Agent Performance

### Metrics Dashboard (Future)
- Issues resolved per agent
- Cross-agent collaboration frequency
- Response time
- Innovation quality
- Safety issues prevented

### Agent Health Check
```bash
# Check agent activity
gh issue list --label "agent:research" --state all
gh issue list --label "agent:hardware" --state all
gh issue list --label "agent:software" --state all
```

## Best Practices

### For Developers

✅ **DO:**
- Use agent templates for structured requests
- Tag multiple agents when needed
- Provide context and requirements
- Respond to agent questions promptly
- Review agent recommendations critically

❌ **DON'T:**
- Bypass agent review for safety-critical changes
- Ignore agent safety warnings
- Make assumptions without research
- Commit directly without PR review

### For Agents

✅ **DO:**
- Cite sources for all claims
- Quantify recommendations
- Consider trade-offs explicitly
- Collaborate across domains
- Escalate safety concerns immediately

❌ **DON'T:**
- Make recommendations without evidence
- Ignore safety implications
- Work in isolation
- Assume other domains
- Rush to solutions without analysis

## Example Agent Interactions

### Research Agent Response
```markdown
🔬 **Research Agent Analysis**

**Question**: Optimal UV wavelength for gel polish curing?

**Findings**:
- 365nm: Cure time 30-45s (photoinitiator peak absorption)
- 405nm: Cure time 60-90s (lower efficiency)
- Both safe with proper enclosure (ANSI Z136.1)

**Recommendation**: 365nm for primary curing

**Trade-offs**: Requires amber acrylic (+$8 vs clear)

**Sources**: 
- Smith et al. (2023) J. Polymer Sci.
- FDA UV Lamp Guidance

**Safety**: Max 30s continuous per ACGIH TLV

@hardware-agent - Confirm LED availability at 365nm
@safety-agent - Review enclosure requirements for 365nm
```

### Hardware Agent Response
```markdown
⚡ **Hardware Agent Review**

**Component Analysis**: 365nm UV LED strips

**Options**:
1. High-power: 5W/m, $30, requires heatsink
2. Standard: 3W/m, $18, passive cooling OK

**Recommendation**: Standard (3W/m)
- Sufficient intensity for 30s cure
- Thermal manageable (<60°C)
- Cost effective

**Circuit Design**: Updated LED driver for 365nm
- Schematic: `hardware/schematics/led-driver-365nm.pdf`
- BOM: Added to main BOM

**Safety**: Thermal fuse rated for 70°C cutoff

@software-agent - Confirm 30s cure profile in code
@safety-agent - Review thermal protection
```

## Troubleshooting

### Agent Not Responding?
1. Check issue has correct label
2. Verify workflow triggered (Actions tab)
3. Check workflow logs for errors
4. Manually trigger workflow if needed

### Agent Conflicts?
1. Safety Agent has final say on safety
2. Research Agent provides evidence
3. Integration Agent mediates technical disputes
4. Escalate to project maintainer if needed

### Need Human Override?
Add label: `human-review-required`
- Pauses agent automation
- Flags for manual review
- Agent recommendations still available

## Future Enhancements

- [ ] AI-powered agent responses (GPT/Claude integration)
- [ ] Agent voting mechanism for decisions
- [ ] Automated code generation by Software Agent
- [ ] 3D model generation by Design Agent
- [ ] Simulation Agent for virtual testing
- [ ] Manufacturing Agent for scale-up planning
- [ ] Business Agent for market analysis

## Resources

- **Agent Architecture**: `.github/agents/README.md`
- **Agent Instructions**: `.github/agents/[agent-name]-agent.md`
- **Workflows**: `.github/workflows/agent-system.yml`
- **Project Board**: https://github.com/grloper/gel-nails-machine/projects

## Getting Help

- **Documentation**: Read agent-specific instructions
- **Discussions**: Ask in GitHub Discussions
- **Issues**: Report agent bugs with `agent-system` label
- **Contact**: Open issue for feature requests

---

**Welcome to the multi-agent future of collaborative development!** 🚀
