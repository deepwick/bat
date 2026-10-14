import os
import plistlib
import shutil
import subprocess
from pathlib import Path

import pytest

from deepwick_spec.ansi import SGR, runs, style_of
from deepwick_spec.check_port import check_port
from deepwick_spec.palette import load_palette

REPO = Path(__file__).resolve().parents[1]
SAMPLES = REPO.parent / "spec" / "samples"
PALETTE = load_palette()
C = PALETTE.colors

requires_bat = pytest.mark.skipif(shutil.which("bat") is None, reason="requires bat")
requires_delta = pytest.mark.skipif(shutil.which("delta") is None, reason="requires delta")


def hexof(name):
    return C[name].lower()


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
    result = subprocess.run(
        ["delta", "--config", str(gitconfig), "--true-color=always", "--paging=never"],
        input=diff, env=env, check=True, capture_output=True, text=True,
    )
    assert result.stderr == ""
    out = result.stdout
    assert style_of(out, "2")["fg"] == hexof("sage")
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
