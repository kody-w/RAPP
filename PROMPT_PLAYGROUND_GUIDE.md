# Prompt Engineering Playground - User Guide

## Overview

The Prompt Playground Agent is a comprehensive tool for iteratively refining prompts, running A/B tests, tracking performance metrics, and auto-optimizing using genetic algorithms.

## Features

✨ **Iterative Prompt Refinement** - Get AI-powered suggestions to improve your prompts
🔬 **A/B Testing** - Compare multiple prompt variants with real performance data
📊 **Performance Metrics** - Track latency, token usage, and success rates
🧬 **Genetic Optimization** - Automatically evolve better prompts using genetic algorithms
💾 **Experiment Management** - Save, load, and analyze your prompt engineering experiments

## Quick Start

### 1. Create an Experiment

```
Create a new prompt experiment called "Customer Support Optimizer" with these test cases:
- "My order hasn't arrived yet"
- "I need to return this product"
- "Can you help me track my package?"
```

**What happens:**
- Creates a new experiment with a unique ID
- Stores your test cases for consistent evaluation
- Sets up the foundation for comparing different prompts

### 2. Add Prompt Variants

```
Add a variant to experiment [ID] called "Empathetic Helper" with this prompt:
"You are a friendly customer support assistant. Always empathize with the customer's situation and provide clear, actionable solutions."
```

**Add multiple variants:**
```
Add another variant called "Concise Expert" with:
"You are a customer support expert. Provide direct, efficient solutions in 2-3 sentences maximum."
```

### 3. Run A/B Tests

```
Run A/B tests on experiment [ID]
```

**What happens:**
- Tests each variant against all test cases
- Measures latency (response time)
- Tracks token usage (cost proxy)
- Calculates success rates
- Ranks variants by performance

### 4. Get Performance Metrics

```
Show me detailed metrics for experiment [ID]
```

**Metrics include:**
- Average response latency
- Average token usage
- Success rate (% of non-errored responses)
- Total tests executed

### 5. Genetic Optimization

```
Run genetic optimization on experiment [ID] with 15 population size and 7 generations
```

**What happens:**
- Uses existing variants as starting population
- Evaluates fitness (latency + token efficiency)
- Selects best performers
- Creates offspring through crossover
- Applies random mutations
- Repeats for specified generations
- Saves the best evolved prompt as a new variant

### 6. Refine a Prompt

```
Give me suggestions to refine this prompt: "You are a helpful assistant."
```

**Returns:**
- 3 specific, actionable improvements
- Categories of enhancement (clarity, specificity, tone)
- Expert prompt engineering advice

## Complete Workflow Example

### Scenario: Optimizing a Content Summarization Prompt

**Step 1: Create Experiment**
```
Create an experiment called "Article Summarizer" with these test cases:
- "Summarize this article about climate change: [long article text]"
- "Give me a summary of this tech blog post: [blog text]"
- "What are the key points from this research paper: [paper text]"
```

**Step 2: Add Initial Variants**
```
Add variant "Basic Summarizer":
"Summarize the following text in 3 bullet points."

Add variant "Structured Summarizer":
"You are an expert at extracting key information. Provide a summary with:
1. Main Topic
2. Key Points (3-4 bullets)
3. Conclusion/Takeaway"

Add variant "Audience-Focused Summarizer":
"Summarize this text as if explaining to a busy executive who needs to make a decision. Focus on actionable insights and implications."
```

**Step 3: Run A/B Tests**
```
Run A/B tests on experiment [ID]
```

**Results might show:**
- Basic Summarizer: Fast (0.8s) but generic
- Structured Summarizer: Slower (1.2s) but comprehensive
- Audience-Focused: Balanced (0.9s) and actionable

**Step 4: Genetic Optimization**
```
Run genetic optimization with 10 population and 5 generations
```

**Result:**
- Evolved prompt combining best elements:
  "You are an expert at extracting key information. Summarize in 3 bullet points focusing on actionable insights."
- Best of both worlds: structured + concise + actionable

**Step 5: Refine Further**
```
Refine the optimized prompt
```

**AI Suggestions:**
1. **Clarity**: Add expected output format
2. **Specificity**: Define what "actionable" means
3. **Constraint**: Add word/character limit

**Step 6: Final Variant**
```
Add variant "Refined Optimized":
"You are an expert at extracting actionable insights. Provide a 3-bullet summary (max 50 words each) focusing on:
- What happened
- Why it matters
- What to do about it"
```

**Step 7: Export Results**
```
Export results for experiment [ID]
```

## Advanced Use Cases

### 1. Cost Optimization

**Goal:** Reduce token usage while maintaining quality

```
1. Create experiment with complex queries
2. Add variants with different length constraints
3. Run A/B tests
4. Compare avg_tokens metric
5. Select variant with lowest tokens + acceptable quality
```

### 2. Latency Optimization

**Goal:** Minimize response time for user-facing applications

```
1. Create experiment with typical user queries
2. Add variants with different prompt lengths
3. Run A/B tests
4. Sort by avg_latency
5. Deploy fastest variant
```

### 3. Multi-Objective Optimization

**Goal:** Balance cost, speed, and quality

```
1. Create experiment with quality test cases
2. Add diverse variants
3. Run A/B tests
4. Use genetic optimization (fitness balances latency + tokens)
5. Manually review top 3 variants
6. Select best based on business requirements
```

### 4. Persona Testing

**Goal:** Find the best "personality" for your AI

```
Variants to test:
- "You are a friendly, casual assistant"
- "You are a professional, formal expert"
- "You are an enthusiastic, energetic helper"
- "You are a calm, methodical advisor"

Run tests and measure user satisfaction proxy (e.g., response completeness)
```

## Best Practices

### Test Case Design

✅ **DO:**
- Use real user queries from your application
- Include edge cases and challenging scenarios
- Maintain consistency across experiments
- Start with 3-5 test cases, expand to 10-20 for production

❌ **DON'T:**
- Use overly simple test cases
- Mix different use cases in one experiment
- Change test cases mid-experiment
- Rely on a single test case

### Variant Creation

✅ **DO:**
- Start with 2-3 clearly different approaches
- Document the hypothesis behind each variant
- Make one change at a time for controlled testing
- Use descriptive names

❌ **DON'T:**
- Create too many variants initially (hard to analyze)
- Make minor wording changes (unlikely to affect metrics)
- Overcomplicate prompts prematurely

### Genetic Optimization

✅ **DO:**
- Start with good base prompts
- Use population size 10-20 for small experiments
- Run 5-10 generations
- Review evolved prompts manually before deploying

❌ **DON'T:**
- Expect perfect results from random starting points
- Run too many generations (diminishing returns)
- Deploy without human review
- Use genetic optimization as first step

### Metrics Analysis

✅ **DO:**
- Consider all metrics together (latency, tokens, success rate)
- Weight metrics based on your priorities
- Run multiple test rounds for consistency
- Compare against baseline performance

❌ **DON'T:**
- Optimize for single metric only
- Ignore success rate
- Trust results from single test run
- Forget about real-world context

## Command Reference

### create_experiment
```
Action: create_experiment
Required: experiment_name, test_cases
Optional: user_guid
```

### add_variant
```
Action: add_variant
Required: experiment_id, prompt
Optional: variant_name, user_guid
```

### run_ab_test
```
Action: run_ab_test
Required: experiment_id
Optional: user_guid
```

### get_metrics
```
Action: get_metrics
Required: experiment_id
Optional: user_guid
```

### genetic_optimize
```
Action: genetic_optimize
Required: experiment_id
Optional: population_size (default: 10), generations (default: 5), user_guid
```

### list_experiments
```
Action: list_experiments
Optional: user_guid
```

### get_experiment
```
Action: get_experiment
Required: experiment_id
Optional: user_guid
```

### refine_prompt
```
Action: refine_prompt
Required: prompt
Optional: user_guid
```

### export_results
```
Action: export_results
Required: experiment_id
Optional: user_guid
```

## Tips & Tricks

### 1. Start Simple
Don't jump into genetic optimization immediately. Start with 2-3 hand-crafted variants, run A/B tests, and understand what works.

### 2. Use Real Data
Test cases should reflect actual user queries from your application. Synthetic test cases often miss important nuances.

### 3. Iterate in Cycles
1. Create variants
2. Test
3. Analyze
4. Refine
5. Repeat

### 4. Document Everything
Use descriptive names for experiments and variants. Future you will thank present you.

### 5. Leverage AI Refinement
The `refine_prompt` action provides expert suggestions. Use it before creating variants to get ideas.

### 6. Balance Metrics
- **Latency**: Important for user-facing apps
- **Tokens**: Important for cost management
- **Quality**: Most important overall

### 7. Genetic Optimization Sweet Spot
- Population: 10-15
- Generations: 5-7
- More isn't always better

## Troubleshooting

### "No variants to test"
**Solution:** Add at least one variant using `add_variant` before running A/B tests.

### "Experiment not found"
**Solution:** Use `list_experiments` to see available experiment IDs. IDs are case-sensitive.

### "Azure OpenAI client not initialized"
**Solution:** Check that your `local.settings.json` has correct Azure OpenAI credentials.

### High latency in tests
**Solution:** This is expected for complex prompts and long test cases. Consider reducing `max_tokens` or simplifying prompts.

### Genetic optimization not improving
**Solution:**
- Start with better base prompts
- Increase population size
- Run more generations
- Check that fitness function aligns with your goals

## Example Conversation Flow

```
User: I need to optimize a prompt for generating product descriptions

Agent: Great! Let's create a comprehensive prompt optimization experiment for product descriptions. First, I'll create an experiment with some realistic test cases.

[Agent calls PromptPlayground with create_experiment action]

Agent: ✅ Created experiment "Product Description Optimizer" (ID: abc123ef)

Now, let's add your first variant. What style of product description are you looking for?

User: Start with a simple, benefits-focused approach

Agent: Perfect! I'll add that variant.

[Agent calls PromptPlayground with add_variant action]

Agent: ✅ Added variant "Benefits-Focused" with prompt: "Write a compelling product description highlighting the top 3 benefits and include a call-to-action."

Let me also add two alternative approaches for comparison:
1. Feature-focused (technical specs)
2. Storytelling approach (emotional connection)

[Agent adds two more variants]

User: Great! Now run the tests

Agent: Running A/B tests across all variants...

[Agent calls run_ab_test]

Agent: ✅ Test complete! Here are your results:

1. Storytelling: 0.95s latency, 285 tokens
2. Benefits-Focused: 1.1s latency, 245 tokens
3. Feature-Focused: 1.3s latency, 310 tokens

The storytelling approach is fastest, but uses more tokens. The benefits-focused approach has the best balance!

User: Can we optimize this further with genetic algorithms?

Agent: Absolutely! I'll run genetic optimization to evolve an even better prompt.

[Agent calls genetic_optimize]

Agent: 🧬 Genetic optimization complete! The evolved prompt combines the best of all approaches:
"Create an engaging product description that tells a brief story (2 sentences) about the product's impact, lists 3 key benefits, and ends with an actionable CTA. Keep it under 80 words."

This optimized variant achieved 0.88s latency with 240 tokens - best of both worlds!

User: Perfect! Export the results so I can share with my team

[Agent calls export_results]

Agent: ✅ Here's your complete experiment data in JSON format [displays JSON]. You can now implement the optimized prompt in your product description generator!
```

## Integration with RAPP System

The Prompt Playground Agent integrates seamlessly with the Copilot Agent 365 system:

### Via Chat Interface
Simply interact naturally:
```
"Create a prompt experiment for email responses"
"Add a variant that's more formal"
"Run A/B tests and show me which performs better"
```

### Via Power Platform
When integrated with Teams/M365 Copilot, users can:
- Collaborate on prompt experiments
- Share results with team members
- Access experiments from any device
- Leverage Office 365 context for test cases

### Data Storage
- Experiments stored per user GUID in Azure File Storage
- Persistent across sessions
- Shareable via export/import
- Backed up automatically

## Performance Considerations

### API Costs
Each A/B test run consumes OpenAI API tokens:
- **Per variant, per test case**: ~100-500 tokens
- **Example**: 3 variants × 5 test cases = 15 API calls
- **Genetic optimization**: Population_size × generations × test_cases API calls

### Optimization Tips
- Use fewer test cases during development (3-5)
- Expand to more test cases (10-20) for production validation
- Limit genetic optimization to 5-7 generations initially
- Monitor your Azure OpenAI quota

## Security & Privacy

- Experiments stored in user-specific storage (GUID-based)
- No cross-user data sharing unless explicitly exported
- All API calls use your Azure OpenAI credentials
- Test cases may contain sensitive data - review before sharing exports

## Future Enhancements

Potential additions (contributions welcome):
- Quality scoring with human feedback
- Multi-model comparison (GPT-4 vs GPT-3.5)
- Cost calculator and budget tracking
- Scheduled automated testing
- Integration with production metrics
- Team collaboration features
- Prompt version control

## Support & Feedback

For issues, questions, or feature requests related to the Prompt Playground Agent:
1. Check this guide for troubleshooting
2. Review the agent code in `agents/prompt_playground_agent.py`
3. Test with simple experiments first
4. Report issues through your normal RAPP support channels

Happy prompt engineering! 🚀
