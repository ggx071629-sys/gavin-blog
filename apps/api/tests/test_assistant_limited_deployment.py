import json

import pytest
from pydantic import ValidationError

from app.assistant_qualification.profile import QualificationProfile, canonical_profile
from tests.test_assistant_qualification_profile import valid_profile_data


def limited_data():
    data = valid_profile_data()
    data["schema_version"] = 4
    data["host"]["memory_mib"] = 3655
    data["backup"]["frequency_seconds"] = 0
    data["observability"]["provider_account_budget_alert_configured"] = False
    data["thresholds"]["scenarios"] = ["cold_start", "idle", "api_restart"]
    data["limited_validation"] = {
        "approval": data["approval"],
        "qualification_status": "NOT_FULLY_QUALIFIED",
        "accepted_gaps": [
            "reduced-host-memory",
            "scheduled-off-host-backup",
            "provider-account-budget-alert",
            "long-duration-resource-validation",
        ],
    }
    return data


def test_limited_profile_truthfully_binds_accepted_omissions():
    profile = QualificationProfile.model_validate(limited_data())
    assert profile.host.memory_mib == 3655
    assert profile.backup.frequency_seconds == 0
    assert (
        json.loads(canonical_profile(profile))["limited_validation"]["qualification_status"]
        == "NOT_FULLY_QUALIFIED"
    )


@pytest.mark.parametrize("mutation", ["approval", "gap", "memory", "secret", "dimension"])
def test_limited_profile_does_not_bypass_safety(mutation):
    data = limited_data()
    if mutation == "approval":
        data.pop("limited_validation")
    elif mutation == "gap":
        data["limited_validation"]["accepted_gaps"].pop()
    elif mutation == "memory":
        data["thresholds"]["max_total_rss_mib"] = 3200
    elif mutation == "secret":
        data["secrets"]["readiness"] = data["secrets"]["csrf"]
    else:
        data["qdrant"]["vector_dimension"] = 8
    with pytest.raises(ValidationError):
        QualificationProfile.model_validate(data)


@pytest.mark.parametrize("version", [2, 3])
def test_full_profiles_retain_requirements_and_canonical_shape(version):
    old = valid_profile_data()
    old["schema_version"] = version
    assert "limited_validation" not in json.loads(
        canonical_profile(QualificationProfile.model_validate(old))
    )
    for section, name, value in [
        ("host", "memory_mib", 3655),
        ("backup", "frequency_seconds", 0),
        ("observability", "provider_account_budget_alert_configured", False),
    ]:
        data = valid_profile_data()
        data["schema_version"] = version
        data[section][name] = value
        with pytest.raises(ValidationError):
            QualificationProfile.model_validate(data)
