"""Regression checks for deployment arguments that CI cannot parse offline."""

from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml"


def test_retrieval_env_vars_use_non_comma_delimiter():
    """CORS contains commas, so gcloud's default comma delimiter is invalid."""
    workflow = WORKFLOW.read_text(encoding="utf-8")
    retrieval_step = workflow.split("- name: Deploy retrieval-api", 1)[1]
    env_arg = retrieval_step.split("--set-env-vars=", 1)[1].splitlines()[0]

    assert env_arg.startswith('"^|^')
    assert "|CORS_ALLOWED_ORIGINS=" in env_arg
    assert "|INGEST_URL=" in env_arg
