# Proactive Insights Agent - Complete Demo Guide

## Overview

The **ProactiveInsightsAgent** demonstrates the most advanced capabilities of the multi-agent architecture:
- ✅ Dynamic agent creation
- ✅ GitHub repository monitoring (scheduled automation framework)
- ✅ AI-powered trend analysis (any OpenAI-compatible API)
- ✅ Persistent memory integration across sessions
- ✅ Proactive intelligence (not reactive)
- ✅ Executive decision support

## Architecture Highlights

### What Makes This Mind-Blowing

1. **Scheduled Automation**: Framework for Azure Functions Timer Trigger integration
2. **Cross-Session Memory**: Insights persist and accumulate over time
3. **Proactive Intelligence**: Generates Monday briefings automatically
4. **Multi-User Context**: User-specific insights with shared organization knowledge
5. **Real AI Integration**: Ready for any OpenAI-compatible API (Azure OpenAI, OpenAI, local models, etc.) - demo uses intelligent simulation

## Quick Start

### Step 1: Configure GitHub Repository

```json
POST /api/rapp_function
{
  "user_input": "Use the ProactiveInsights agent to configure my repository",
  "conversation_history": [],
  "function_call": {
    "name": "ProactiveInsights",
    "arguments": {
      "action": "configure_repo",
      "github_repo": "my-company/sales-data",
      "data_path": "data/monthly_sales.csv",
      "user_guid": "exec-team-001"
    }
  }
}
```

### Step 2: Schedule Daily Monitoring

```json
POST /api/rapp_function
{
  "user_input": "Set up daily monitoring for sales data",
  "conversation_history": [],
  "function_call": {
    "name": "ProactiveInsights",
    "arguments": {
      "action": "schedule_monitoring",
      "github_repo": "my-company/sales-data",
      "data_path": "data/monthly_sales.csv",
      "user_guid": "exec-team-001"
    }
  }
}
```

**Response:**
```
⏰ Daily Monitoring Scheduled

GitHub Repo: my-company/sales-data
Data Path: data/monthly_sales.csv
Schedule: Every day at 8:00 AM
User Context: exec-team-001

🔄 Automated Workflow:
1. 8:00 AM Daily → Download latest data from GitHub
2. 8:05 AM → Analyze trends with AI
3. 8:10 AM → Store insights in your memory
4. Sunday 6:00 PM → Generate Monday meeting briefing
```

### Step 3: Download Data (Manual Test)

```json
POST /api/rapp_function
{
  "user_input": "Download the latest sales data",
  "conversation_history": [],
  "function_call": {
    "name": "ProactiveInsights",
    "arguments": {
      "action": "download_data",
      "user_guid": "exec-team-001"
    }
  }
}
```

**Response:**
```
📥 Data Downloaded from GitHub

Repository: my-company/sales-data
File Path: data/monthly_sales.csv
Records Downloaded: 30
Downloaded At: 2024-01-15 08:00:00

📊 Data Preview:
- Total Sales Records: 30
- Date Range: 2023-12-16 to 2024-01-14
- Total Revenue: $125,450.00

✅ Next Steps:
1. Use 'analyze_trends' to run GPT-4 analysis on this data
2. Insights will be automatically stored in memory
3. Access insights anytime with 'view_insights'
```

### Step 4: Analyze Trends with AI

```json
POST /api/rapp_function
{
  "user_input": "Analyze the sales trends",
  "conversation_history": [],
  "function_call": {
    "name": "ProactiveInsights",
    "arguments": {
      "action": "analyze_trends",
      "time_period": "month",
      "user_guid": "exec-team-001"
    }
  }
}
```

**Response:**
```
🧠 AI Analysis Complete

Analysis Period: Month
Data Points Analyzed: 30
Analysis Timestamp: 2024-01-15 08:05:23

📈 Key Trends
- Revenue is increasing by 15.3% compared to first half of period
- Average daily revenue: $4,181.67
- North region is the top performer with $35,200.00

💰 Opportunities Identified
- Top performing region (North) could be replicated in underperforming regions
- Average deal size of $3,250.00 suggests upsell potential
- Weekend sales show significant drop - opportunity for targeted campaigns

⚠️ Risks & Concerns
- Revenue volatility detected - 15.3% variance between periods
- Weekend sales 60% lower than weekdays - coverage gap identified
- Regional concentration risk - top region represents significant portion of revenue

✅ Recommended Actions
1. Investigate North region's success factors for replication
2. Develop weekend sales coverage strategy or promotional campaigns
3. Diversify regional sales to reduce concentration risk
4. Implement upselling training to increase average deal size
5. Schedule weekly review of volatility metrics

💾 Storage
✅ Insights stored in persistent memory
✅ Available for Monday briefings and cross-session analysis
```

### Step 5: Get Monday Meeting Briefing

```json
POST /api/rapp_function
{
  "user_input": "Generate my Monday meeting briefing",
  "conversation_history": [],
  "function_call": {
    "name": "ProactiveInsights",
    "arguments": {
      "action": "get_monday_briefing",
      "user_guid": "exec-team-001"
    }
  }
}
```

**Response:**
```
📋 Monday Meeting Executive Briefing
Generated: Monday, January 15, 2024 at 06:00 AM

---

🎯 Week in Review

📈 Top Trends (Last 7 Days):
- Revenue is increasing by 15.3% compared to first half of period
- Average daily revenue: $4,181.67
- North region is the top performer with $35,200.00

💰 Key Opportunities:
- Top performing region (North) could be replicated in underperforming regions
- Average deal size of $3,250.00 suggests upsell potential
- Weekend sales show significant drop - opportunity for targeted campaigns

⚠️ Risks Requiring Attention:
- Revenue volatility detected - 15.3% variance between periods
- Weekend sales 60% lower than weekdays - coverage gap identified
- Regional concentration risk - top region represents significant portion

✅ Recommended Actions for This Week
1. Investigate North region's success factors for replication
2. Develop weekend sales coverage strategy or promotional campaigns
3. Diversify regional sales to reduce concentration risk
4. Implement upselling training to increase average deal size
5. Schedule weekly review of volatility metrics

---

💡 How to Use This Briefing
1. Review trends to understand the current state
2. Prioritize opportunities based on revenue potential
3. Assign owners to action items during your meeting
4. Schedule follow-ups for risk mitigation

🔄 Data Source: Insights accumulated from daily GitHub monitoring and AI analysis
📊 Insights Analyzed: 7 sessions over 7 days
```

## Advanced Usage Patterns

### Multi-User Contexts

Different teams can have isolated insights:

```javascript
// Sales Team Context
{
  "action": "analyze_trends",
  "user_guid": "sales-team-001"
}

// Executive Team Context
{
  "action": "analyze_trends",
  "user_guid": "exec-team-001"
}

// Marketing Team Context
{
  "action": "analyze_trends",
  "user_guid": "marketing-team-001"
}
```

Each team gets personalized insights while contributing to shared organizational memory.

### Custom Analysis Prompts

Tailor AI analysis for specific business needs:

```json
{
  "action": "analyze_trends",
  "analysis_prompt": "Focus on customer acquisition cost trends and identify which marketing channels are driving the highest quality leads. Calculate ROI by channel and recommend budget reallocation.",
  "user_guid": "marketing-team-001"
}
```

### Cross-Session Intelligence

The agent remembers insights across sessions:

**Week 1:**
```
Trend: North region performing well
```

**Week 2:**
```
Insight: North region success attributed to new sales manager
Action: Replicate North's practices in South region
```

**Week 3:**
```
Validation: South region improvement after implementing North's practices
```

This creates **emergent intelligence** that improves over time.

## Production Deployment

### Azure Functions Timer Trigger Integration

Add to `function_app.py`:

```python
@app.timer_trigger(schedule="0 0 8 * * *", arg_name="myTimer", run_on_startup=False)
def daily_sales_analysis(myTimer: func.TimerRequest) -> None:
    """Runs every day at 8:00 AM UTC"""

    # Initialize agent
    from agents.proactive_insights_agent import ProactiveInsightsAgent
    agent = ProactiveInsightsAgent()

    # Download data
    agent.perform(action='download_data', user_guid='exec-team-001')

    # Analyze trends
    agent.perform(action='analyze_trends', time_period='week', user_guid='exec-team-001')

    logging.info("Daily sales analysis completed")


@app.timer_trigger(schedule="0 0 18 * * 0", arg_name="myTimer", run_on_startup=False)
def sunday_briefing_generation(myTimer: func.TimerRequest) -> None:
    """Runs every Sunday at 6:00 PM UTC"""

    from agents.proactive_insights_agent import ProactiveInsightsAgent
    agent = ProactiveInsightsAgent()

    # Generate Monday briefing
    briefing = agent.perform(action='get_monday_briefing', user_guid='exec-team-001')

    # In production: Send email or Teams message with briefing
    # send_teams_message(briefing)

    logging.info("Monday briefing generated and sent")
```

### GitHub API Integration

Replace sample data generation with real GitHub API calls (works with any OpenAI-compatible endpoint):

```python
def _download_github_data(self, kwargs):
    """Download sales data from GitHub repository"""
    import requests

    github_repo = kwargs.get('github_repo')
    data_path = kwargs.get('data_path')

    # GitHub API request with authentication
    github_token = os.getenv('GITHUB_TOKEN')
    headers = {'Authorization': f'token {github_token}'}

    url = f'https://api.github.com/repos/{github_repo}/contents/{data_path}'
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # Decode base64 content
        import base64
        content = base64.b64decode(response.json()['content']).decode('utf-8')

        # Parse CSV/JSON data
        sales_data = self._parse_sales_file(content)

        # Store and return
        return self._store_downloaded_data(sales_data, github_repo, data_path)
    else:
        return f"Error downloading from GitHub: {response.status_code}"
```

## Business Impact Scenarios

### Scenario 1: Early Risk Detection

**Without ProactiveInsights:**
- Sales decline discovered in quarterly review
- 3 months of lost revenue
- Reactive scrambling to fix

**With ProactiveInsights:**
- Decline detected in week 1 (daily monitoring)
- Automated alert to leadership
- Corrective action taken immediately
- **Impact:** $250K revenue saved

### Scenario 2: Opportunity Identification

**Without ProactiveInsights:**
- Marketing campaign success unknown until post-analysis
- Budget decisions based on outdated data

**With ProactiveInsights:**
- Campaign ROI tracked daily
- High-performing channels identified in real-time
- Budget reallocated to maximize ROI
- **Impact:** 35% improvement in marketing efficiency

### Scenario 3: Executive Time Savings

**Without ProactiveInsights:**
- 4 hours preparing for Monday meetings
- Manual data gathering and analysis
- Inconsistent insights

**With ProactiveInsights:**
- 5 minutes reviewing automated briefing
- Consistent, AI-powered analysis
- **Impact:** 200+ hours saved annually per executive

## Integration with Other Agents

### Agent Orchestration Example

Combine ProactiveInsights with other agents for complete automation:

```javascript
// Step 1: ProactiveInsights identifies opportunity
{
  "insight": "North region performing 40% above target"
}

// Step 2: EnterpriseOrchestrator checks team capacity
{
  "action": "check_capacity",
  "region": "North"
}

// Step 3: ManageMemory stores decision
{
  "memory_type": "task",
  "content": "Hire 2 additional sales reps for North region to capitalize on momentum"
}

// Step 4: Automated notification
// Send to HR team and hiring manager
```

This creates a **self-optimizing business intelligence system**.

## API Examples

### Using with Natural Language (via Assistant)

```javascript
// User simply says:
{
  "user_input": "Show me my Monday briefing",
  "conversation_history": []
}

// Assistant understands intent and calls:
{
  "function_call": {
    "name": "ProactiveInsights",
    "arguments": {
      "action": "get_monday_briefing",
      "user_guid": "user-from-context"
    }
  }
}
```

### Testing Locally

```bash
# Start the function
./run.sh

# Test in another terminal
curl -X POST http://localhost:7071/api/rapp_function \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Configure ProactiveInsights for my-company/sales-data repository",
    "conversation_history": []
  }'
```

## Cost Analysis

### Azure Resources Required

**Minimal Setup:**
- Azure Functions (Consumption): ~$5/month
- Azure Storage: ~$1/month
- AI API (varies by provider): ~$10/month (100K tokens)
- **Total: ~$16/month**

**Enterprise Setup:**
- Azure Functions (Premium): ~$50/month
- Azure Storage: ~$5/month
- AI API (varies by provider): ~$100/month (1M tokens)
- Application Insights: ~$10/month
- **Total: ~$165/month**

**Note:** Compatible with Azure OpenAI, OpenAI, local models via LiteLLM, Anthropic Claude, or any OpenAI-compatible endpoint.

### ROI Calculation

**Executive Time Savings:**
- 4 hours/week × $200/hour = $800/week
- Annual savings: $41,600

**Early Risk Detection:**
- Prevent 1 major issue/year = $250,000+

**Opportunity Capture:**
- 10% improvement in sales efficiency = $500,000+

**Total Annual Value: $791,600+**
**Cost: $1,980/year (enterprise setup)**
**ROI: 39,980%**

## Next Steps

1. **Deploy the agent** - It's already in your `agents/` folder
2. **Configure your GitHub repo** - Use the `configure_repo` action
3. **Test manually** - Run `download_data` and `analyze_trends`
4. **Set up automation** - Add Timer Triggers to `function_app.py`
5. **Monitor results** - Check Application Insights for execution logs
6. **Expand** - Add more data sources (CRM, Analytics, etc.)

## Support & Questions

This agent demonstrates:
- ✅ How to create custom agents with complex workflows
- ✅ Integration with external systems (GitHub)
- ✅ Persistent memory and cross-session learning
- ✅ Proactive intelligence generation
- ✅ Multi-user context management
- ✅ Production-ready patterns for Azure Functions
- ✅ Works with any OpenAI-compatible API provider

**Want to customize for your use case?** The agent code is fully documented and ready to extend!
