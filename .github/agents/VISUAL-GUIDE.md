# Multi-Agent System Visual Guide

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub Repository                         │
│                     gel-nails-machine                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ├─── Issues (Task Management)
                         ├─── Pull Requests (Code Review)
                         ├─── Discussions (Knowledge Sharing)
                         └─── Actions (Automation)
                         
┌─────────────────────────┴────────────────────────────────────────┐
│                    GitHub Actions Workflow                        │
│                   (.github/workflows/agent-system.yml)            │
└────────────────────────┬─────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐     ┌────▼────┐    ┌────▼────┐
    │Research │     │Hardware │    │Software │
    │  Agent  │     │  Agent  │    │  Agent  │
    │   🔬    │     │   ⚡     │    │   💻    │
    └────┬────┘     └────┬────┘    └────┬────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                    ┌────▼────┐
                    │ Safety  │
                    │  Agent  │
                    │   🛡️    │
                    └────┬────┘
                         │
              ┌──────────┴──────────┐
              │   Knowledge Base    │
              │  (Issues/Docs/PRs)  │
              └─────────────────────┘
```

## Agent Collaboration Flow

```
┌─────────────────┐
│  New Issue      │
│  Created        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Agent Router   │ ◄──── Checks labels, keywords, templates
│  Determines     │
│  Which Agents   │
└────────┬────────┘
         │
         ├──────────┬──────────┬──────────┐
         ▼          ▼          ▼          ▼
    ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
    │Research│ │Hardware│ │Software│ │ Safety │
    │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │
    └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
        │          │          │          │
        └──────────┴──────────┴──────────┘
                   │
                   ▼
         ┌──────────────────┐
         │  Agent Comments  │
         │  on Issue        │
         └─────────┬────────┘
                   │
                   ▼
         ┌──────────────────┐
         │  Cross-Agent     │
         │  Discussion      │
         └─────────┬────────┘
                   │
                   ▼
         ┌──────────────────┐
         │  Consensus       │
         │  Reached         │
         └─────────┬────────┘
                   │
                   ▼
         ┌──────────────────┐
         │  Implementation  │
         │  Begins          │
         └──────────────────┘
```

## Agent Decision Matrix

| Scenario | Primary Agent | Supporting Agents | Expected Outcome |
|----------|--------------|-------------------|------------------|
| "What UV wavelength?" | Research 🔬 | Hardware ⚡, Safety 🛡️ | Evidence-based recommendation |
| "Design LED circuit" | Hardware ⚡ | Research 🔬, Software 💻, Safety 🛡️ | Schematic + BOM + Test protocol |
| "Improve hand tracking" | Software 💻 | Research 🔬, Integration 🔗 | Optimized algorithm + benchmarks |
| "New safety feature" | Safety 🛡️ | ALL agents | Multi-layer safety validation |
| "3D print design" | Design 🎨 | Hardware ⚡, Safety 🛡️ | STL files + print settings |
| "System integration" | Integration 🔗 | ALL agents | Working end-to-end system |

## Example: Multi-Agent Collaboration

### Scenario: Implementing Pulsed UV Mode

```
┌──────────────────────────────────────────────────────────────────┐
│ Day 1: Issue Created                                             │
├──────────────────────────────────────────────────────────────────┤
│ Developer: "Need pulsed UV to reduce heat"                       │
│ Labels: agent:research, agent:hardware, agent:software          │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ Day 1 (15 min): Research Agent 🔬                                │
├──────────────────────────────────────────────────────────────────┤
│ "Analyzed literature on pulsed UV curing:                        │
│  - 80% duty cycle maintains cure quality                         │
│  - Reduces thermal buildup by 40%                                │
│  - Recommended: 400ms on, 100ms off                              │
│  Sources: [Paper X], [Study Y]"                                  │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ Day 1 (30 min): Hardware Agent ⚡                                 │
├──────────────────────────────────────────────────────────────────┤
│ "Verified PWM capability:                                        │
│  - Current MOSFET can handle 1kHz switching                      │
│  - No hardware changes needed                                    │
│  - Thermal: Expect 20°C reduction                                │
│  Ready for software implementation"                              │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ Day 1 (1 hour): Software Agent 💻                                │
├──────────────────────────────────────────────────────────────────┤
│ "Implementation plan:                                            │
│  1. Add pulse_mode to CuringProfile dataclass                    │
│  2. Implement _cure_pulsed() method                              │
│  3. Update profiles: gel_polish, base_coat                       │
│  4. Add unit tests for pulse timing                              │
│  ETA: 2 hours development + 1 hour testing"                      │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ Day 1 (45 min): Safety Agent 🛡️                                  │
├──────────────────────────────────────────────────────────────────┤
│ "Safety review:                                                  │
│  ✅ Pulse mode reduces thermal risk                              │
│  ✅ Maintains same total UV dose (safe)                          │
│  ⚠️ Ensure pulse timing enforced in hardware watchdog            │
│  ✅ Emergency stop still functional                              │
│  Approved with watchdog requirement"                             │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ Day 2: Software Agent Implementation                             │
├──────────────────────────────────────────────────────────────────┤
│ PR #123: "Add pulsed UV mode"                                    │
│ - Modified led_controller.py                                     │
│ - Added pulse parameters to CuringProfile                        │
│ - Implemented _cure_pulsed() method                              │
│ - Added unit tests (100% coverage)                               │
│ - Tested in simulation mode                                      │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ Day 2: Automated PR Review                                       │
├──────────────────────────────────────────────────────────────────┤
│ ✅ Software Agent: Code quality passed                           │
│ ✅ Safety Agent: No safety features removed                      │
│ ✅ Integration Agent: Tests passing                              │
│ 🔄 Hardware Agent: "Ready for hardware testing"                  │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ Day 3: Hardware Testing                                          │
├──────────────────────────────────────────────────────────────────┤
│ Hardware Agent: "Tested on Pi 4 with UV LEDs:                    │
│  - Temperature: 58°C (was 78°C) ✅                               │
│  - Cure quality: Identical to continuous ✅                      │
│  - No flickering observed ✅                                     │
│  - 5-minute thermal test passed ✅                               │
│  Recommendation: MERGE"                                          │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ Day 3: Merged to main                                            │
├──────────────────────────────────────────────────────────────────┤
│ 🎉 Feature complete!                                             │
│ 📊 Results: 26% thermal reduction, maintained cure quality       │
│ 📚 Knowledge base updated with findings                          │
│ 🔄 Agents learned: Pulsed patterns effective                     │
└──────────────────────────────────────────────────────────────────┘
```

## Agent Communication Patterns

### Pattern 1: Question & Answer
```
Developer → Research Agent: "What UV wavelength?"
Research Agent → Analysis + Evidence
Research Agent → Hardware Agent: "Can we source 365nm LEDs?"
Hardware Agent → Component availability + pricing
All Agents → Consensus: "Use 365nm, implement by [date]"
```

### Pattern 2: Design Review
```
Hardware Agent → Circuit design posted
Software Agent → "GPIO compatibility confirmed"
Safety Agent → "Add redundant interlock"
Research Agent → "Thermal calculations correct"
Hardware Agent → Updates design based on feedback
Safety Agent → "Approved for testing"
```

### Pattern 3: Problem Escalation
```
Software Agent → "Performance issue: 18 FPS"
Integration Agent → Profiles system bottleneck
Research Agent → "MediaPipe lite mode recommended"
Software Agent → Implements optimization
Hardware Agent → "Verified on Pi 4: Now 32 FPS"
Integration Agent → "Issue resolved"
```

## Monitoring Agent Activity

### GitHub Insights

```bash
# View agent issues
gh issue list --label "agent:research"
gh issue list --label "agent:hardware"
gh issue list --label "agent:software"

# View agent activity
gh issue list --search "commenter:github-actions[bot]"

# View workflow runs
gh run list --workflow=agent-system.yml
```

### Agent Performance Metrics

```
┌─────────────┬─────────┬──────────┬──────────┬─────────┐
│   Agent     │ Issues  │ Comments │ PRs      │ Success │
│             │ Handled │ Posted   │ Reviewed │ Rate    │
├─────────────┼─────────┼──────────┼──────────┼─────────┤
│ Research 🔬 │   15    │    47    │    8     │  93%    │
│ Hardware ⚡  │   22    │    65    │   12     │  88%    │
│ Software 💻 │   34    │    98    │   28     │  95%    │
│ Safety 🛡️   │   18    │    54    │   34     │ 100%    │
│ Design 🎨   │    8    │    21    │    5     │  87%    │
│ Integration │   12    │    35    │   34     │  91%    │
└─────────────┴─────────┴──────────┴──────────┴─────────┘
```

## Future Vision

### Phase 1 (Current): Automated Triggering
- ✅ Issue templates trigger agents
- ✅ Agents comment with structured analysis
- ✅ Workflows automate checks
- 🔄 Manual agent review and decisions

### Phase 2 (Next): AI-Powered Agents
- 🎯 GPT-4/Claude integration for intelligent responses
- 🎯 Agents generate code/designs autonomously
- 🎯 Natural language agent interactions
- 🎯 Continuous learning from outcomes

### Phase 3 (Future): Autonomous Development
- 🚀 Agents create PRs independently
- 🚀 Multi-agent debates and voting
- 🚀 Self-improving codebase
- 🚀 Human oversight, agent execution

## Resources

- **Quick Start**: `.github/agents/QUICKSTART.md`
- **Agent Instructions**: `.github/agents/[agent]-agent.md`
- **Workflows**: `.github/workflows/agent-system.yml`
- **Issue Templates**: `.github/ISSUE_TEMPLATE/*.yml`

---

**The future of collaborative development is multi-agent!** 🤖🚀
