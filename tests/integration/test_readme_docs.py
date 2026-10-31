"""README structure, environment documentation, and architecture checks."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"

EXPECTED_SECTIONS = [
    "Project Overview",
    "Business Problem",
    "Features",
    "Architecture",
    "Technology Stack",
    "Installation",
    "Configuration",
    "Usage",
    "Example Queries",
    "Evaluation",
    "Screenshots",
    "Limitations",
    "Future Improvements",
]


def test_readme_has_the_required_13_sections_in_order() -> None:
    readme = README.read_text(encoding="utf-8")
    sections = re.findall(r"^## \d+\. (.+)$", readme, flags=re.MULTILINE)
    assert sections == EXPECTED_SECTIONS


def test_every_env_example_variable_is_documented_in_configuration_table() -> None:
    readme = README.read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    variables = [
        line.split("=", maxsplit=1)[0]
        for line in env_example.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    config_section = readme.split("## 7. Configuration", maxsplit=1)[1].split("## 8.", maxsplit=1)[0]
    missing = [name for name in variables if f"| `{name}` |" not in config_section]
    assert not missing, f"README configuration table is missing: {missing}"


def test_readme_embeds_the_architecture_pipelines_and_vector_database() -> None:
    readme = README.read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    for token in ("Pipeline A", "Pipeline B", "ChromaDB", "FastAPI", "Gemini"):
        assert token in architecture
        assert token in readme
    assert "```mermaid" in readme
