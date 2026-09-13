"""Settings.deployed_commit — RENDER_GIT_COMMIT을 short SHA로 줄인다."""

from lions_core.config import Settings


def test_short_sha_from_full_commit():
    assert Settings(render_git_commit="126d3f5aa1b2c3d4e5f6").deployed_commit == "126d3f5"


def test_none_when_not_deployed():
    assert Settings().deployed_commit is None


def test_none_when_blank_or_whitespace():
    assert Settings(render_git_commit="   ").deployed_commit is None


def test_reads_the_render_environment_variable(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "deadbeefcafe")

    assert Settings().deployed_commit == "deadbee"
