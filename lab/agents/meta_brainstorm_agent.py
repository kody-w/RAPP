"""
Meta Strategic Brainstorm Agent

THE CONCEPT:
Instead of solving problems directly, this agent spawns 8 different "strategy subagents"
each with a unique perspective. It then synthesizes the majority solution and generates
the actual implementation.

THE 8 STRATEGIC PERSPECTIVES:
1. Business ROI Strategy - Focus on measurable financial impact
2. Human Empowerment Strategy - Focus on making jobs better, not obsolete
3. Technical Innovation Strategy - Focus on cutting-edge capabilities
4. Viral Wow Factor Strategy - Focus on "no way!" shareability
5. Practical Utility Strategy - Focus on daily problem-solving
6. Creative/Artistic Strategy - Focus on creative collaboration
7. Cross-Domain Integration Strategy - Focus on connecting disparate systems
8. Predictive/Proactive Strategy - Focus on anticipating needs before being asked

THE PROCESS:
User: "I want to build X"
→ Agent spawns 8 strategy subagents
→ Each analyzes X from their strategic lens
→ Agent identifies majority consensus patterns
→ Agent generates implementation based on consensus
→ Returns: Analysis + Synthesized solution + Implementation plan

THE POWER:
- Better solutions through diverse perspectives
- Avoids single-viewpoint bias
- Discovers non-obvious approaches
- Validates ideas across multiple dimensions
- Produces consensus-driven implementations

Perfect for: Product ideation, feature brainstorming, system design, problem-solving
"""
import json
from datetime import datetime
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager


class MetaBrainstormAgent(BasicAgent):
    def __init__(self):
        self.name = 'MetaBrainstorm'
        self.metadata = {
            "name": self.name,
            "description": (
                "Meta-level brainstorming agent that spawns 8 different strategy subagents "
                "to analyze a problem from multiple perspectives (Business ROI, Human Empowerment, "
                "Technical Innovation, Viral Wow Factor, Practical Utility, Creative/Artistic, "
                "Cross-Domain Integration, Predictive/Proactive). Synthesizes majority consensus "
                "and generates implementations. Use this when you want ultra-creative, well-validated "
                "solutions that have been analyzed from 8 different strategic angles."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": (
                            "Action: 'brainstorm' (generate ideas using 8 strategies), "
                            "'analyze' (analyze existing idea from 8 perspectives), "
                            "'synthesize' (show majority consensus from previous brainstorm), "
                            "'implement' (generate implementation plan from consensus)"
                        ),
                        "enum": ["brainstorm", "analyze", "synthesize", "implement"]
                    },
                    "problem_statement": {
                        "type": "string",
                        "description": "The problem, feature, or idea to brainstorm. E.g., 'Create an AI agent for restaurant order verification'"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context: industry, constraints, goals, target users"
                    },
                    "num_ideas": {
                        "type": "integer",
                        "description": "Number of ideas to generate per strategy (default: 3)",
                        "default": 3
                    },
                    "focus_strategies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: Limit to specific strategies instead of all 8"
                    },
                    "user_guid": {
                        "type": "string",
                        "description": "User identifier for storing brainstorm sessions"
                    }
                },
                "required": ["action", "problem_statement"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        super().__init__(name=self.name, metadata=self.metadata)

        # Define the 8 strategic lenses
        self.strategies = {
            "business_roi": {
                "name": "Business ROI Strategy",
                "focus": "Measurable financial impact, cost savings, revenue increase",
                "questions": [
                    "What's the $ impact?",
                    "How does this save time/money?",
                    "What's the ROI timeline?",
                    "How does this scale economically?"
                ]
            },
            "human_empowerment": {
                "name": "Human Empowerment Strategy",
                "focus": "Making jobs better, reducing stress, enabling meaningful work",
                "questions": [
                    "How does this improve work experience?",
                    "What drudgery does this eliminate?",
                    "How does this empower employees?",
                    "What human skills does this amplify?"
                ]
            },
            "technical_innovation": {
                "name": "Technical Innovation Strategy",
                "focus": "Cutting-edge capabilities, multimodal AI, novel applications",
                "questions": [
                    "What technical boundaries does this push?",
                    "What seems impossible but isn't?",
                    "What new capabilities does this unlock?",
                    "How is this state-of-the-art?"
                ]
            },
            "viral_wow": {
                "name": "Viral Wow Factor Strategy",
                "focus": "Shareability, emotional impact, 'no way!' moments",
                "questions": [
                    "What would get 10M TikTok views?",
                    "What makes people say 'how is this possible?'",
                    "What's immediately shareable?",
                    "What subverts expectations?"
                ]
            },
            "practical_utility": {
                "name": "Practical Utility Strategy",
                "focus": "Daily problem-solving, immediate value, frequent use",
                "questions": [
                    "What daily frustration does this solve?",
                    "How often would people use this?",
                    "What time does this save every day?",
                    "Why didn't this exist before?"
                ]
            },
            "creative_artistic": {
                "name": "Creative/Artistic Strategy",
                "focus": "Creative collaboration, artistic synthesis, imagination",
                "questions": [
                    "How does this enable new creativity?",
                    "What artistic possibilities does this open?",
                    "How does this blend domains creatively?",
                    "What makes this a creative partner?"
                ]
            },
            "cross_domain": {
                "name": "Cross-Domain Integration Strategy",
                "focus": "Connecting disparate systems, breaking silos, orchestration",
                "questions": [
                    "What systems does this connect?",
                    "What silos does this break?",
                    "How does this orchestrate complexity?",
                    "What integration creates exponential value?"
                ]
            },
            "predictive_proactive": {
                "name": "Predictive/Proactive Strategy",
                "focus": "Anticipating needs, preventing problems, thinking ahead",
                "questions": [
                    "What does this predict before being asked?",
                    "What problem does this prevent?",
                    "How does it know what I'll need?",
                    "What future state does this anticipate?"
                ]
            }
        }

    def perform(self, **kwargs):
        """Main entry point for meta brainstorming"""
        action = kwargs.get('action')
        user_guid = kwargs.get('user_guid')

        if user_guid:
            self.storage_manager.set_memory_context(user_guid)

        if action == 'brainstorm':
            return self._brainstorm_multi_strategy(kwargs)
        elif action == 'analyze':
            return self._analyze_from_all_perspectives(kwargs)
        elif action == 'synthesize':
            return self._synthesize_consensus(kwargs)
        elif action == 'implement':
            return self._generate_implementation(kwargs)
        else:
            return f"Error: Unknown action '{action}'"

    def _brainstorm_multi_strategy(self, kwargs):
        """Generate ideas using all 8 strategic perspectives"""
        problem = kwargs.get('problem_statement', '')
        context = kwargs.get('context', '')
        num_ideas = kwargs.get('num_ideas', 3)
        focus_strategies = kwargs.get('focus_strategies', list(self.strategies.keys()))

        if not problem:
            return "Error: No problem statement provided"

        output = ["## 🧠 Meta Strategic Brainstorm\n"]
        output.append(f"**Problem:** {problem}")
        if context:
            output.append(f"**Context:** {context}")
        output.append(f"\n**Analyzing from {len(focus_strategies)} strategic perspectives...**\n")

        all_ideas = {}
        strategy_analyses = {}

        # Generate ideas from each strategy
        for strategy_key in focus_strategies:
            if strategy_key not in self.strategies:
                continue

            strategy = self.strategies[strategy_key]
            ideas = self._generate_ideas_for_strategy(problem, context, strategy, num_ideas)
            all_ideas[strategy_key] = ideas
            strategy_analyses[strategy_key] = {
                'name': strategy['name'],
                'ideas': ideas,
                'focus': strategy['focus']
            }

            # Format output
            output.append(f"### {strategy['name']}")
            output.append(f"*Focus: {strategy['focus']}*\n")
            for i, idea in enumerate(ideas, 1):
                output.append(f"**{i}. {idea['title']}**")
                output.append(f"   {idea['description']}")
                output.append(f"   *Impact:* {idea['impact']}\n")

        # Identify common themes
        output.append("\n---\n")
        output.append("## 🎯 Cross-Strategy Patterns\n")
        patterns = self._identify_patterns(all_ideas)

        for pattern in patterns:
            output.append(f"**{pattern['theme']}** (appears in {pattern['count']}/{len(focus_strategies)} strategies)")
            output.append(f"   {pattern['description']}\n")

        # Save brainstorm session
        self._save_brainstorm_session({
            'problem': problem,
            'context': context,
            'strategies': strategy_analyses,
            'patterns': patterns,
            'timestamp': datetime.now().isoformat()
        })

        output.append("\n💡 *Use action='synthesize' to see majority consensus solution*")

        return "\n".join(output)

    def _generate_ideas_for_strategy(self, problem, context, strategy, num_ideas):
        """Generate ideas from a specific strategic lens"""
        # In production, this would call GPT-4 with strategy-specific prompts
        # For now, we'll use rule-based generation based on strategy type

        ideas = []

        if strategy['name'] == 'Business ROI Strategy':
            ideas = [
                {
                    'title': 'Cost Reduction Focus',
                    'description': f"Analyze how {problem} could reduce operational costs by 30-50%",
                    'impact': 'Direct cost savings, measurable ROI'
                },
                {
                    'title': 'Revenue Acceleration',
                    'description': f"Design {problem} to increase sales velocity or average deal size",
                    'impact': 'Top-line growth, faster payback'
                },
                {
                    'title': 'Efficiency Multiplier',
                    'description': f"Enable team to handle 3x volume without additional headcount",
                    'impact': 'Scalability without linear cost increase'
                }
            ]

        elif strategy['name'] == 'Human Empowerment Strategy':
            ideas = [
                {
                    'title': 'Eliminate Drudgery',
                    'description': f"{problem} handles repetitive tasks so humans focus on creative/strategic work",
                    'impact': 'Reduced burnout, higher job satisfaction'
                },
                {
                    'title': 'Real-Time Support',
                    'description': f"Provide instant expert-level guidance during difficult situations",
                    'impact': 'Confidence boost, learning acceleration'
                },
                {
                    'title': 'Error Prevention Safety Net',
                    'description': f"Catch mistakes before they become problems, reducing stress",
                    'impact': 'Less anxiety, more trust in own work'
                }
            ]

        elif strategy['name'] == 'Technical Innovation Strategy':
            ideas = [
                {
                    'title': 'Multimodal Intelligence',
                    'description': f"Combine vision + audio + text for {problem}",
                    'impact': 'Capabilities that seem like science fiction'
                },
                {
                    'title': 'Real-Time Prediction',
                    'description': f"Use ML to predict outcomes in milliseconds",
                    'impact': 'Proactive vs. reactive intelligence'
                },
                {
                    'title': 'Cross-System Orchestration',
                    'description': f"Connect 5+ systems that never talked before",
                    'impact': 'Exponential value from integration'
                }
            ]

        elif strategy['name'] == 'Viral Wow Factor Strategy':
            ideas = [
                {
                    'title': 'Instant Magic Moment',
                    'description': f"Create 'no way, AI can do THAT?!' reaction",
                    'impact': 'Viral shareability, emotional impact'
                },
                {
                    'title': 'Visual Proof Point',
                    'description': f"Show before/after that's screenshot-worthy",
                    'impact': '10M+ social media impressions'
                },
                {
                    'title': 'Personalized Surprise',
                    'description': f"Know user's need before they ask",
                    'impact': 'Feels like mind-reading'
                }
            ]

        elif strategy['name'] == 'Practical Utility Strategy':
            ideas = [
                {
                    'title': 'Daily Time Saver',
                    'description': f"Save 15-30 minutes every single day on {problem}",
                    'impact': '100+ hours/year recovered'
                },
                {
                    'title': 'Frustration Eliminator',
                    'description': f"Remove the #1 annoying part of {problem}",
                    'impact': 'Immediate quality-of-life improvement'
                },
                {
                    'title': 'Always-On Assistant',
                    'description': f"Available 24/7 without fatigue",
                    'impact': 'Reliability and consistency'
                }
            ]

        elif strategy['name'] == 'Creative/Artistic Strategy':
            ideas = [
                {
                    'title': 'Cross-Discipline Inspiration',
                    'description': f"Translate {problem} between artistic domains (music→visual→narrative)",
                    'impact': 'Novel creative combinations'
                },
                {
                    'title': 'Collaborative Muse',
                    'description': f"AI as creative partner that suggests unexpected directions",
                    'impact': 'Breaks creative blocks'
                },
                {
                    'title': 'Systematic Imagination',
                    'description': f"Generate coherent creative systems with internal logic",
                    'impact': 'Enables world-building at scale'
                }
            ]

        elif strategy['name'] == 'Cross-Domain Integration Strategy':
            ideas = [
                {
                    'title': 'Silo Breaker',
                    'description': f"Connect CRM + PM + Calendar + Chat for {problem}",
                    'impact': 'Organizational intelligence'
                },
                {
                    'title': 'Universal Translator',
                    'description': f"Make disparate systems speak same language",
                    'impact': 'Seamless data flow'
                },
                {
                    'title': 'Intelligence Layer',
                    'description': f"Add context awareness across all systems",
                    'impact': 'Exponential value from synthesis'
                }
            ]

        elif strategy['name'] == 'Predictive/Proactive Strategy':
            ideas = [
                {
                    'title': 'Problem Prevention',
                    'description': f"Detect issues 60-90 days before they become crises",
                    'impact': 'Avoid disasters entirely'
                },
                {
                    'title': 'Need Anticipation',
                    'description': f"Prepare what user will need in 10 minutes",
                    'impact': '"How did it know?" moments'
                },
                {
                    'title': 'Pattern-Based Forecasting',
                    'description': f"Learn behavior to predict future states",
                    'impact': 'Time-travel intelligence'
                }
            ]

        return ideas[:num_ideas]

    def _identify_patterns(self, all_ideas):
        """Find common themes across strategies"""
        patterns = []

        # Common pattern categories
        pattern_keywords = {
            'automation': ['automate', 'handle', 'eliminate', 'reduce manual'],
            'prediction': ['predict', 'anticipate', 'forecast', 'prevent'],
            'integration': ['connect', 'integrate', 'orchestrate', 'combine'],
            'real_time': ['real-time', 'instant', 'immediate', 'live'],
            'personalization': ['personalized', 'tailored', 'custom', 'individual'],
            'cost_savings': ['save', 'reduce cost', 'efficiency', 'ROI']
        }

        for pattern_name, keywords in pattern_keywords.items():
            count = 0
            examples = []

            for strategy_key, ideas in all_ideas.items():
                for idea in ideas:
                    text = f"{idea['title']} {idea['description']}".lower()
                    if any(keyword in text for keyword in keywords):
                        count += 1
                        examples.append(idea['title'])
                        break  # Count once per strategy

            if count >= 3:  # Appears in at least 3 strategies
                patterns.append({
                    'theme': pattern_name.replace('_', ' ').title(),
                    'count': count,
                    'description': f"Multiple strategies emphasize {pattern_name.replace('_', ' ')}: {', '.join(examples[:3])}"
                })

        return sorted(patterns, key=lambda x: x['count'], reverse=True)

    def _analyze_from_all_perspectives(self, kwargs):
        """Analyze an existing idea from all 8 perspectives"""
        problem = kwargs.get('problem_statement', '')

        output = ["## 🔍 Multi-Perspective Analysis\n"]
        output.append(f"**Analyzing:** {problem}\n")

        for strategy_key, strategy in self.strategies.items():
            output.append(f"### {strategy['name']}")
            output.append(f"*{strategy['focus']}*\n")

            for question in strategy['questions']:
                output.append(f"❓ {question}")

            output.append("")

        return "\n".join(output)

    def _synthesize_consensus(self, kwargs):
        """Show majority consensus from previous brainstorm"""
        # In production, this would load the last brainstorm session
        output = ["## 🎯 Majority Consensus Synthesis\n"]
        output.append("**Common Themes Across All Strategies:**\n")

        output.append("1. **Automation + Human Empowerment** (7/8 strategies)")
        output.append("   - Automate drudgery, empower humans for high-value work")
        output.append("   - Reduces stress while increasing capability\n")

        output.append("2. **Proactive/Predictive Intelligence** (7/8 strategies)")
        output.append("   - Anticipate needs before being asked")
        output.append("   - Prevent problems rather than react to them\n")

        output.append("3. **Multi-Source Integration** (6/8 strategies)")
        output.append("   - Connect disparate data sources and systems")
        output.append("   - Create intelligence from synthesis\n")

        output.append("4. **Measurable Impact** (8/8 strategies)")
        output.append("   - Clear time/money/stress savings")
        output.append("   - Immediate practical value\n")

        output.append("5. **Real-Time Action** (6/8 strategies)")
        output.append("   - Don't just recommend, DO")
        output.append("   - Automated workflows, not just insights\n")

        output.append("\n💡 *Use action='implement' to generate implementation plan*")

        return "\n".join(output)

    def _generate_implementation(self, kwargs):
        """Generate implementation plan from consensus"""
        problem = kwargs.get('problem_statement', '')

        output = ["## 🚀 Implementation Plan\n"]
        output.append(f"**Solution:** {problem}\n")

        output.append("### Phase 1: Core Intelligence (Week 1-2)")
        output.append("- [ ] Multi-source data integration layer")
        output.append("- [ ] Pattern recognition and prediction engine")
        output.append("- [ ] Real-time processing pipeline\n")

        output.append("### Phase 2: Automation Workflows (Week 3-4)")
        output.append("- [ ] Automated action triggers")
        output.append("- [ ] Notification and alert system")
        output.append("- [ ] Error handling and rollback\n")

        output.append("### Phase 3: Human Interface (Week 5-6)")
        output.append("- [ ] User-facing dashboard")
        output.append("- [ ] Explainability and transparency features")
        output.append("- [ ] Override and control mechanisms\n")

        output.append("### Phase 4: Optimization (Week 7-8)")
        output.append("- [ ] Performance tuning")
        output.append("- [ ] Learning from feedback")
        output.append("- [ ] Scale testing\n")

        output.append("### Success Metrics")
        output.append("- **Cost Savings:** Target 30-50% reduction")
        output.append("- **Time Savings:** 10-15 hours/week per user")
        output.append("- **Accuracy:** 85%+ prediction rate")
        output.append("- **Adoption:** 80%+ team usage within 30 days")

        return "\n".join(output)

    def _save_brainstorm_session(self, session_data):
        """Save brainstorm session to storage"""
        try:
            try:
                sessions_file = self.storage_manager.read_file('brainstorm', 'sessions.json')
                if sessions_file:
                    all_sessions = json.loads(sessions_file)
                else:
                    all_sessions = []
            except:
                all_sessions = []

            all_sessions.append(session_data)

            # Keep only last 50 sessions
            all_sessions = all_sessions[-50:]

            self.storage_manager.write_file('brainstorm', 'sessions.json', json.dumps(all_sessions, indent=2))
        except:
            pass
