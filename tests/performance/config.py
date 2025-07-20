"""Performance test configuration utilities."""

import tomllib
from pathlib import Path
from typing import Dict


def get_performance_thresholds() -> Dict[str, float]:
    """Read performance thresholds from pyproject.toml.

    Returns:
        Dict containing performance threshold values with fallback defaults.
    """
    # Default fallback values
    defaults = {
        "unflare_cache_hit_speedup": 10.0,
        "direct_request_timeout": 5.0,
        "unflare_first_request_max": 30.0,
    }

    try:
        # Find pyproject.toml in the project root
        project_root = Path(__file__).parent.parent.parent
        pyproject_path = project_root / "pyproject.toml"

        if not pyproject_path.exists():
            return defaults

        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        # Extract performance thresholds
        thresholds = pyproject_data.get("tool", {}).get("performance-thresholds", {})

        # Merge with defaults (config overrides defaults)
        result = defaults.copy()
        result.update(thresholds)

        return result

    except (OSError, ValueError, KeyError):
        # Return defaults if any error occurs reading config
        return defaults
