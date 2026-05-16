"""
Aethera AI - Intent Classification and Specialist Routing Module

Routes user queries to the appropriate specialist based on:
- Intent classification using keyword matching and ML
- Query complexity assessment
- Domain-specific signal detection
- Multi-domain query handling

The router is the "traffic cop" that directs every query to the right expert.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import yaml


class RoutingConfidence(Enum):
    """Confidence levels for routing decisions."""
    VERY_HIGH = 0.9  # Direct specialist match
    HIGH = 0.7       # Strong match
    MEDIUM = 0.5     # Moderate match
    LOW = 0.3        # Weak match
    VERY_LOW = 0.1   # Guessing


@dataclass
class RoutingResult:
    """Result of intent classification and routing."""
    primary_specialist: str
    confidence: float
    confidence_level: RoutingConfidence
    secondary_specialists: List[str] = field(default_factory=list)
    detected_intents: List[str] = field(default_factory=list)
    detected_entities: List[Dict[str, str]] = field(default_factory=list)
    requires_multi_agent: bool = False
    recommended_tools: List[str] = field(default_factory=list)
    query_complexity: str = "medium"  # simple, medium, complex
    reasoning: str = ""


class IntentClassifier:
    """
    Classifies user intent using keyword matching and pattern recognition.

    Supports slash commands, natural language queries, and healthcare-specific
    intent patterns.
    """

    # Slash command patterns
    SLASH_COMMANDS = {
        "help": "show_help",
        "specialist": "force_specialist",
        "specialists": "list_specialists",
        "skills": "list_skills",
        "skill": "run_skill",
        "plugins": "list_plugins",
        "plugin": "plugin_command",
        "connectors": "list_connectors",
        "connector": "connector_command",
        "automations": "list_automations",
        "queue": "show_queue",
        "briefing": "generate_briefing",
        "alerts": "show_alerts",
        "dashboard": "show_dashboard",
        "code": "code_lookup",
        "appeal": "start_appeal",
        "denial": "analyze_denial",
        "drug": "drug_lookup",
        "npi": "npi_lookup",
        "coverage": "coverage_check",
        "fee": "fee_schedule",
        "cf": "cloudflare_command",
        "profile": "show_profile",
        "settings": "show_settings",
        "export": "export_data",
        "model": "set_model",
        "local": "force_local",
        "search": "web_search",
        "memory": "show_memory",
        "forget": "remove_memory",
    }

    # Intent keywords by category
    INTENT_KEYWORDS = {
        # Healthcare Provider intents
        "coding_lookup": [
            "ICD", "CPT", "HCPCS", "CDT", "code", "coding", "diagnosis code",
            "procedure code", "revenue code", "modifier", "NDC"
        ],
        "claim_analysis": [
            "claim", "EOB", "ERA", "remittance", "837", "835", "submission",
            "rejection", "denial", "appeal", "underpaid", "overpaid"
        ],
        "reimbursement_check": [
            "reimbursement", "payment", "fee schedule", "MPFS", "OPPS", "IPPS",
            "DRG", "APC", "allowed", "denied", "adjustment"
        ],
        "medical_necessity": [
            "medical necessity", "coverage", "LCD", "NCD", "prior auth",
            "authorization", "pre-cert", "pre-certification"
        ],
        "cci_edit": [
            "CCI", "NCCI", "bundled", "unbundled", "modifier 59", "edit",
            "pair", "compatible"
        ],

        # Healthcare Payer intents
        "adjudication_logic": [
            "adjudication", "claim processing", "auto-adjudicate", "manual review",
            "pricing", "COB", "coordination of benefits"
        ],
        "utilization_management": [
            "utilization management", "UM", "prior authorization", "concurrent review",
            "retrospective review", "level of care", "inpatient", "observation"
        ],
        "risk_adjustment": [
            "risk adjustment", "HCC", "RAF", "CMS-HCC", "HHS-HCC", "CDPS",
            "risk score", "capture", "gap closure"
        ],
        "quality_measures": [
            "HEDIS", "Stars", "Star Ratings", "MIPS", "quality measures",
            "CAHPS", "EGHPSS", "Outcomes"
        ],
        "network_management": [
            "network", "in-network", "out-of-network", "credentialing",
            "provider directory", "adequacy", "participating"
        ],

        # Regulatory intents
        "compliance_check": [
            "compliance", "HIPAA", "OIG", "Stark", "Anti-Kickback", "AKS",
            "False Claims", "fraud", "abuse", "audit"
        ],
        "regulatory_research": [
            "regulation", "rule", "CMS manual", "transmittal", "final rule",
            "proposed rule", "CFR", "statute", "law"
        ],

        # Clinical intents
        "clinical_reference": [
            "clinical", "guideline", "protocol", "pathway", "best practice",
            "evidence", "study", "trial"
        ],
        "drug_information": [
            "drug", "medication", "pharmaceutical", "dosage", "interaction",
            "contraindication", "side effect", "adverse"
        ],
        "lab_interpretation": [
            "lab", "laboratory", "result", "value", "level", "marker",
            "LOINC", "reference range"
        ],

        # General intents
        "research": [
            "research", "literature", "review", "evidence", "systematic",
            "meta-analysis", "study", "paper", "article"
        ],
        "analysis": [
            "analyze", "analysis", "breakdown", "trend", "pattern",
            "insight", "findings"
        ],
        "comparison": [
            "compare", "comparison", "vs", "versus", "difference", "similar",
            "better", "worse"
        ],
        "calculation": [
            "calculate", "calculation", "compute", "formula", "equation",
            "score", "index", "ratio"
        ],
        "summarization": [
            "summarize", "summary", "overview", "brief", "highlights",
            "key points", "tl;dr"
        ],
        "explanation": [
            "explain", "what is", "how does", "why", "describe", "define",
            "meaning", "purpose"
        ],
        "how_to": [
            "how to", "steps", "process", "procedure", "workflow",
            "instructions", "guide"
        ],
        "troubleshooting": [
            "error", "issue", "problem", "not working", "broken", "fix",
            "debug", "troubleshoot"
        ],
        "creative": [
            "write", "draft", "create", "generate", "compose", "design",
            "brainstorm", "ideas"
        ],
        "planning": [
            "plan", "strategy", "roadmap", "timeline", "schedule", "organize",
            "prepare"
        ],
    }

    # Complexity indicators
    COMPLEXITY_INDICATORS = {
        "complex": [
            "multi", "multiple", "several", "various", "comprehensive",
            "detailed", "thorough", "deep dive", "in-depth", "complete",
            "full analysis", "compare all", "review everything"
        ],
        "simple": [
            "quick", "brief", "simple", "basic", "just", "only", "one",
            "single", "yes or no", "what's", "whats"
        ]
    }

    def __init__(self, config_path: Optional[str] = None):
        self.config = {}
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    self.config = yaml.safe_load(f)
            except Exception:
                pass

        # Compile regex patterns for keywords
        self.keyword_patterns = {}
        for intent, keywords in self.INTENT_KEYWORDS.items():
            pattern = r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b'
            self.keyword_patterns[intent] = re.compile(pattern, re.IGNORECASE)

        self.complexity_patterns = {}
        for level, indicators in self.COMPLEXITY_INDICATORS.items():
            pattern = r'\b(' + '|'.join(re.escape(i) for i in indicators) + r')\b'
            self.complexity_patterns[level] = re.compile(pattern, re.IGNORECASE)

    def classify(self, query: str) -> List[str]:
        """
        Classify query intent.

        Returns list of detected intents ranked by confidence.
        """
        detected_intents = []

        # Check for slash commands first
        if query.strip().startswith('/'):
            command = query.split()[0].lower().lstrip('/')
            if command in self.SLASH_COMMANDS:
                return [f"command:{self.SLASH_COMMANDS[command]}"]

        # Score each intent category
        intent_scores = []
        for intent, pattern in self.keyword_patterns.items():
            matches = pattern.findall(query)
            if matches:
                # Score based on number of matches and keyword specificity
                score = len(matches) * 0.3
                # Boost for exact phrase matches
                for match in matches:
                    if match.lower() in query.lower():
                        score += 0.1
                intent_scores.append((intent, score))

        # Sort by score
        intent_scores.sort(key=lambda x: x[1], reverse=True)

        # Return intents above threshold
        for intent, score in intent_scores:
            if score >= 0.3:
                detected_intents.append(intent)

        return detected_intents if detected_intents else ["general_query"]

    def assess_complexity(self, query: str) -> str:
        """Assess query complexity."""
        # Check length
        word_count = len(query.split())

        # Check for complexity indicators
        complex_matches = len(self.complexity_patterns["complex"].findall(query))
        simple_matches = len(self.complexity_patterns["simple"].findall(query))

        # Decision logic
        if complex_matches > simple_matches or word_count > 50:
            return "complex"
        elif simple_matches > complex_matches or word_count < 10:
            return "simple"
        else:
            return "medium"

    def extract_entities(self, query: str) -> List[Dict[str, str]]:
        """Extract relevant entities from query."""
        entities = []

        # ICD-10 codes
        icd_pattern = r'\b([A-Z]\d{2}(?:\.\d{1,4})?)\b'
        for match in re.finditer(icd_pattern, query, re.IGNORECASE):
            entities.append({
                "type": "icd10",
                "value": match.group(1).upper(),
                "position": match.start()
            })

        # CPT codes (5 digits, optionally followed by letter, with context)
        cpt_pattern = r'\bCPT[:\s]?\s*(\d{4}[0-9A-Z]\d?)\b|\b(\d{5}[A-Z]?)\b(?=\s*(?:code|procedure|service)|\s*$)'
        for match in re.finditer(cpt_pattern, query, re.IGNORECASE):
            value = match.group(1) or match.group(2)
            if value:
                entities.append({
                    "type": "cpt",
                    "value": value.upper(),
                    "position": match.start()
                })

        # HCPCS codes
        hcpcs_pattern = r'\b([A-Z]\d{4}[A-Z]?)\b'
        for match in re.finditer(hcpcs_pattern, query):
            entities.append({
                "type": "hcpcs",
                "value": match.group(1).upper(),
                "position": match.start()
            })

        # NPI numbers (require NPI prefix to avoid false positives)
        npi_pattern = r'\bNPI[:\s]?\s*(\d{10})\b'
        for match in re.finditer(npi_pattern, query, re.IGNORECASE):
            entities.append({
                "type": "npi",
                "value": match.group(1),
                "position": match.start()
            })

        # Dollar amounts
        money_pattern = r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        for match in re.finditer(money_pattern, query):
            entities.append({
                "type": "monetary",
                "value": match.group(1),
                "position": match.start()
            })

        # Dates
        date_pattern = r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b'
        for match in re.finditer(date_pattern, query):
            entities.append({
                "type": "date",
                "value": match.group(1),
                "position": match.start()
            })

        return entities


class AetheraRouter:
    """
    Main router for Aethera AI.

    Routes queries to specialists with proper tool selection and
    multi-agent coordination when needed.

    Slash commands recognized:
    - /help - show all commands
    - /specialist <name> - force a specific specialist
    - /skills - list available skills
    - /skill <name> - run a specific skill
    - /plugins - list plugins and status
    - /connectors - list connectors and status
    - /automations - list active automations
    - /queue - show action queue
    - /briefing - generate morning briefing
    - /alerts - show active alerts
    - /dashboard - switch to dashboard view
    - /code <query> - force ICD-10/CPT lookup
    - /appeal <claim_info> - start appeals workflow
    - /denial <codes> - analyze denial
    - /drug <name> - drug lookup
    - /npi <number_or_name> - NPI lookup
    - /coverage <cpt> <payer> - coverage criteria check
    - /fee <cpt> - fee schedule lookup
    - /cf status - Cloudflare infrastructure status
    - /profile - view/edit user profile
    - /settings - open settings
    - /export <type> - export data
    - /model <name> - force a specific model
    - /local - force local Ollama model
    - /search <query> - web search
    - /memory - show what Aethera remembers
    - /forget <topic> - remove specific memories
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.classifier = IntentClassifier(config_path)
        self.specialists = self._load_specialists()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    def _load_specialists(self) -> Dict[str, Dict[str, Any]]:
        """Load specialist configuration."""
        specialists = {}
        if self.config.get('specialists'):
            for name, spec_config in self.config['specialists'].items():
                specialists[name] = {
                    "enabled": spec_config.get("enabled", True),
                    "description": spec_config.get("description", ""),
                    "color": spec_config.get("color", "#6B7280"),
                    "default_model": spec_config.get("default_model", "aethera-cloud-balanced"),
                    "keywords": spec_config.get("keywords", []),
                    "tools": spec_config.get("tools", []),
                    "priority": spec_config.get("priority", 3)
                }
        return specialists

    def route(self, query: str, context: Optional[Dict[str, Any]] = None) -> RoutingResult:
        """
        Route a user query to the appropriate specialist.

        Args:
            query: User's query text
            context: Optional context (conversation history, user profile, etc.)

        Returns:
            RoutingResult with specialist, confidence, and recommendations
        """
        # Check for slash commands
        if query.strip().startswith('/'):
            return self._route_command(query)

        # Classify intent
        detected_intents = self.classifier.classify(query)
        complexity = self.classifier.assess_complexity(query)
        entities = self.classifier.extract_entities(query)

        # Find matching specialist
        specialist, confidence, reasoning = self._find_specialist(
            query, detected_intents, entities
        )

        # Determine if multi-agent is needed
        requires_multi_agent = (
            confidence < 0.5 or
            len(detected_intents) > 2 or
            complexity == "complex"
        )

        # Get recommended tools
        recommended_tools = self._get_recommended_tools(specialist, detected_intents)

        # Determine confidence level
        if confidence >= 0.9:
            confidence_level = RoutingConfidence.VERY_HIGH
        elif confidence >= 0.7:
            confidence_level = RoutingConfidence.HIGH
        elif confidence >= 0.5:
            confidence_level = RoutingConfidence.MEDIUM
        elif confidence >= 0.3:
            confidence_level = RoutingConfidence.LOW
        else:
            confidence_level = RoutingConfidence.VERY_LOW

        return RoutingResult(
            primary_specialist=specialist,
            confidence=confidence,
            confidence_level=confidence_level,
            detected_intents=detected_intents,
            detected_entities=entities,
            requires_multi_agent=requires_multi_agent,
            recommended_tools=recommended_tools,
            query_complexity=complexity,
            reasoning=reasoning
        )

    def _route_command(self, query: str) -> RoutingResult:
        """Route slash commands to appropriate handlers."""
        parts = query.strip().split()
        command = parts[0].lower().lstrip('/')

        # Map commands to specialists
        command_specialist_map = {
            "code": "healthcare_provider",
            "appeal": "healthcare_provider",
            "denial": "healthcare_provider",
            "drug": "healthcare_pharmacy",
            "npi": "healthcare_provider",
            "coverage": "healthcare_provider",
            "fee": "healthcare_provider",
            "cf": "cloudflare_ops",
            "search": "research",
        }

        specialist = command_specialist_map.get(command, "general")

        return RoutingResult(
            primary_specialist=specialist,
            confidence=1.0,
            confidence_level=RoutingConfidence.VERY_HIGH,
            detected_intents=[f"command:{command}"],
            reasoning=f"Slash command /{command} routed to {specialist}"
        )

    def _find_specialist(
        self,
        query: str,
        intents: List[str],
        entities: List[Dict[str, str]]
    ) -> Tuple[str, float, str]:
        """
        Find the best matching specialist for a query.

        Returns:
            Tuple of (specialist_name, confidence, reasoning)
        """
        query_lower = query.lower()
        scores = {}

        # Score each specialist
        for specialist_name, specialist_config in self.specialists.items():
            if not specialist_config.get("enabled", True):
                continue

            score = 0.0
            reasons = []

            # Keyword matching
            keywords = specialist_config.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    score += 0.15
                    reasons.append(f"matched keyword '{keyword}'")

            # Intent matching
            for intent in intents:
                if self._intent_matches_specialist(intent, specialist_name):
                    score += 0.3
                    reasons.append(f"intent '{intent}' matches specialist")

            # Entity-based boosting
            for entity in entities:
                if self._entity_matches_specialist(entity, specialist_name):
                    score += 0.2
                    reasons.append(f"entity '{entity['type']}' relevant to specialist")

            # Apply priority bonus (lower priority number = higher priority)
            priority = specialist_config.get("priority", 3)
            if score > 0:
                score *= (1.0 + (0.1 * (3 - priority)))

            scores[specialist_name] = (score, reasons)

        # Find best match
        if not scores:
            return "general", 0.3, "No strong specialist match found, using general"

        best_specialist = max(scores.items(), key=lambda x: x[1][0])
        specialist_name = best_specialist[0]
        score = min(1.0, best_specialist[1][0])
        reasons = best_specialist[1][1]

        # If best score is very low, fall back to general
        if score < 0.15:
            return "general", 0.3, "No strong specialist match found, using general"

        reasoning = f"Selected {specialist_name}: " + "; ".join(reasons[:3]) if reasons else f"Default to {specialist_name}"

        return specialist_name, score, reasoning

    def _intent_matches_specialist(self, intent: str, specialist: str) -> bool:
        """Check if an intent matches a specialist."""
        # Healthcare provider intents
        if specialist == "healthcare_provider":
            return intent in [
                "coding_lookup", "claim_analysis", "reimbursement_check",
                "medical_necessity", "cci_edit"
            ]

        # Healthcare payer intents
        if specialist == "healthcare_payer":
            return intent in [
                "adjudication_logic", "utilization_management", "risk_adjustment",
                "quality_measures", "network_management"
            ]

        # Regulatory intents
        if specialist == "healthcare_regulatory":
            return intent in ["compliance_check", "regulatory_research"]

        # Clinical intents
        if specialist == "healthcare_clinical":
            return intent in ["clinical_reference", "drug_information", "lab_interpretation"]

        # Analytics intents
        if specialist == "healthcare_analytics":
            return intent in ["quality_measures", "risk_adjustment", "analysis"]

        # General intents
        if specialist == "research":
            return intent in ["research"]

        if specialist == "data_analytics":
            return intent in ["analysis"]

        if specialist == "software_engineering":
            return intent in ["troubleshooting", "how_to"]

        if specialist == "personal_assistant":
            return intent in ["planning", "how_to"]

        return False

    def _entity_matches_specialist(self, entity: Dict[str, str], specialist: str) -> bool:
        """Check if an entity is relevant to a specialist."""
        entity_type = entity.get("type", "")

        if specialist == "healthcare_provider":
            return entity_type in ["icd10", "cpt", "hcpcs", "npi", "monetary"]

        if specialist == "healthcare_pharmacy":
            return entity_type in ["ndc"]

        return False

    def _get_recommended_tools(
        self,
        specialist: str,
        intents: List[str]
    ) -> List[str]:
        """Get recommended tools based on specialist and intents."""
        tools = []

        # Get specialist's default tools
        if specialist in self.specialists:
            tools = self.specialists[specialist].get("tools", [])

        # Add intent-specific tools
        if "coding_lookup" in intents:
            tools.extend(["code_lookup", "cci_editor"])
        if "claim_analysis" in intents:
            tools.extend(["denial_analyzer", "edi_parser"])
        if "drug_information" in intents:
            tools.extend(["drug_reference", "medical_calculator"])
        if "lab_interpretation" in intents:
            tools.extend(["lab_interpreter"])
        if "calculation" in intents:
            tools.extend(["calculator", "medical_calculator"])
        if "research" in intents:
            tools.extend(["web_researcher", "summarizer"])

        return list(set(tools))  # Remove duplicates

    def list_specialists(self) -> List[Dict[str, Any]]:
        """List all available specialists."""
        return [
            {
                "name": name,
                "description": config["description"],
                "color": config["color"],
                "enabled": config["enabled"],
                "priority": config["priority"]
            }
            for name, config in self.specialists.items()
            if config.get("enabled", True)
        ]

    def get_specialist(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specialist details by name."""
        return self.specialists.get(name)


# Singleton instance
_router: Optional[AetheraRouter] = None


def get_router(config_path: str = "config.yaml") -> AetheraRouter:
    """Get or create the singleton router instance."""
    global _router
    if _router is None:
        _router = AetheraRouter(config_path)
    return _router
