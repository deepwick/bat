import os
import plistlib
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from deepwick_spec.check_port import check_port
from deepwick_spec.palette import load_palette

REPO = Path(__file__).resolve().parents[1]
SAMPLES = REPO.parent / "spec" / "samples"
PALETTE = load_palette()
C = PALETTE.colors
SGR = re.compile(r"\x1b\[([0-9;]*)m")

requires_bat = pytest.mark.skipif(shutil.which("bat") is None, reason="requires bat")
requires_delta = pytest.mark.skipif(shutil.which("delta") is None, reason="requires delta")


def hexof(name):
    return C[name].lower()


def runs(text):
    """Split ANSI output into (text, style) runs; style tracks 24-bit fg/bg, bold, italic."""
    blank = {"fg": None, "bg": None, "bold": False, "italic": False}
    style, out, pos = dict(blank), [], 0
    for m in SGR.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], dict(style)))
        params = [int(p) if p else 0 for p in m.group(1).split(";")]
        i = 0
        while i < len(params):
            p = params[i]
            if p == 0:
                style = dict(blank)
            elif p == 1:
                style["bold"] = True
            elif p == 3:
                style["italic"] = True
            elif p in (38, 48) and params[i + 1 : i + 2] == [2]:
                r, g, b = params[i + 2 : i + 5]
                style["fg" if p == 38 else "bg"] = f"#{r:02x}{g:02x}{b:02x}"
                i += 4
            i += 1
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], dict(style)))
    return out


def style_of(text, token):
    for chunk, style in runs(text):
        if chunk.strip() == token:
            return style
    raise AssertionError(f"no run equal to {token!r}")


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    root = tmp_path_factory.mktemp("bat")
    config = root / "config"
    (config / "themes").mkdir(parents=True)
    shutil.copy(REPO / "Deepwick.tmTheme", config / "themes")
    environment = {
        **os.environ,
        "BAT_CONFIG_DIR": str(config),
        "BAT_CONFIG_PATH": str(root / "no-config"),
        "BAT_CACHE_PATH": str(root / "xdg-cache" / "bat"),
        "XDG_CACHE_HOME": str(root / "xdg-cache"),
    }
    subprocess.run(["bat", "cache", "--build"], env=environment, check=True, capture_output=True)
    return environment


def bat(env, path):
    return subprocess.run(
        ["bat", "--color=always", "--theme=Deepwick", "--italic-text=always", "--style=plain", "--paging=never", str(path)],
        env=env, check=True, capture_output=True, text=True,
    ).stdout


def test_theme_is_valid_plist_named_deepwick():
    with open(REPO / "Deepwick.tmTheme", "rb") as f:
        theme = plistlib.load(f)
    assert theme["name"] == "Deepwick"
    globals_ = theme["settings"][0]["settings"]
    assert globals_["background"] == C["background"]
    assert globals_["foreground"] == C["foreground"]
    assert globals_["selection"] == C["selection"]
    assert globals_["lineHighlight"] == C["surface"]


@requires_bat
def test_bat_lists_theme(env):
    themes = subprocess.run(["bat", "--list-themes", "--color=never"], env=env, check=True, capture_output=True, text=True).stdout
    assert "Deepwick" in themes.splitlines()


@requires_bat
@pytest.mark.parametrize(
    ("token", "color", "italic"),
    [
        ("Escape sequences and f-strings", "comment", True),
        ("def", "blue", False),
        ("class", "blue", False),
        ("Mood", "teal", False),
        ("say_hello", "yellow", False),
        ("if", "magenta", False),
        ("import", "magenta", False),
        ("3", "sage", False),
        ("no one to greet", "orange", False),
    ],
)
def test_python_sample_roles(env, token, color, italic):
    style = style_of(bat(env, SAMPLES / "sample.py"), token)
    assert style["fg"] == hexof(color)
    assert style["italic"] is italic


@requires_bat
def test_python_escape_is_gold(env):
    out = bat(env, SAMPLES / "sample.py")
    escapes = [style for chunk, style in runs(out) if chunk.startswith("\\n")]
    assert escapes and escapes[0]["fg"] == hexof("gold")


@requires_bat
def test_typescript_interface_is_mint_and_regex_is_rose(env):
    out = bat(env, SAMPLES / "sample.ts")
    assert style_of(out, "Greeter")["fg"] in (hexof("mint"), hexof("teal"))
    regex = [style for chunk, style in runs(out) if "hello," in chunk]
    assert regex and regex[0]["fg"] == hexof("rose")


@requires_bat
@requires_delta
def test_delta_feature_uses_diff_backgrounds(env, tmp_path):
    (tmp_path / "a.py").write_text("x = 1\nname = 'a'\n")
    (tmp_path / "b.py").write_text("x = 2\nname = 'a'\n")
    gitconfig = tmp_path / "gitconfig"
    gitconfig.write_text(f"[include]\n    path = {REPO / 'deepwick.gitconfig'}\n[delta]\n    features = deepwick\n")
    diff = subprocess.run(
        ["git", "diff", "--no-index", "--no-color", "a.py", "b.py"],
        cwd=tmp_path, capture_output=True, text=True,
    ).stdout
    out = subprocess.run(
        ["delta", "--config", str(gitconfig), "--true-color=always", "--paging=never"],
        input=diff, env=env, check=True, capture_output=True, text=True,
    ).stdout
    backgrounds = {style["bg"] for _, style in runs(out)}
    for name in ("diffAdded", "diffRemoved", "diffAddedEmph", "diffRemovedEmph"):
        assert hexof(name) in backgrounds, name


def test_port_conventions():
    assert check_port(REPO, PALETTE.allowed_hex()) == []


@requires_bat
def test_python_decorator_is_function_color(env):
    line = next(l for l in bat(env, SAMPLES / "sample.py").splitlines() if SGR.sub("", l).strip() == "@dataclass")
    colors = {style["fg"] for chunk, style in runs(line) if chunk.strip()}
    assert colors == {hexof("yellow")}


@requires_bat
def test_python_logical_operators_are_foreground(env):
    out = bat(env, SAMPLES / "sample.py")
    assert style_of(out, "and")["fg"] == hexof("foreground")
