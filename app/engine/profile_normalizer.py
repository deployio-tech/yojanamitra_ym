import json, logging, os
from typing import Any, Optional

logger = logging.getLogger(__name__)

class ProfileNormalizer:
    _instance = None

    def __init__(self, registry_path: Optional[str] = None):
        if registry_path is None:
            registry_path = os.path.join(
                os.path.dirname(__file__), '..', '..', 'profile_field_registry.json'
            )
        with open(registry_path) as f:
            self.registry = json.load(f)

        self.form_to_canonical: dict[str, str] = {}
        for canonical, data in self.registry.get('profile_fields', {}).items():
            self.form_to_canonical[canonical] = canonical
            for mapping in data.get('form_mappings', []):
                self.form_to_canonical[mapping] = canonical

    @classmethod
    def get_instance(cls) -> 'ProfileNormalizer':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    def normalize(self, raw_profile: dict) -> dict:
        if not raw_profile:
            return {}

        normalized = {}
        conflicts = {}

        for key, value in raw_profile.items():
            canonical = self.form_to_canonical.get(key, key)
            if canonical in normalized:
                conflicts.setdefault(canonical, []).append(key)
                if key == canonical:
                    normalized[canonical] = value
            else:
                normalized[canonical] = value

        if conflicts:
            for canonical, dupes in conflicts.items():
                logger.warning(
                    "Profile normalization conflict: multiple keys map to '%s': %s. "
                    "snake_case value used.", canonical, dupes
                )

        return normalized

    def validate(self) -> list[str]:
        issues = []
        mapping_to_fields: dict[str, str] = {}

        for canonical, data in self.registry.get('profile_fields', {}).items():
            for mapping in data.get('form_mappings', []):
                if mapping in mapping_to_fields:
                    issues.append(
                        f"Duplicate mapping '{mapping}' in both "
                        f"'{mapping_to_fields[mapping]}' and '{canonical}'"
                    )
                else:
                    mapping_to_fields[mapping] = canonical

            for derived_field in data.get('derives', {}).keys():
                if derived_field not in self.registry.get('profile_fields', {}):
                    issues.append(
                        f"'{canonical}' derives '{derived_field}' "
                        f"which is not a registered field"
                    )

        return issues
