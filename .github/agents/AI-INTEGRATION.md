# Adding AI Intelligence to Agents

This guide shows how to make your agents truly autonomous using AI models like GPT-4, Claude, or GitHub Copilot.

## Current State vs. Future State

### Current (Template-Based)
- Agents are structured templates
- Humans follow agent instructions
- Automated triggering and routing
- Manual analysis and responses

### Future (AI-Powered)
- Agents use AI models for reasoning
- Autonomous analysis and recommendations
- Automated code generation
- Human oversight, not execution

## Option 1: GitHub Copilot Integration

### Using GitHub Copilot Chat API

```yaml
# .github/workflows/agent-system.yml
jobs:
  research-agent:
    steps:
      - name: AI-Powered Research Analysis
        run: |
          # Load research agent persona
          PERSONA=$(cat .github/agents/research-agent.md)
          
          # Get issue content
          ISSUE_TITLE="${{ github.event.issue.title }}"
          ISSUE_BODY="${{ github.event.issue.body }}"
          
          # Call GitHub Copilot (when API available)
          RESPONSE=$(gh copilot chat --prompt "
            Context: $PERSONA
            
            Question: $ISSUE_TITLE
            Details: $ISSUE_BODY
            
            Provide evidence-based research analysis.
          ")
          
          # Post response as comment
          gh issue comment ${{ github.event.issue.number }} --body "$RESPONSE"
```

### Current Limitation
GitHub Copilot API for automation is not yet publicly available. Use GPT-4 or Claude instead (Option 2).

## Option 2: OpenAI GPT-4 Integration

### Setup

1. **Get API Key**
   ```bash
   # Sign up at https://platform.openai.com
   # Get API key from API settings
   ```

2. **Add to GitHub Secrets**
   ```bash
   # In your repo:
   Settings → Secrets and variables → Actions → New repository secret
   
   Name: OPENAI_API_KEY
   Value: sk-...your-key...
   ```

3. **Update Workflow**
   ```yaml
   # .github/workflows/agent-system.yml
   jobs:
     research-agent:
       steps:
         - name: AI Research Analysis
           env:
             OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
           run: |
             # Install OpenAI CLI
             pip install openai
             
             # Create Python script
             cat > analyze.py << 'EOF'
             import os
             import openai
             import sys
             
             openai.api_key = os.environ['OPENAI_API_KEY']
             
             # Load agent persona
             with open('.github/agents/research-agent.md', 'r') as f:
                 persona = f.read()
             
             # Get issue details
             issue_title = sys.argv[1]
             issue_body = sys.argv[2]
             
             # Call GPT-4
             response = openai.ChatCompletion.create(
                 model="gpt-4",
                 messages=[
                     {"role": "system", "content": f"You are the Research Agent.\n\n{persona}"},
                     {"role": "user", "content": f"Issue: {issue_title}\n\nDetails: {issue_body}\n\nProvide evidence-based analysis."}
                 ],
                 temperature=0.3,  # Lower = more focused
                 max_tokens=2000
             )
             
             print(response.choices[0].message.content)
             EOF
             
             # Run analysis
             RESPONSE=$(python analyze.py "${{ github.event.issue.title }}" "${{ github.event.issue.body }}")
             
             # Post as comment
             gh issue comment ${{ github.event.issue.number }} --body "🔬 **Research Agent AI Analysis**\n\n$RESPONSE"
   ```

## Option 3: Anthropic Claude Integration

### Setup

1. **Get API Key**
   ```bash
   # Sign up at https://console.anthropic.com
   # Get API key
   ```

2. **Add to GitHub Secrets**
   ```bash
   Name: ANTHROPIC_API_KEY
   Value: sk-ant-...your-key...
   ```

3. **Update Workflow**
   ```yaml
   jobs:
     research-agent:
       steps:
         - name: Claude AI Analysis
           env:
             ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
           run: |
             pip install anthropic
             
             cat > analyze.py << 'EOF'
             import os
             import anthropic
             import sys
             
             client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
             
             # Load agent persona
             with open('.github/agents/research-agent.md', 'r') as f:
                 persona = f.read()
             
             issue_title = sys.argv[1]
             issue_body = sys.argv[2]
             
             # Call Claude
             message = client.messages.create(
                 model="claude-3-opus-20240229",
                 max_tokens=2000,
                 system=f"You are the Research Agent.\n\n{persona}",
                 messages=[
                     {"role": "user", "content": f"Issue: {issue_title}\n\nDetails: {issue_body}\n\nProvide evidence-based analysis."}
                 ]
             )
             
             print(message.content[0].text)
             EOF
             
             RESPONSE=$(python analyze.py "${{ github.event.issue.title }}" "${{ github.event.issue.body }}")
             gh issue comment ${{ github.event.issue.number }} --body "🔬 **Research Agent AI Analysis**\n\n$RESPONSE"
   ```

## Option 4: Local AI Models (Free, Private)

### Using Ollama + Llama 3

1. **Setup Ollama**
   ```bash
   # Install Ollama locally
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Pull Llama 3 model
   ollama pull llama3:70b
   ```

2. **Create Agent Service**
   ```python
   # agent_service.py
   import subprocess
   import json
   
   def query_agent(persona_file, question):
       # Load persona
       with open(persona_file, 'r') as f:
           persona = f.read()
       
       # Build prompt
       prompt = f"""
       {persona}
       
       Question: {question}
       
       Provide detailed, evidence-based analysis following the agent instructions above.
       """
       
       # Call Ollama
       result = subprocess.run(
           ['ollama', 'run', 'llama3:70b', prompt],
           capture_output=True,
           text=True
       )
       
       return result.stdout
   
   # Usage
   response = query_agent('.github/agents/research-agent.md', 'What UV wavelength is best?')
   print(response)
   ```

## Complete Example: AI-Powered Research Agent

```python
# .github/scripts/ai_research_agent.py
import os
import sys
import openai
from typing import Dict, List

class AIResearchAgent:
    def __init__(self, api_key: str):
        openai.api_key = api_key
        
        # Load agent persona
        with open('.github/agents/research-agent.md', 'r') as f:
            self.persona = f.read()
    
    def analyze(self, question: str, context: str = "") -> Dict:
        """Analyze research question using GPT-4."""
        
        prompt = f"""
        Research Question: {question}
        
        Context: {context}
        
        Provide analysis in this format:
        
        ## Research Question
        [Restate clearly]
        
        ## Hypothesis
        [Your hypothesis based on scientific principles]
        
        ## Evidence
        [Key findings from literature - cite sources]
        
        ## Recommendation
        [Clear, actionable recommendation]
        
        ## Trade-offs
        [Pros and cons]
        
        ## Safety Considerations
        [Any safety implications]
        
        ## References
        [Sources cited]
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": self.persona},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=3000
        )
        
        analysis = response.choices[0].message.content
        
        return {
            'analysis': analysis,
            'model': 'gpt-4-turbo',
            'tokens': response.usage.total_tokens
        }
    
    def consult_other_agents(self, analysis: str, agents: List[str]) -> Dict:
        """Get feedback from other agents."""
        
        feedback = {}
        
        for agent in agents:
            persona_file = f'.github/agents/{agent}-agent.md'
            with open(persona_file, 'r') as f:
                agent_persona = f.read()
            
            prompt = f"""
            Research Agent provided this analysis:
            
            {analysis}
            
            Review from your domain perspective. Provide:
            1. Validation of approach
            2. Additional considerations
            3. Concerns or warnings
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": agent_persona},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            feedback[agent] = response.choices[0].message.content
        
        return feedback

# Main execution
if __name__ == "__main__":
    api_key = os.environ.get('OPENAI_API_KEY')
    
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        sys.exit(1)
    
    agent = AIResearchAgent(api_key)
    
    # Analyze question
    question = sys.argv[1] if len(sys.argv) > 1 else "Test question"
    context = sys.argv[2] if len(sys.argv) > 2 else ""
    
    result = agent.analyze(question, context)
    
    print("# Research Agent AI Analysis\n")
    print(result['analysis'])
    print(f"\n\n_Generated by {result['model']} ({result['tokens']} tokens)_")
    
    # Optionally get feedback from other agents
    if '--consult' in sys.argv:
        print("\n\n# Cross-Agent Feedback\n")
        feedback = agent.consult_other_agents(
            result['analysis'],
            ['hardware', 'software', 'safety']
        )
        
        for agent_name, response in feedback.items():
            print(f"\n## {agent_name.title()} Agent Feedback\n")
            print(response)
```

## Advanced: Multi-Agent Debate

```python
# .github/scripts/agent_debate.py
import openai
import os

class AgentDebate:
    def __init__(self, topic: str, agents: list):
        self.topic = topic
        self.agents = agents
        self.history = []
        openai.api_key = os.environ['OPENAI_API_KEY']
    
    def run_round(self, round_num: int):
        """Run one round of debate."""
        
        print(f"\n## Round {round_num}\n")
        
        for agent_name in self.agents:
            # Load agent persona
            with open(f'.github/agents/{agent_name}-agent.md', 'r') as f:
                persona = f.read()
            
            # Build context from debate history
            context = "\n\n".join([
                f"**{entry['agent']}**: {entry['statement']}" 
                for entry in self.history
            ])
            
            prompt = f"""
            Topic: {self.topic}
            
            Previous statements:
            {context}
            
            Now provide your perspective. Consider other agents' points and either:
            1. Support with additional evidence
            2. Raise concerns
            3. Propose compromise
            4. Vote for final decision (if consensus reached)
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": persona},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            
            statement = response.choices[0].message.content
            
            self.history.append({
                'round': round_num,
                'agent': agent_name,
                'statement': statement
            })
            
            print(f"### {agent_name.title()} Agent\n")
            print(statement)
            print()
    
    def check_consensus(self) -> bool:
        """Check if agents reached consensus."""
        # Look for "VOTE:", "CONSENSUS:", "AGREE:" in recent statements
        recent = [entry['statement'].lower() for entry in self.history[-len(self.agents):]]
        vote_count = sum(1 for s in recent if 'vote:' in s or 'consensus' in s)
        return vote_count >= len(self.agents) * 0.75  # 75% consensus
    
    def run_debate(self, max_rounds: int = 3):
        """Run complete debate."""
        print(f"# Multi-Agent Debate: {self.topic}\n")
        print(f"Participants: {', '.join(self.agents)}\n")
        
        for round_num in range(1, max_rounds + 1):
            self.run_round(round_num)
            
            if self.check_consensus():
                print("\n✅ **Consensus Reached!**\n")
                break
        else:
            print("\n⚠️ **No consensus after {max_rounds} rounds. Human decision required.**\n")
        
        return self.history

# Usage
if __name__ == "__main__":
    debate = AgentDebate(
        topic="Should we use 365nm or 405nm UV LEDs?",
        agents=['research', 'hardware', 'software', 'safety']
    )
    
    results = debate.run_debate(max_rounds=3)
```

## Cost Considerations

### GPT-4 Pricing (as of 2024)
- Input: $0.01 per 1K tokens
- Output: $0.03 per 1K tokens
- Average agent response: ~2K tokens = $0.08

### Estimated Monthly Costs
| Usage | Issues/Month | Cost |
|-------|--------------|------|
| Light | 10 | $0.80 |
| Medium | 50 | $4.00 |
| Heavy | 200 | $16.00 |

### Cost Optimization
1. Use GPT-4 only for complex questions
2. Use GPT-3.5 for simple analysis (10x cheaper)
3. Cache common responses
4. Batch similar questions

## Best Practices

### 1. Temperature Settings
```python
# For factual research (Research Agent)
temperature=0.3  # More focused, deterministic

# For creative design (Design Agent)
temperature=0.7  # More creative, varied

# For code generation (Software Agent)
temperature=0.2  # Very precise
```

### 2. Prompt Engineering
```python
# Good prompt structure
prompt = f"""
Role: {agent_persona}

Task: {specific_task}

Context: {relevant_context}

Format: {desired_output_format}

Constraints:
- Must cite sources
- Must quantify recommendations
- Must consider safety
"""
```

### 3. Validation
```python
# Always validate AI responses
def validate_response(response: str) -> bool:
    checks = [
        len(response) > 100,  # Not too short
        '##' in response,  # Has structure
        'source' in response.lower() or 'reference' in response.lower(),  # Has citations
    ]
    return all(checks)
```

## Next Steps

1. **Choose Integration Option**
   - Start with GPT-4 (easiest)
   - Or use Claude (similar)
   - Or local models (free, private)

2. **Test with One Agent**
   - Start with Research Agent
   - Test on real questions
   - Refine prompts

3. **Expand to All Agents**
   - Add AI to Hardware Agent
   - Add AI to Software Agent
   - Enable multi-agent debates

4. **Monitor and Optimize**
   - Track costs
   - Measure accuracy
   - Improve prompts

---

**With AI integration, your agents become truly autonomous!** 🤖✨
