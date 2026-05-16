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
import logging
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Type

from skills.skill_base import AetheraSkill

logger = logging.getLogger("aethera.skills.registry")


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
        self._lock = threading.Lock()
        self._skill_files: Dict[str, Path] = {}  # name -> source file path
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
                    self._skill_files[skill_instance.name] = file_path
                except Exception as e:
                    logger.warning(f"Failed to instantiate skill {name}: {e}")

    def register(self, skill: AetheraSkill):
        """
        Register a skill instance.

        Args:
            skill: AetheraSkill instance to register
        """
        with self._lock:
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
        with self._lock:
            if name in self._skills:
                skill = self._skills[name]
                category = skill.category
                if category in self._categories and name in self._categories[category]:
                    self._categories[category].remove(name)
                    if not self._categories[category]:
                        del self._categories[category]
                del self._skills[name]
                self._skill_files.pop(name, None)

    def register_dynamic_skill(self, skill: AetheraSkill, file_path: Optional[Path] = None):
        """
        Register a dynamically created skill and optionally track its file.

        Args:
            skill: AetheraSkill instance to register
            file_path: Optional path to the skill's source file
        """
        self.register(skill)
        if file_path:
            with self._lock:
                self._skill_files[skill.name] = file_path
        logger.info(f"Registered dynamic skill: {skill.name} (source={skill.source})")

    def hot_reload(self) -> Dict[str, Any]:
        """
        Hot-reload user-created skills from disk.

        Invalidates import caches, re-scans skills/user/ directory,
        and registers any new or modified skills.

        Returns:
            Dict with 'added', 'removed', 'updated' skill lists
        """
        with self._lock:
            old_names = set(self._skills.keys())

        # Invalidate import caches so modified modules reload
        importlib.invalidate_caches()

        # Re-discover from user directory
        base_path = Path(__file__).parent
        user_dir = base_path / "user"
        if not user_dir.exists():
            return {"added": [], "removed": [], "updated": [], "total": len(old_names)}

        # Remove existing user skills first
        with self._lock:
            user_skills = dict(self._categories.get("user", []))
            user_skill_names = list(self._categories.get("user", []))
            for name in user_skill_names:
                if name in self._skills:
                    del self._skills[name]
                self._skill_files.pop(name, None)
            if "user" in self._categories:
                del self._categories["user"]

        # Re-discover
        for file_path in user_dir.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
            try:
                # Force reimport by removing from sys.modules
                rel_path = file_path.relative_to(base_path)
                module_name = str(rel_path.with_suffix("")).replace(os.sep, ".")
                full_module = f"skills.{module_name}"
                if full_module in importlib.sys.modules:
                    del importlib.sys.modules[full_module]
                self._load_module(file_path, "user")
            except Exception as e:
                logger.warning(f"Failed to hot-reload skill from {file_path}: {e}")

        with self._lock:
            new_names = set(self._skills.keys())

        added = list(new_names - old_names)
        removed = list(old_names - new_names)
        # Updated = re-registered skills that existed before
        updated = [n for n in added if n in user_skill_names]

        logger.info(f"Hot-reload complete: {len(added)} added, {len(removed)} removed, {len(updated)} updated")
        return {
            "added": added,
            "removed": removed,
            "updated": updated,
            "total": len(new_names),
        }

    def reload_skill(self, name: str) -> bool:
        """
        Reload a specific skill by name.

        Args:
            name: Skill name to reload

        Returns:
            True if skill was found and reloaded, False otherwise
        """
        with self._lock:
            file_path = self._skill_files.get(name)

        if not file_path or not file_path.exists():
            logger.warning(f"Cannot reload skill {name}: source file not found")
            return False

        # Remove old registration
        self.unregister(name)

        # Force reimport
        rel_path = file_path.relative_to(Path(__file__).parent)
        module_name = str(rel_path.with_suffix("")).replace(os.sep, ".")
        full_module = f"skills.{module_name}"
        if full_module in importlib.sys.modules:
            del importlib.sys.modules[full_module]

        importlib.invalidate_caches()

        # Reload
        category = "user" if "user" in str(file_path) else ("healthcare" if "healthcare" in str(file_path) else "builtin")
        try:
            self._load_module(file_path, category)
            logger.info(f"Reloaded skill: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to reload skill {name}: {e}")
            return False

    def reload_user_skills(self) -> Dict[str, Any]:
        """
        Remove all user-category skills and re-discover from skills/user/.

        Returns:
            Dict with 'added', 'removed', 'total' counts
        """
        return self.hot_reload()

    def get_user_skills(self) -> List[AetheraSkill]:
        """Get all user-created skills."""
        return self.get_by_category("user")

    def get_skill_file_path(self, name: str) -> Optional[Path]:
        """Get the source file path for a skill."""
        with self._lock:
            return self._skill_files.get(name)

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
