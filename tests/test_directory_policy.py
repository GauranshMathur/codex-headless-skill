"""The Claude plugin directory refuses a plugin from an unverified organisation if a skill
pre-approves any tool beyond Read, Grep, Glob and LS (Bash included, even narrowed). Keep
the pre-approved list inside that set so a release is not blocked at publish time."""
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = {"Read", "Glob", "Grep", "LS"}


def _frontmatter(path):
    text = path.read_text()
    return re.match(r"---\n(.*?)\n---\n", text, re.S).group(1)


def test_skills_preapprove_only_read_only_tools():
    skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
    assert skills
    for skill in skills:
        block = re.search(r"^allowed-tools:\n((?:  - .*\n?)+)", _frontmatter(skill) + "\n", re.M)
        tools = re.findall(r"  - (.*)", block.group(1)) if block else []
        assert set(tools) <= ALLOWED, f"{skill.relative_to(ROOT)} pre-approves {sorted(set(tools) - ALLOWED)}"


def test_icon_is_a_square_png_the_directory_accepts():
    icon = ROOT / ".claude-plugin" / "icon.png"
    data = icon.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    assert width == height and 512 <= width <= 2048
    assert len(data) < 2 * 1024 * 1024
