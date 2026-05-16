"""
Aethera AI - Skill Registry

Discovers, loads, and manages all skills.

Startup:
1. Scan skills/builtin/, skills/healthcare/, skills/user/
2. Import all modules, find AetheraSkill subclasses
3. Register each with name, description, parameters

Runtime:
- Router queries registry: "which skills match this user intent?"
- Registry returns ranked list of relevant skills
- LLM receives tool definitions for selected skills
- LLM calls tools → Registry routes to skill.execute()
- Results returned to LLM for response generation

Slash commands in chat:
/skills              — list all available skills
/skills healthcare   — list healthcare skills
/skill info <name>   — show skill details
/skill run <name>    — force-run a specific skill
"""

import importlib
import inspect
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Type

from skills.skill_base import AetheraSkill


class SkillRegistry:
    """
    Discovers, loads, and manages all skills.
    Thread-safe singleton pattern.
    """

    _instance: Optional["SkillRegistry"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._skills: Dict[str, AetheraSkill] = {}
        self._categories: Dict[str, List[str]] = {}
        self._initialized = True

    def discover(self, base_path: Optional[Path] = None):
        """
        Discover and load all skills from standard directories.

        Args:
            base_path: Base path to skills directory. Defaults to ./skills
        """
        if base_path is None:
            base_path = Path(__file__).parent

        # Directories to scan
        scan_dirs = ["builtin", "healthcare", "user"]

        for dir_name in scan_dirs:
            dir_path = base_path / dir_name
            if not dir_path.exists():
                continue

            # Find all Python files
            for file_path in dir_path.glob("*.py"):
                if file_path.name.startswith("_"):
                    continue  # Skip __init__.py and private files

                try:
                    self._load_module(file_path, dir_name)
                except Exception as e:
                    print(f"Warning: Failed to load skill from {file_path}: {e}")

    def _load_module(self, file_path: Path, category: str):
        """Load a skill module and register any skills."""
        # Create module name from file path
        rel_path = file_path.relative_to(Path(__file__).parent)
        module_name = str(rel_path.with_suffix("")).replace(os.sep, ".")

        # Import module
        module = importlib.import_module(f"skills.{module_name}")

        # Find all AetheraSkill subclasses
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, AetheraSkill) and obj is not AetheraSkill:
                # Create instance and register
                try:
                    skill_instance = obj()
                    self.register(skill_instance)
                except Exception as e:
                    print(f"Warning: Failed to instantiate skill {name}: {e}")

    def register(self, skill: AetheraSkill):
        """
        Register a skill instance.

        Args:
            skill: AetheraSkill instance to register
        """
        name = skill.name
        self._skills[name] = skill

        # Add to category
        category = skill.category
        if category not in self._categories:
            self._categories[category] = []
        if name not in self._categories[category]:
            self._categories[category].append(name)

    def unregister(self, name: str):
        """Unregister a skill by name."""
        if name in self._skills:
            skill = self._skills[name]
            category = skill.category
            if category in self._categories:
                self._categories[category].remove(name)
            del self._skills[name]

    def get(self, name: str) -> Optional[AetheraSkill]:
        """Get a skill by name."""
        return self._skills.get(name)

    def list(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all registered skills.

        Args:
            category: Optional category filter

        Returns:
            List of skill info dictionaries
        """
        skills = []
        for name, skill in self._skills.items():
            if category and skill.category != category:
                continue
            skills.append({
                "name": name,
                "description": skill.description,
                "category": skill.category,
                "parameters": skill.parameters,
                "examples": skill.examples,
                "requires_phi_protection": skill.requires_phi_protection
            })
        return skills

    def list_categories(self) -> List[str]:
        """List all skill categories."""
        return list(self._categories.keys())

    def get_by_category(self, category: str) -> List[AetheraSkill]:
        """Get all skills in a category."""
        names = self._categories.get(category, [])
        return [self._skills[name] for name in names if name in self._skills]

    def get_tool_definitions(self) -> List[dict]:
        """Get OpenAI tool definitions for all skills."""
        return [skill.to_tool_definition() for skill in self._skills.values()]

    def get_tool_definition(self, name: str) -> Optional[dict]:
        """Get OpenAI tool definition for a specific skill."""
        skill = self.get(name)
        return skill.to_tool_definition() if skill else None

    async def execute(self, name: str, **kwargs) -> Any:
        """
        Execute a skill by name.

        Args:
            name: Skill name to execute
            **kwargs: Input parameters

        Returns:
            Skill result
        """
        skill = self.get(name)
        if not skill:
            raise ValueError(f"Skill not found: {name}")

        result = await skill.run(**kwargs)
        return result

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search skills by keyword matching.

        Args:
            query: Search query

        Returns:
            Ranked list of matching skills
        """
        query_lower = query.lower()
        matches = []

        for name, skill in self._skills.items():
            score = 0

            # Match against name
            if query_lower in name.lower():
                score += 10

            # Match against description
            if query_lower in skill.description.lower():
                score += 5

            # Match against category
            if query_lower in skill.category.lower():
                score += 3

            # Match against parameter names
            params = skill.parameters.get("properties", {})
            for param_name in params:
                if query_lower in param_name.lower():
                    score += 2

            if score > 0:
                matches.append({
                    "skill": name,
                    "score": score,
                    **self.list()[list(self._skills.keys()).index(name)]
                })

        # Sort by score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches


# Global registry instance
_registry: Optional[SkillRegistry] = None


def get_registry() -> SkillRegistry:
    """Get the global skill registry."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry


def discover_skills(base_path: Optional[Path] = None):
    """Discover and load all skills."""
    registry = get_registry()
    registry.discover(base_path)


def get_skill(name: str) -> Optional[AetheraSkill]:
    """Get a skill by name."""
    return get_registry().get(name)


def list_skills(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all skills."""
    return get_registry().list(category)
