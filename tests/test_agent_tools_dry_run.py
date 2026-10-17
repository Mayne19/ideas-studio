"""Outil d'essai à blanc : domaines enregistrés et sources admissibles."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "agent_tools_dry_run", Path(__file__).resolve().parents[1] / "scripts" / "agent_tools_dry_run.py")
dry_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dry_run)


def test_cdc_subdomains_count_as_one_registered_domain():
    urls = ["https://www.cdc.gov/yellow-book/x.html", "https://cdc.gov/travel", "https://wwwnc.cdc.gov/travel/page/jet-lag"]
    assert {dry_run.domain_of(u) for u in urls} == {"cdc.gov"}
    assert all(dry_run.admissible(u) for u in urls)


def test_nhs_uk_is_recognised_as_admissible():
    assert dry_run.domain_of("https://www.nhs.uk/conditions/jet-lag/") == "nhs.uk"
    assert dry_run.admissible("https://www.nhs.uk/conditions/jet-lag/")
    assert not dry_run.admissible("https://www.boots.com/healthhub/jet-lag")


def test_registered_domain_matches_the_validator():
    assert dry_run.domain_of("https://presse.inserm.fr/a") == "inserm.fr" and dry_run.admissible("https://presse.inserm.fr/a")
    assert dry_run.domain_of("https://sante.gouv.fr/x") == "sante.gouv.fr" and dry_run.admissible("https://sante.gouv.fr/x")
    assert dry_run.domain_of("https://notcdc.gov.example.com/") == "example.com"
