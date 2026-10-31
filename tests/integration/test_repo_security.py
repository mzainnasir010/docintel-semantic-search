"""Repository security regression checks for secrets and sample-document attribution."""

from scripts.security_check import ROOT, audit_repository


def test_repository_has_no_tracked_env_or_obvious_key_patterns() -> None:
    assert audit_repository(ROOT) == []
