from pathlib import Path

import yaml

# Default constitutional rules
DEFAULT_CONSTITUTION = """
## Team Mission
Provide honest, calibrated intelligence to support decision-making.

## Core Rules
1. EPISTEMIC HONESTY: Never state speculation as fact. Tag uncertain claims with [SPECULATION].
2. CONFIDENCE CALIBRATION: Always express confidence as 0.0-1.0. Never omit.
3. BAD NEWS FIRST: Surface risks and negative signals before positive ones.
4. UNCERTAINTY ACKNOWLEDGMENT: "I don't know" is a valid and required answer when uncertain.
5. NO HALLUCINATION: If you cannot verify a claim, say so explicitly.

## Epistemic Honesty
- Distinguish between observed facts and inferences
- Quantify uncertainty where possible
- Challenge your own assumptions before presenting conclusions

## Agent SOUL.md Contract
Each agent must have a SOUL.md defining: Mission, Persona, Values, Hard Constraints, Tools, Collaboration.
All agents inherit these Core Rules. SOUL.md may add constraints but not remove them.
"""


class Constitution:
    def __init__(self, text: str):
        self.text = text

    @classmethod
    def default(cls) -> "Constitution":
        return cls(DEFAULT_CONSTITUTION)

    @classmethod
    def from_file(cls, path: str | Path) -> "Constitution":
        """Load from a CONSTITUTION.md or plain text file."""
        path = Path(path)
        try:
            return cls(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise ValueError(f"Constitution file not found: {path}")

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Constitution":
        """Load from YAML config file with 'constitution' key."""
        path = Path(path)
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise ValueError(f"YAML file not found: {path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}")
        text = data.get("constitution", "") if isinstance(data, dict) else ""
        if not text:
            raise ValueError(f"No 'constitution' key found in {path}")
        return cls(text)

    @classmethod
    def from_soul_md(cls, path: str | Path) -> "Constitution":
        """Extract constitution from a SOUL.md file (looks for ## Hard Constraints section)."""
        path = Path(path)
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
        capturing = False
        section_lines = []
        for line in lines:
            if line.strip().startswith("## Hard Constraints"):
                capturing = True
                section_lines.append(line)
                continue
            if capturing:
                # Stop at the next ## section heading
                if line.startswith("## ") and section_lines:
                    break
                section_lines.append(line)
        if section_lines:
            return cls("\n".join(section_lines).strip())
        # Fallback: return full file
        return cls(content)

    def as_prompt(self) -> str:
        """Return constitution text formatted for injection into system prompt."""
        return f"[CONSTITUTIONAL RULES]\n{self.text}\n[END CONSTITUTIONAL RULES]"

    def merge(self, other: "Constitution") -> "Constitution":
        """Merge two constitutions (combine their texts)."""
        return Constitution(self.text + "\n\n" + other.text)
