"""
Contract Analysis Agent
Analyzes contracts to extract key obligations, identify risks, and compare multiple contracts.
"""
import json
import uuid
from datetime import datetime
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager


class ContractAnalysisAgent(BasicAgent):
    def __init__(self):
        self.name = 'ContractAnalysis'
        self.metadata = {
            "name": self.name,
            "description": (
                "Analyzes legal contracts to extract key obligations, payment terms, deadlines, "
                "risk factors, and liabilities. Can store contracts and compare multiple contracts "
                "side-by-side. Use this agent when the user wants to analyze contract documents, "
                "understand contractual obligations, flag risks, or compare contract terms."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action to perform: 'analyze' to analyze a single contract, 'store' to save a contract for later comparison, 'compare' to compare two stored contracts, or 'list' to show stored contracts.",
                        "enum": ["analyze", "store", "compare", "list"]
                    },
                    "contract_text": {
                        "type": "string",
                        "description": "The full text of the contract to analyze or store. Required for 'analyze' and 'store' actions."
                    },
                    "contract_name": {
                        "type": "string",
                        "description": "A name or identifier for the contract (e.g., 'Vendor Agreement 2024', 'Employment Contract - John Doe'). Required for 'store' action."
                    },
                    "contract_id_1": {
                        "type": "string",
                        "description": "First contract ID for comparison. Required for 'compare' action."
                    },
                    "contract_id_2": {
                        "type": "string",
                        "description": "Second contract ID for comparison. Required for 'compare' action."
                    },
                    "analysis_focus": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of specific areas to focus on: 'obligations', 'payments', 'deadlines', 'risks', 'termination', 'liability', 'warranties', 'intellectual_property'."
                    },
                    "user_guid": {
                        "type": "string",
                        "description": "User identifier for storing contracts in user-specific storage."
                    }
                },
                "required": ["action"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        """Main entry point for contract analysis operations"""
        action = kwargs.get('action', 'analyze')
        user_guid = kwargs.get('user_guid')

        # Set user context for storage operations
        if user_guid:
            self.storage_manager.set_memory_context(user_guid)

        if action == 'analyze':
            return self._analyze_contract(kwargs)
        elif action == 'store':
            return self._store_contract(kwargs)
        elif action == 'compare':
            return self._compare_contracts(kwargs)
        elif action == 'list':
            return self._list_contracts()
        else:
            return f"Error: Unknown action '{action}'. Valid actions are: analyze, store, compare, list."

    def _analyze_contract(self, kwargs):
        """Analyze a single contract and extract key information"""
        contract_text = kwargs.get('contract_text', '')
        analysis_focus = kwargs.get('analysis_focus', [
            'obligations', 'payments', 'deadlines', 'risks', 'termination', 'liability'
        ])

        if not contract_text:
            return "Error: No contract text provided for analysis."

        # Initialize results
        results = {
            'summary': self._extract_summary(contract_text),
            'sections': {}
        }

        # Extract information based on focus areas
        if 'obligations' in analysis_focus:
            results['sections']['Key Obligations'] = self._extract_obligations(contract_text)

        if 'payments' in analysis_focus:
            results['sections']['Payment Terms'] = self._extract_payment_terms(contract_text)

        if 'deadlines' in analysis_focus:
            results['sections']['Deadlines & Timelines'] = self._extract_deadlines(contract_text)

        if 'risks' in analysis_focus:
            results['sections']['Risk Factors'] = self._identify_risks(contract_text)

        if 'termination' in analysis_focus:
            results['sections']['Termination Conditions'] = self._extract_termination(contract_text)

        if 'liability' in analysis_focus:
            results['sections']['Liability & Indemnification'] = self._extract_liability(contract_text)

        if 'warranties' in analysis_focus:
            results['sections']['Warranties & Representations'] = self._extract_warranties(contract_text)

        if 'intellectual_property' in analysis_focus:
            results['sections']['Intellectual Property'] = self._extract_ip_terms(contract_text)

        # Format results
        return self._format_analysis_results(results)

    def _extract_summary(self, text):
        """Extract basic contract information"""
        lines = text.split('\n')
        summary = {
            'length': f"{len(text)} characters, {len(lines)} lines",
            'type': self._identify_contract_type(text),
        }
        return summary

    def _identify_contract_type(self, text):
        """Identify the type of contract based on keywords"""
        text_lower = text.lower()

        contract_types = {
            'employment': ['employment', 'employee', 'employer', 'hire', 'job title', 'salary'],
            'vendor': ['vendor', 'supplier', 'purchase', 'goods', 'services'],
            'nda': ['non-disclosure', 'confidential', 'confidentiality', 'proprietary information'],
            'lease': ['lease', 'landlord', 'tenant', 'rent', 'premises', 'property'],
            'service': ['service agreement', 'statement of work', 'sow', 'deliverables'],
            'license': ['license', 'licensor', 'licensee', 'intellectual property', 'software'],
        }

        matches = []
        for contract_type, keywords in contract_types.items():
            if sum(1 for keyword in keywords if keyword in text_lower) >= 2:
                matches.append(contract_type)

        return matches[0] if matches else 'general'

    def _extract_obligations(self, text):
        """Extract key obligations and responsibilities"""
        obligations = []
        lines = text.split('\n')

        # Keywords that indicate obligations
        obligation_keywords = [
            'shall', 'must', 'will', 'agrees to', 'required to', 'responsible for',
            'obligated to', 'undertakes to', 'commits to'
        ]

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in obligation_keywords):
                # Get some context (current line + next line if available)
                context = line.strip()
                if i + 1 < len(lines) and lines[i + 1].strip():
                    context += " " + lines[i + 1].strip()

                if len(context) > 20:  # Filter out very short matches
                    obligations.append(context[:300])  # Limit length

        return obligations[:10] if obligations else ["No specific obligations identified using keyword matching."]

    def _extract_payment_terms(self, text):
        """Extract payment-related terms"""
        payment_terms = []
        lines = text.split('\n')

        payment_keywords = [
            'payment', 'fee', 'compensation', 'invoice', 'price', 'cost',
            'dollar', '$', 'paid', 'remuneration', 'salary', 'wage'
        ]

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in payment_keywords):
                context = line.strip()
                if i + 1 < len(lines) and lines[i + 1].strip():
                    context += " " + lines[i + 1].strip()

                if len(context) > 15:
                    payment_terms.append(context[:300])

        return payment_terms[:8] if payment_terms else ["No payment terms identified using keyword matching."]

    def _extract_deadlines(self, text):
        """Extract deadlines and time-sensitive clauses"""
        deadlines = []
        lines = text.split('\n')

        deadline_keywords = [
            'deadline', 'within', 'days', 'weeks', 'months', 'by the date',
            'no later than', 'prior to', 'before', 'after', 'term of'
        ]

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in deadline_keywords):
                context = line.strip()
                if i + 1 < len(lines) and lines[i + 1].strip():
                    context += " " + lines[i + 1].strip()

                if len(context) > 15:
                    deadlines.append(context[:300])

        return deadlines[:8] if deadlines else ["No specific deadlines identified using keyword matching."]

    def _identify_risks(self, text):
        """Identify potential risk factors and problematic clauses"""
        risks = []
        text_lower = text.lower()

        risk_patterns = {
            'Unlimited Liability': ['unlimited liability', 'without limitation', 'no cap on liability'],
            'Automatic Renewal': ['automatic renewal', 'automatically renew', 'auto-renew'],
            'Unilateral Changes': ['may modify', 'reserves the right to change', 'at our discretion'],
            'Broad Indemnification': ['indemnify', 'hold harmless', 'defend against all claims'],
            'Exclusive Jurisdiction': ['exclusive jurisdiction', 'exclusive venue', 'forum selection'],
            'Non-Compete': ['non-compete', 'non-competition', 'shall not compete'],
            'Assignment Restrictions': ['not assign', 'may not transfer', 'assignment prohibited'],
            'Penalty Clauses': ['penalty', 'liquidated damages', 'late fee'],
        }

        for risk_name, keywords in risk_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                risks.append(f"⚠️ {risk_name}: Found language that may indicate this risk")

        return risks if risks else ["No major risk factors identified using pattern matching."]

    def _extract_termination(self, text):
        """Extract termination and cancellation terms"""
        termination_terms = []
        lines = text.split('\n')

        termination_keywords = [
            'terminate', 'termination', 'cancel', 'cancellation', 'exit',
            'end this agreement', 'may be terminated', 'notice period'
        ]

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in termination_keywords):
                context = line.strip()
                if i + 1 < len(lines) and lines[i + 1].strip():
                    context += " " + lines[i + 1].strip()

                if len(context) > 15:
                    termination_terms.append(context[:300])

        return termination_terms[:6] if termination_terms else ["No termination clauses identified using keyword matching."]

    def _extract_liability(self, text):
        """Extract liability and indemnification clauses"""
        liability_terms = []
        lines = text.split('\n')

        liability_keywords = [
            'liability', 'indemnify', 'indemnification', 'hold harmless',
            'limitation of liability', 'damages', 'liable for'
        ]

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in liability_keywords):
                context = line.strip()
                if i + 1 < len(lines) and lines[i + 1].strip():
                    context += " " + lines[i + 1].strip()

                if len(context) > 15:
                    liability_terms.append(context[:300])

        return liability_terms[:6] if liability_terms else ["No liability terms identified using keyword matching."]

    def _extract_warranties(self, text):
        """Extract warranty and representation clauses"""
        warranties = []
        lines = text.split('\n')

        warranty_keywords = [
            'warrant', 'warranty', 'represents', 'representation', 'guarantees',
            'guarantee', 'assures', 'assurance'
        ]

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in warranty_keywords):
                context = line.strip()
                if i + 1 < len(lines) and lines[i + 1].strip():
                    context += " " + lines[i + 1].strip()

                if len(context) > 15:
                    warranties.append(context[:300])

        return warranties[:6] if warranties else ["No warranty terms identified using keyword matching."]

    def _extract_ip_terms(self, text):
        """Extract intellectual property terms"""
        ip_terms = []
        lines = text.split('\n')

        ip_keywords = [
            'intellectual property', 'copyright', 'trademark', 'patent',
            'trade secret', 'proprietary', 'ownership', 'ip rights'
        ]

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ip_keywords):
                context = line.strip()
                if i + 1 < len(lines) and lines[i + 1].strip():
                    context += " " + lines[i + 1].strip()

                if len(context) > 15:
                    ip_terms.append(context[:300])

        return ip_terms[:6] if ip_terms else ["No intellectual property terms identified using keyword matching."]

    def _format_analysis_results(self, results):
        """Format analysis results into readable output"""
        output = ["## Contract Analysis Results\n"]

        # Summary
        summary = results.get('summary', {})
        output.append(f"**Document Stats:** {summary.get('length', 'N/A')}")
        output.append(f"**Contract Type:** {summary.get('type', 'unknown').title()}\n")

        # Sections
        for section_name, items in results.get('sections', {}).items():
            output.append(f"### {section_name}")
            if items:
                for i, item in enumerate(items, 1):
                    output.append(f"{i}. {item}")
            else:
                output.append("- None identified")
            output.append("")

        return "\n".join(output)

    def _store_contract(self, kwargs):
        """Store a contract for later retrieval and comparison"""
        contract_text = kwargs.get('contract_text', '')
        contract_name = kwargs.get('contract_name', '')

        if not contract_text:
            return "Error: No contract text provided."

        if not contract_name:
            return "Error: No contract name provided. Please specify a name for this contract."

        # Generate unique ID
        contract_id = str(uuid.uuid4())[:8]

        # Store contract
        contract_data = {
            'id': contract_id,
            'name': contract_name,
            'text': contract_text,
            'stored_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'length': len(contract_text),
            'type': self._identify_contract_type(contract_text)
        }

        # Read existing contracts
        try:
            contracts_file = self.storage_manager.read_file('contracts', 'stored_contracts.json')
            if contracts_file:
                all_contracts = json.loads(contracts_file)
            else:
                all_contracts = {}
        except:
            all_contracts = {}

        # Add new contract
        all_contracts[contract_id] = contract_data

        # Save back
        self.storage_manager.write_file('contracts', 'stored_contracts.json', json.dumps(all_contracts, indent=2))

        return f"✅ Contract stored successfully!\n\n**Contract ID:** {contract_id}\n**Name:** {contract_name}\n**Type:** {contract_data['type']}\n**Length:** {contract_data['length']} characters\n\nUse this Contract ID to compare with other contracts."

    def _list_contracts(self):
        """List all stored contracts"""
        try:
            contracts_file = self.storage_manager.read_file('contracts', 'stored_contracts.json')
            if not contracts_file:
                return "No contracts stored yet. Use the 'store' action to save contracts for comparison."

            all_contracts = json.loads(contracts_file)

            if not all_contracts:
                return "No contracts stored yet."

            output = ["## Stored Contracts\n"]
            for contract_id, contract_data in all_contracts.items():
                output.append(f"**ID:** {contract_id}")
                output.append(f"**Name:** {contract_data.get('name', 'Unnamed')}")
                output.append(f"**Type:** {contract_data.get('type', 'unknown')}")
                output.append(f"**Stored:** {contract_data.get('stored_date', 'N/A')}")
                output.append(f"**Length:** {contract_data.get('length', 0)} characters\n")

            return "\n".join(output)
        except Exception as e:
            return f"Error listing contracts: {str(e)}"

    def _compare_contracts(self, kwargs):
        """Compare two stored contracts side-by-side"""
        contract_id_1 = kwargs.get('contract_id_1', '')
        contract_id_2 = kwargs.get('contract_id_2', '')

        if not contract_id_1 or not contract_id_2:
            return "Error: Please provide both contract_id_1 and contract_id_2 for comparison."

        try:
            # Load contracts
            contracts_file = self.storage_manager.read_file('contracts', 'stored_contracts.json')
            if not contracts_file:
                return "Error: No contracts stored. Please store contracts first using the 'store' action."

            all_contracts = json.loads(contracts_file)

            contract_1 = all_contracts.get(contract_id_1)
            contract_2 = all_contracts.get(contract_id_2)

            if not contract_1:
                return f"Error: Contract with ID '{contract_id_1}' not found."
            if not contract_2:
                return f"Error: Contract with ID '{contract_id_2}' not found."

            # Analyze both contracts
            analysis_1 = self._analyze_contract({'contract_text': contract_1['text']})
            analysis_2 = self._analyze_contract({'contract_text': contract_2['text']})

            # Create comparison table
            output = ["## Contract Comparison\n"]
            output.append(f"### Contract A: {contract_1['name']}")
            output.append(f"**ID:** {contract_id_1} | **Type:** {contract_1['type']} | **Length:** {contract_1['length']} chars\n")

            output.append(f"### Contract B: {contract_2['name']}")
            output.append(f"**ID:** {contract_id_2} | **Type:** {contract_2['type']} | **Length:** {contract_2['length']} chars\n")

            output.append("---\n")
            output.append("### Side-by-Side Analysis\n")
            output.append("#### Contract A Analysis")
            output.append(analysis_1)
            output.append("\n#### Contract B Analysis")
            output.append(analysis_2)

            return "\n".join(output)
        except Exception as e:
            return f"Error comparing contracts: {str(e)}"
