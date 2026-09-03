"""
Profile Completion Guard.
Verifies whether a student has completed their academic credentials onboarding.
"""
from __future__ import annotations


def is_profile_complete(profile: dict | None) -> bool:
    if not profile or not isinstance(profile, dict):
        return False

    name = (profile.get("name") or "").strip()
    email = (profile.get("email") or "").strip()
    major = (profile.get("field_of_study") or "").strip()
    inst = (profile.get("university") or "").strip()
    target = (profile.get("target_degree") or profile.get("academic_level") or "").strip()

    # Must have name, email, institution, major, and target degree level
    if not (name and email and major and inst and target):
        return False

    # For undergraduate, should have secondary school/college and GPA or result
    gpa = profile.get("gpa")
    ssc = profile.get("ssc_result")
    hsc = profile.get("hsc_result")

    # If gpa is present, or ssc/hsc is present
    has_academic_record = bool(gpa or ssc or hsc)
    return has_academic_record
