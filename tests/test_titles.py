import pytest

from jobradar.common import title_matches


@pytest.mark.parametrize("title", [
    "Application Security Engineer",
    "Senior AppSec Engineer (m/w/d)",
    "Product Security Engineer",
    "Penetration Tester",
    "Senior Penetration Testing Consultant",
    "Pentester - Web & Mobile",
    "Security Consultant (Application Security)",
    "Threat Modeling Lead",
    "Offensive Security Consultant",
    "VAPT Specialist",
])
def test_included(title):
    assert title_matches(title)


@pytest.mark.parametrize("title", [
    "Cloud Security Engineer",
    "AI Security Engineer",
    "Red Team Operator",
    "Red Teamer",
    "Principal Application Security Engineer",
    "VP, Product Security",
    "Director of Security Engineering",
    "Head of AppSec",
    "SOC Analyst",
    "Application Security Manager",
    "Cloud Engineer",          # old config matched "cloud"
    "Employment Laws Advisor", # old config matched "aws" inside "laws"
    "Software Engineer",
])
def test_excluded(title):
    assert not title_matches(title)


@pytest.mark.parametrize("title", [
    "Master Thesis: Next-Generation Platform Engineering for DevSecOps",
    "Working Student, Security Engineer",
    "Werkstudent IT-Security (m/w/d)",
    "Security Engineering Intern",
])
def test_students_excluded(title):
    assert not title_matches(title)


@pytest.mark.parametrize("title", ["Penetrationstester (m/w/d)", "Ethical Hacker", "Pentestare till Knowit"])
def test_native_language_titles(title):
    assert title_matches(title)
