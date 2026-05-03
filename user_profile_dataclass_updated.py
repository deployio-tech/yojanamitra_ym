"""
Updated UserProfile dataclass
Generated from new_profile_fields.json

Replace / extend your existing UserProfile dataclass with this version.
All legacy fields are preserved; new fields are appended at the end of each
section with a "# NEW" comment so they're easy to spot.

The eligibility engine reads from this dataclass after ProfileNormalizer runs.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class EducationEntry:
    education_level:   str            = ""       # "Class 10" | "Class 12" | "Graduation" …
    stream:            str            = ""
    status:            str            = ""       # "Completed" | "Pursuing" | "Dropped Out"
    percentage_marks:  Optional[float] = None
    year_of_passing:   Optional[int]  = None
    institute_type:    str            = ""       # "Government" | "Government-Aided" | "Private"


@dataclass
class DisabilityEntry:
    disability_type:       str            = ""
    disability_percentage: Optional[int]  = None


@dataclass
class LandParcel:
    area_in_acres: float = 0.0
    land_type:     str   = ""    # "Agricultural" | "Residential" | "Commercial"
    is_irrigated:  bool  = False


@dataclass
class FamilyMember:
    relation:      str  = ""     # "Spouse" | "Son" | "Daughter" | "Father" | "Mother"
    date_of_birth: str  = ""     # ISO date string
    is_alive:      bool = True


@dataclass
class UserProfile:
    # ── Core demographics ─────────────────────────────────────────────────────
    age:                        Optional[int]   = None
    gender:                     str             = ""     # "male" | "female" | "transgender"
    state:                      str             = ""
    caste:                      str             = ""     # normalised: "sc"|"st"|"obc"|"general"|"ews"|"minority"|"dnt"
    residence:                  str             = ""     # "rural" | "urban"
    religion:                   str             = ""
    marital_status:             str             = ""

    # ── Financial ─────────────────────────────────────────────────────────────
    annual_family_income:       int             = 0
    is_bpl:                     bool            = False
    has_bank_account:           bool            = False  # NEW

    # ── Disability ────────────────────────────────────────────────────────────
    is_disabled:                bool            = False
    disability_percentage:      int             = 0
    disability_entries:         List[DisabilityEntry] = field(default_factory=list)  # NEW

    # ── Occupation ────────────────────────────────────────────────────────────
    is_self_employed:           bool            = False
    is_farmer:                  bool            = False
    is_student:                 bool            = False
    occupation_type:            str             = ""     # NEW — "Construction Worker" | "Artisan" …
    employment_status:          str             = ""

    # ── Land ─────────────────────────────────────────────────────────────────
    land_owned_acres:           float           = 0.0
    is_landless:                bool            = False
    land_parcels:               List[LandParcel] = field(default_factory=list)  # NEW

    # ── Family ────────────────────────────────────────────────────────────────
    num_daughters:              int             = 0
    is_orphan:                  bool            = False
    family_members:             List[FamilyMember] = field(default_factory=list)  # NEW

    # ── Education ─────────────────────────────────────────────────────────────
    highest_education_level:    str             = ""
    education_entries:          List[EducationEntry] = field(default_factory=list)  # NEW

    # ── Residency ────────────────────────────────────────────────────────────
    state_of_domicile:          str             = ""     # NEW — full canonical name
    residence_location_type:    str             = ""     # NEW — "Rural" | "Urban"
    years_in_current_state:     Optional[int]   = None   # NEW

    # ── Special categories ────────────────────────────────────────────────────
    is_senior_citizen:          bool            = False
    is_widow:                   bool            = False
    is_tribal:                  bool            = False
    is_minority:                bool            = False
    is_bocw_registered:         bool            = False
    is_school_dropout:          bool            = False
    is_first_gen_student:       bool            = False
    is_pensioner:               bool            = False
    is_abandoned_woman:         bool            = False
    is_single_woman:            bool            = False
    is_acid_attack_survivor:    bool            = False
    is_migrant_worker:          bool            = False

    is_ex_serviceman_or_dependent:    bool      = False  # NEW
    is_shg_member:                    bool      = False  # NEW
    is_freedom_fighter_or_dependent:  bool      = False  # NEW

    # ── Health ────────────────────────────────────────────────────────────────
    has_critical_illness:       bool            = False  # NEW
    is_pregnant:                bool            = False  # NEW
    is_lactating_mother:        bool            = False  # NEW

    # ── Social category (v2, rich) ────────────────────────────────────────────
    social_category:            str             = ""     # NEW — raw value from dropdown

    # ── Assets ───────────────────────────────────────────────────────────────
    has_pucca_house:            bool            = False
    is_govt_employee:           bool            = False

    # ── Achievement ───────────────────────────────────────────────────────────
    achievement_certificates:   List[str]       = field(default_factory=list)

    # ── Derived / computed ────────────────────────────────────────────────────
    # These are set by ProfileNormalizer after all raw fields are loaded.
    age_band:                   str             = ""     # "child" | "youth" | "adult" | "senior"
    caste_category_tokens:      List[str]       = field(default_factory=list)  # NEW — ["sc","st"] etc.
