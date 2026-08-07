"""
modules/dummy_data_engine/application/services/synthetic_identity_factory.py
==============================================================================
Sub-Module 3.1 — Synthetic Identity & Demographics Factory.
Source of truth: ARCHITECTURE.md §3.1

Generates realistic student/staff/parent identity records using Faker(en_IN)
with custom providers for Indian phone formats and school-appropriate age ranges.

Dependencies: NONE (pure generation utility — trivially unit-testable).
"""
from __future__ import annotations

import logging
import random
from datetime import date, timedelta
from uuid import uuid4

from faker import Faker

from modules.dummy_data_engine.domain.dtos import (
    Gender,
    GenerateIdentitiesRequestDTO,
    SyntheticIdentityDTO,
)

logger = logging.getLogger(__name__)

# Weighted distributions matching real Indian school demographics
_GENDER_WEIGHTS = {Gender.MALE: 0.52, Gender.FEMALE: 0.47, Gender.OTHER: 0.01}
_BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
_BLOOD_WEIGHTS = [0.28, 0.07, 0.23, 0.02, 0.06, 0.01, 0.30, 0.03]
_GUARDIAN_RELATIONS = ["Father", "Mother", "Guardian"]
_GUARDIAN_WEIGHTS = [0.50, 0.38, 0.12]

# Grade-level → student age band (grade 10 = 14–16 years)
_GRADE_AGE_BANDS: dict[int, tuple[int, int]] = {
    1: (5, 7), 2: (6, 8), 3: (7, 9), 4: (8, 10), 5: (9, 11),
    6: (10, 12), 7: (11, 13), 8: (12, 14), 9: (13, 15), 10: (14, 16),
    11: (15, 17), 12: (16, 18),
}


def _indian_mobile(faker: Faker) -> str:
    """Generate a realistic Indian mobile number (+91 XXXXX-XXXXX)."""
    prefix = random.choice([
        "6", "7", "8", "9",
        "70", "72", "73", "74", "75", "76", "77", "78", "79",
        "80", "82", "83", "84", "85", "86", "87", "88", "89",
        "90", "91", "92", "93", "94", "95", "96", "97", "98", "99",
    ])
    number = prefix + "".join([str(random.randint(0, 9)) for _ in range(10 - len(prefix))])
    return f"+91-{number[:5]}-{number[5:]}"


def _dob_for_grade(grade_level: int, reference_date: date | None = None) -> date:
    """Generate a DOB appropriate for the given grade level. grade_level=0 means staff (25-55)."""
    ref = reference_date or date.today()
    if grade_level == 0:
        # Staff: age 25–55
        age_years = random.randint(25, 55)
    else:
        min_age, max_age = _GRADE_AGE_BANDS.get(grade_level, (10, 16))
        age_years = random.randint(min_age, max_age)
    age_days = age_years * 365 + random.randint(0, 364)
    return ref - timedelta(days=age_days)


class SyntheticIdentityFactory:
    """
    Sub-Module 3.1: Generates statistically realistic identity records.
    Pure generation utility — no DB interaction, no side effects.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._seed = seed
        self._faker = Faker(["en_IN", "en_US"])
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)
        logger.debug("SyntheticIdentityFactory initialized (seed=%s)", seed)

    def _pick_gender(self) -> Gender:
        genders = list(_GENDER_WEIGHTS.keys())
        weights = list(_GENDER_WEIGHTS.values())
        return random.choices(genders, weights=weights, k=1)[0]

    def _pick_blood_group(self) -> str:
        return random.choices(_BLOOD_GROUPS, weights=_BLOOD_WEIGHTS, k=1)[0]

    def _make_name(self, gender: Gender) -> str:
        if gender == Gender.FEMALE:
            return self._faker.name_female()
        elif gender == Gender.MALE:
            return self._faker.name_male()
        return self._faker.name()

    def generate_student_identities(
        self,
        count: int,
        grade_level: int = 10,
    ) -> list[SyntheticIdentityDTO]:
        """
        Generate `count` student identity records for the given grade level.
        Each record includes a guardian identity cross-linked via guardian_name/phone.
        """
        identities = []
        for _ in range(count):
            gender = self._pick_gender()
            full_name = self._make_name(gender)
            dob = _dob_for_grade(grade_level)
            phone = _indian_mobile(self._faker)
            email = (
                full_name.lower().replace(" ", ".")
                + str(random.randint(10, 99))
                + "@student.greenwoodhigh.edu.in"
            )
            guardian_relation = random.choices(
                _GUARDIAN_RELATIONS, weights=_GUARDIAN_WEIGHTS, k=1
            )[0]
            guardian_name = self._make_name(
                Gender.FEMALE if guardian_relation == "Mother" else Gender.MALE
            )
            guardian_phone = _indian_mobile(self._faker)

            identity = SyntheticIdentityDTO(
                identity_id=uuid4(),
                full_name=full_name,
                dob=dob,
                gender=gender,
                phone=phone,
                email=email,
                address=self._faker.address().replace("\n", ", "),
                blood_group=self._pick_blood_group(),
                guardian_name=guardian_name,
                guardian_phone=guardian_phone,
                guardian_relation=guardian_relation,
            )
            identities.append(identity)

        logger.info(
            "Generated %d student identities for grade %d", count, grade_level
        )
        return identities

    def generate_staff_identities(
        self,
        count: int,
        department: str = "General",
    ) -> list[SyntheticIdentityDTO]:
        """Generate `count` staff identity records."""
        identities = []
        for _ in range(count):
            gender = self._pick_gender()
            full_name = self._make_name(gender)
            phone = _indian_mobile(self._faker)
            email = (
                full_name.lower().split()[0]
                + "."
                + full_name.lower().split()[-1]
                + "@greenwoodhigh.edu.in"
            )
            identity = SyntheticIdentityDTO(
                identity_id=uuid4(),
                full_name=full_name,
                dob=_dob_for_grade(grade_level=0),   # staff age 25–55
                gender=gender,
                phone=phone,
                email=email,
                address=self._faker.address().replace("\n", ", "),
                blood_group=self._pick_blood_group(),
            )
            identities.append(identity)

        logger.info("Generated %d staff identities (%s)", count, department)
        return identities

    def generate_guardian_identity(
        self,
        student_identity: SyntheticIdentityDTO,
    ) -> SyntheticIdentityDTO:
        """Generate a guardian identity cross-linked to an existing student."""
        gender = (
            Gender.FEMALE
            if student_identity.guardian_relation == "Mother"
            else Gender.MALE
        )
        return SyntheticIdentityDTO(
            identity_id=uuid4(),
            full_name=student_identity.guardian_name or self._make_name(gender),
            dob=_dob_for_grade(grade_level=0),
            gender=gender,
            phone=student_identity.guardian_phone or _indian_mobile(self._faker),
            email=f"parent.{student_identity.full_name.lower().replace(' ', '.')}@gmail.com",
            address=student_identity.address,
            blood_group=self._pick_blood_group(),
        )
