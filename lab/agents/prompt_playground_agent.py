"""
Prompt Engineering Playground Agent

This agent provides a comprehensive prompt engineering environment with:
- Iterative prompt refinement
- A/B testing across multiple prompt variants
- Performance metrics tracking (latency, tokens, quality)
- Genetic algorithm-based optimization
- Experiment management and analysis

Usage:
1. Create an experiment with test cases
2. Add prompt variants to test
3. Run A/B tests to compare performance
4. Use genetic optimization to evolve better prompts
5. Analyze results and export findings
"""

import json
import uuid
import time
import random
import re
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager
from openai import AzureOpenAI


class PromptPlaygroundAgent(BasicAgent):
    def __init__(self):
        self.name = 'PromptPlayground'
        self.metadata = {
            "name": self.name,
            "description": """Prompt engineering playground for iterative prompt refinement, A/B testing,
            performance tracking, and genetic algorithm optimization. Create experiments, test variants,
            and auto-optimize prompts for your use cases.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": """Action to perform. Options:
                        - 'create_experiment': Start a new prompt engineering experiment
                        - 'add_variant': Add a new prompt variant to an experiment
                        - 'run_ab_test': Execute A/B tests on prompt variants
                        - 'get_metrics': Retrieve performance metrics
                        - 'genetic_optimize': Use genetic algorithms to evolve prompts
                        - 'list_experiments': Show all experiments
                        - 'get_experiment': Get detailed results from an experiment
                        - 'refine_prompt': Get AI-powered suggestions to improve a prompt
                        - 'export_results': Export experiment data as JSON""",
                        "enum": ["create_experiment", "add_variant", "run_ab_test",
                                "get_metrics", "genetic_optimize", "list_experiments",
                                "get_experiment", "refine_prompt", "export_results"]
                    },
                    "experiment_id": {
                        "type": "string",
                        "description": "Unique identifier for the experiment (required for most actions)"
                    },
                    "experiment_name": {
                        "type": "string",
                        "description": "Name for the experiment (required for create_experiment)"
                    },
                    "test_cases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of test inputs to evaluate prompts against (for create_experiment)"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "The prompt text to test or refine"
                    },
                    "variant_name": {
                        "type": "string",
                        "description": "Name for the prompt variant (for add_variant)"
                    },
                    "population_size": {
                        "type": "integer",
                        "description": "Number of prompt variants in genetic algorithm population (default: 10)"
                    },
                    "generations": {
                        "type": "integer",
                        "description": "Number of generations for genetic optimization (default: 5)"
                    },
                    "user_guid": {
                        "type": "string",
                        "description": "User GUID for personalized experiment storage"
                    }
                },
                "required": ["action"]
            }
        }
        self.storage_manager = AzureFileStorageManager()

        # Initialize Azure OpenAI client
        try:
            self.client = AzureOpenAI(
                api_key=os.environ['AZURE_OPENAI_API_KEY'],
                api_version=os.environ.get('AZURE_OPENAI_API_VERSION', '2024-02-15-preview'),
                azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT']
            )
            self.deployment_name = os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o')
        except Exception as e:
            self.client = None
            self.deployment_name = None

        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        """Main entry point for the agent"""
        action = kwargs.get('action', '')
        user_guid = kwargs.get('user_guid')

        # Set memory context for user-specific storage
        if user_guid:
            self.storage_manager.set_memory_context(user_guid)

        # Route to appropriate handler
        if action == 'create_experiment':
            return self._create_experiment(kwargs)
        elif action == 'add_variant':
            return self._add_variant(kwargs)
        elif action == 'run_ab_test':
            return self._run_ab_test(kwargs)
        elif action == 'get_metrics':
            return self._get_metrics(kwargs)
        elif action == 'genetic_optimize':
            return self._genetic_optimize(kwargs)
        elif action == 'list_experiments':
            return self._list_experiments(kwargs)
        elif action == 'get_experiment':
            return self._get_experiment(kwargs)
        elif action == 'refine_prompt':
            return self._refine_prompt(kwargs)
        elif action == 'export_results':
            return self._export_results(kwargs)
        else:
            return f"Unknown action: {action}. Available actions: create_experiment, add_variant, run_ab_test, get_metrics, genetic_optimize, list_experiments, get_experiment, refine_prompt, export_results"

    def _create_experiment(self, kwargs: Dict[str, Any]) -> str:
        """Create a new prompt engineering experiment"""
        experiment_name = kwargs.get('experiment_name', 'Unnamed Experiment')
        test_cases = kwargs.get('test_cases', [])

        if not test_cases:
            return "Error: You must provide at least one test case for the experiment."

        # Generate unique experiment ID
        experiment_id = str(uuid.uuid4())[:8]

        # Create experiment structure
        experiment = {
            'id': experiment_id,
            'name': experiment_name,
            'created_at': datetime.now().isoformat(),
            'test_cases': test_cases,
            'variants': {},
            'results': {},
            'metrics': {},
            'generations': []
        }

        # Save to storage
        self._save_experiment(experiment_id, experiment)

        return f"""✅ Created experiment '{experiment_name}' (ID: {experiment_id})

📝 Test cases: {len(test_cases)}
{chr(10).join([f"  {i+1}. {tc[:60]}..." if len(tc) > 60 else f"  {i+1}. {tc}" for i, tc in enumerate(test_cases)])}

Next steps:
1. Add prompt variants: Use add_variant action
2. Run A/B tests: Use run_ab_test action
3. Optimize with genetic algorithms: Use genetic_optimize action"""

    def _add_variant(self, kwargs: Dict[str, Any]) -> str:
        """Add a prompt variant to an experiment"""
        experiment_id = kwargs.get('experiment_id')
        variant_name = kwargs.get('variant_name', f'Variant-{len(kwargs)}')
        prompt = kwargs.get('prompt', '')

        if not experiment_id:
            return "Error: experiment_id is required"
        if not prompt:
            return "Error: prompt text is required"

        # Load experiment
        experiment = self._load_experiment(experiment_id)
        if not experiment:
            return f"Error: Experiment {experiment_id} not found"

        # Add variant
        variant_id = str(uuid.uuid4())[:8]
        experiment['variants'][variant_id] = {
            'id': variant_id,
            'name': variant_name,
            'prompt': prompt,
            'added_at': datetime.now().isoformat()
        }

        # Save experiment
        self._save_experiment(experiment_id, experiment)

        return f"""✅ Added variant '{variant_name}' to experiment '{experiment['name']}'

📌 Variant ID: {variant_id}
📝 Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}

Total variants in experiment: {len(experiment['variants'])}"""

    def _run_ab_test(self, kwargs: Dict[str, Any]) -> str:
        """Run A/B tests on all variants in an experiment"""
        experiment_id = kwargs.get('experiment_id')

        if not experiment_id:
            return "Error: experiment_id is required"

        if not self.client:
            return "Error: Azure OpenAI client not initialized. Check your configuration."

        # Load experiment
        experiment = self._load_experiment(experiment_id)
        if not experiment:
            return f"Error: Experiment {experiment_id} not found"

        if not experiment['variants']:
            return "Error: No variants to test. Add variants first using add_variant action."

        # Run tests
        results_summary = []

        for variant_id, variant in experiment['variants'].items():
            variant_results = []
            total_tokens = 0
            total_latency = 0

            for test_case in experiment['test_cases']:
                try:
                    # Measure performance
                    start_time = time.time()

                    response = self.client.chat.completions.create(
                        model=self.deployment_name,
                        messages=[
                            {"role": "system", "content": variant['prompt']},
                            {"role": "user", "content": test_case}
                        ],
                        temperature=0.7,
                        max_tokens=500
                    )

                    latency = time.time() - start_time

                    # Extract metrics
                    completion = response.choices[0].message.content
                    tokens_used = response.usage.total_tokens

                    total_tokens += tokens_used
                    total_latency += latency

                    variant_results.append({
                        'test_case': test_case,
                        'response': completion,
                        'tokens': tokens_used,
                        'latency': latency,
                        'timestamp': datetime.now().isoformat()
                    })

                except Exception as e:
                    variant_results.append({
                        'test_case': test_case,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })

            # Calculate metrics
            num_tests = len(experiment['test_cases'])
            avg_tokens = total_tokens / num_tests if num_tests > 0 else 0
            avg_latency = total_latency / num_tests if num_tests > 0 else 0

            # Store results
            experiment['results'][variant_id] = variant_results
            experiment['metrics'][variant_id] = {
                'avg_tokens': avg_tokens,
                'avg_latency': avg_latency,
                'total_tests': num_tests,
                'success_rate': sum(1 for r in variant_results if 'error' not in r) / num_tests if num_tests > 0 else 0
            }

            results_summary.append({
                'variant_name': variant['name'],
                'variant_id': variant_id,
                'avg_tokens': avg_tokens,
                'avg_latency': avg_latency
            })

        # Save updated experiment
        self._save_experiment(experiment_id, experiment)

        # Format results
        output = f"✅ A/B Test completed for experiment '{experiment['name']}'\n\n"
        output += "📊 Results Summary:\n"

        # Sort by avg latency (faster is better)
        results_summary.sort(key=lambda x: x['avg_latency'])

        for i, result in enumerate(results_summary, 1):
            output += f"\n{i}. {result['variant_name']} (ID: {result['variant_id']})\n"
            output += f"   ⏱️  Avg Latency: {result['avg_latency']:.2f}s\n"
            output += f"   🎫 Avg Tokens: {result['avg_tokens']:.0f}\n"

        best_variant = results_summary[0]
        output += f"\n🏆 Best performer: {best_variant['variant_name']}"

        return output

    def _get_metrics(self, kwargs: Dict[str, Any]) -> str:
        """Get detailed metrics for an experiment"""
        experiment_id = kwargs.get('experiment_id')

        if not experiment_id:
            return "Error: experiment_id is required"

        experiment = self._load_experiment(experiment_id)
        if not experiment:
            return f"Error: Experiment {experiment_id} not found"

        if not experiment['metrics']:
            return "No metrics available. Run A/B tests first using run_ab_test action."

        output = f"📊 Metrics for '{experiment['name']}' (ID: {experiment_id})\n\n"

        for variant_id, metrics in experiment['metrics'].items():
            variant = experiment['variants'].get(variant_id, {})
            variant_name = variant.get('name', 'Unknown')

            output += f"📌 {variant_name}\n"
            output += f"   ⏱️  Avg Latency: {metrics['avg_latency']:.3f}s\n"
            output += f"   🎫 Avg Tokens: {metrics['avg_tokens']:.1f}\n"
            output += f"   ✅ Success Rate: {metrics['success_rate']*100:.1f}%\n"
            output += f"   📝 Tests Run: {metrics['total_tests']}\n\n"

        return output

    def _genetic_optimize(self, kwargs: Dict[str, Any]) -> str:
        """Use genetic algorithms to optimize prompts"""
        experiment_id = kwargs.get('experiment_id')
        population_size = kwargs.get('population_size', 10)
        generations = kwargs.get('generations', 5)

        if not experiment_id:
            return "Error: experiment_id is required"

        if not self.client:
            return "Error: Azure OpenAI client not initialized"

        experiment = self._load_experiment(experiment_id)
        if not experiment:
            return f"Error: Experiment {experiment_id} not found"

        if not experiment['variants']:
            return "Error: Need at least one variant as a starting point. Use add_variant first."

        # Get base prompts from existing variants
        base_prompts = [v['prompt'] for v in experiment['variants'].values()]

        output = f"🧬 Starting genetic optimization for '{experiment['name']}'\n\n"
        output += f"Population size: {population_size}\n"
        output += f"Generations: {generations}\n"
        output += f"Base prompts: {len(base_prompts)}\n\n"

        # Initialize population
        population = self._initialize_population(base_prompts, population_size)

        generation_log = []

        for gen in range(generations):
            output += f"🔄 Generation {gen + 1}/{generations}...\n"

            # Evaluate fitness for each individual
            fitness_scores = []
            for individual in population:
                fitness = self._evaluate_fitness(individual, experiment['test_cases'][:3])  # Use first 3 test cases for speed
                fitness_scores.append((individual, fitness))

            # Sort by fitness (lower is better - based on latency)
            fitness_scores.sort(key=lambda x: x[1])

            # Log best of generation
            best_prompt, best_fitness = fitness_scores[0]
            generation_log.append({
                'generation': gen + 1,
                'best_fitness': best_fitness,
                'best_prompt': best_prompt[:100]
            })

            output += f"   Best fitness: {best_fitness:.3f}\n"

            # Selection: Keep top 30%
            survivors = [individual for individual, _ in fitness_scores[:max(3, population_size // 3)]]

            # Generate new population
            new_population = survivors.copy()

            while len(new_population) < population_size:
                # Crossover: Combine two random survivors
                if len(survivors) >= 2:
                    parent1, parent2 = random.sample(survivors, 2)
                    child = self._crossover(parent1, parent2)

                    # Mutation: Random chance to mutate
                    if random.random() < 0.3:
                        child = self._mutate(child)

                    new_population.append(child)
                else:
                    # If not enough survivors, mutate existing ones
                    new_population.append(self._mutate(random.choice(survivors)))

            population = new_population

        # Save best prompt as new variant
        best_prompt, best_fitness = fitness_scores[0]
        variant_id = str(uuid.uuid4())[:8]
        experiment['variants'][variant_id] = {
            'id': variant_id,
            'name': f'Genetically Optimized (Gen {generations})',
            'prompt': best_prompt,
            'added_at': datetime.now().isoformat(),
            'optimization_metadata': {
                'method': 'genetic_algorithm',
                'generations': generations,
                'population_size': population_size,
                'final_fitness': best_fitness
            }
        }

        experiment['generations'] = generation_log
        self._save_experiment(experiment_id, experiment)

        output += f"\n✅ Optimization complete!\n"
        output += f"🏆 Best prompt (Fitness: {best_fitness:.3f}):\n{best_prompt}\n"
        output += f"\n📌 Saved as variant: {variant_id}"

        return output

    def _initialize_population(self, base_prompts: List[str], population_size: int) -> List[str]:
        """Initialize population with variations of base prompts"""
        population = base_prompts.copy()

        while len(population) < population_size:
            base = random.choice(base_prompts)
            mutated = self._mutate(base)
            population.append(mutated)

        return population[:population_size]

    def _evaluate_fitness(self, prompt: str, test_cases: List[str]) -> float:
        """Evaluate fitness of a prompt (lower is better)"""
        if not self.client:
            return float('inf')

        total_latency = 0
        total_tokens = 0
        errors = 0

        for test_case in test_cases:
            try:
                start_time = time.time()
                response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": test_case}
                    ],
                    temperature=0.7,
                    max_tokens=300
                )
                latency = time.time() - start_time
                total_latency += latency
                total_tokens += response.usage.total_tokens
            except Exception:
                errors += 1

        if errors == len(test_cases):
            return float('inf')

        # Fitness = weighted combination of latency and token usage
        # Lower is better
        avg_latency = total_latency / len(test_cases)
        avg_tokens = total_tokens / len(test_cases)

        fitness = (avg_latency * 0.7) + (avg_tokens / 1000 * 0.3)
        return fitness

    def _crossover(self, parent1: str, parent2: str) -> str:
        """Combine two prompts to create offspring"""
        # Split prompts into sentences
        sentences1 = re.split(r'[.!?]\s+', parent1)
        sentences2 = re.split(r'[.!?]\s+', parent2)

        # Randomly select sentences from each parent
        child_sentences = []
        max_len = max(len(sentences1), len(sentences2))

        for i in range(max_len):
            if i < len(sentences1) and i < len(sentences2):
                child_sentences.append(random.choice([sentences1[i], sentences2[i]]))
            elif i < len(sentences1):
                child_sentences.append(sentences1[i])
            elif i < len(sentences2):
                child_sentences.append(sentences2[i])

        return '. '.join(child_sentences).strip()

    def _mutate(self, prompt: str) -> str:
        """Apply random mutations to a prompt"""
        mutations = [
            lambda p: p.replace("You are", "You're"),
            lambda p: p.replace("should", "must"),
            lambda p: p.replace("can", "should"),
            lambda p: p + " Be concise.",
            lambda p: p + " Provide detailed explanations.",
            lambda p: p.replace(".", "!"),
            lambda p: "Always " + p,
            lambda p: p.replace("helpful", "extremely helpful"),
            lambda p: p.replace("assistant", "expert assistant"),
            lambda p: p + " Focus on accuracy."
        ]

        mutation = random.choice(mutations)
        try:
            return mutation(prompt)
        except:
            return prompt

    def _refine_prompt(self, kwargs: Dict[str, Any]) -> str:
        """Get AI-powered suggestions to improve a prompt"""
        prompt = kwargs.get('prompt', '')

        if not prompt:
            return "Error: prompt text is required"

        if not self.client:
            return "Error: Azure OpenAI client not initialized"

        refinement_prompt = f"""You are a prompt engineering expert. Analyze this prompt and provide 3 specific, actionable suggestions to improve it:

PROMPT TO ANALYZE:
{prompt}

Provide suggestions in this format:
1. [Suggestion category]: [Specific improvement]
2. [Suggestion category]: [Specific improvement]
3. [Suggestion category]: [Specific improvement]

Focus on clarity, effectiveness, and specificity."""

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "user", "content": refinement_prompt}
                ],
                temperature=0.8,
                max_tokens=500
            )

            suggestions = response.choices[0].message.content

            return f"""💡 Prompt Refinement Suggestions

Original prompt:
{prompt}

{suggestions}

💡 Tip: Create variants based on these suggestions and run A/B tests to find the best version!"""

        except Exception as e:
            return f"Error getting refinement suggestions: {str(e)}"

    def _list_experiments(self, kwargs: Dict[str, Any]) -> str:
        """List all experiments"""
        try:
            # Read all experiments from storage
            experiments_data = self.storage_manager.read_file('prompt_playground', 'experiments.json')

            if not experiments_data:
                return "No experiments found. Create one using create_experiment action."

            experiments = json.loads(experiments_data)

            if not experiments:
                return "No experiments found."

            output = "📚 Your Prompt Engineering Experiments:\n\n"

            for exp_id, exp in experiments.items():
                output += f"📌 {exp['name']} (ID: {exp_id})\n"
                output += f"   Created: {exp['created_at'][:10]}\n"
                output += f"   Variants: {len(exp.get('variants', {}))}\n"
                output += f"   Test cases: {len(exp.get('test_cases', []))}\n"
                output += f"   Status: {'Tested' if exp.get('results') else 'Not tested'}\n\n"

            return output

        except Exception as e:
            return f"Error listing experiments: {str(e)}"

    def _get_experiment(self, kwargs: Dict[str, Any]) -> str:
        """Get detailed information about an experiment"""
        experiment_id = kwargs.get('experiment_id')

        if not experiment_id:
            return "Error: experiment_id is required"

        experiment = self._load_experiment(experiment_id)
        if not experiment:
            return f"Error: Experiment {experiment_id} not found"

        output = f"📊 Experiment Details: {experiment['name']}\n\n"
        output += f"ID: {experiment_id}\n"
        output += f"Created: {experiment['created_at']}\n"
        output += f"Test Cases: {len(experiment['test_cases'])}\n"
        output += f"Variants: {len(experiment['variants'])}\n\n"

        if experiment['variants']:
            output += "📝 Variants:\n"
            for var_id, variant in experiment['variants'].items():
                output += f"  • {variant['name']} (ID: {var_id})\n"
                output += f"    Prompt: {variant['prompt'][:80]}...\n\n"

        if experiment['metrics']:
            output += "📊 Performance Metrics:\n"
            for var_id, metrics in experiment['metrics'].items():
                variant_name = experiment['variants'][var_id]['name']
                output += f"  • {variant_name}:\n"
                output += f"    Latency: {metrics['avg_latency']:.3f}s\n"
                output += f"    Tokens: {metrics['avg_tokens']:.0f}\n"
                output += f"    Success: {metrics['success_rate']*100:.0f}%\n\n"

        if experiment.get('generations'):
            output += f"🧬 Genetic Optimization: {len(experiment['generations'])} generations\n"

        return output

    def _export_results(self, kwargs: Dict[str, Any]) -> str:
        """Export experiment results as JSON"""
        experiment_id = kwargs.get('experiment_id')

        if not experiment_id:
            return "Error: experiment_id is required"

        experiment = self._load_experiment(experiment_id)
        if not experiment:
            return f"Error: Experiment {experiment_id} not found"

        # Create export data
        export_data = {
            'experiment': experiment,
            'exported_at': datetime.now().isoformat()
        }

        # Pretty print JSON
        json_output = json.dumps(export_data, indent=2)

        return f"""✅ Experiment data exported

```json
{json_output}
```

You can save this data for further analysis or import it later."""

    def _load_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """Load an experiment from storage"""
        try:
            experiments_data = self.storage_manager.read_file('prompt_playground', 'experiments.json')

            if not experiments_data:
                return None

            experiments = json.loads(experiments_data)
            return experiments.get(experiment_id)

        except Exception:
            return None

    def _save_experiment(self, experiment_id: str, experiment: Dict[str, Any]):
        """Save an experiment to storage"""
        try:
            # Load all experiments
            experiments_data = self.storage_manager.read_file('prompt_playground', 'experiments.json')

            if experiments_data:
                experiments = json.loads(experiments_data)
            else:
                experiments = {}

            # Update experiment
            experiments[experiment_id] = experiment

            # Save back to storage
            self.storage_manager.write_file(
                'prompt_playground',
                'experiments.json',
                json.dumps(experiments, indent=2)
            )

        except Exception as e:
            raise Exception(f"Failed to save experiment: {str(e)}")
