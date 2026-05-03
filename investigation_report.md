# Deep Extraction Investigation
**Total successful extractions found:** 1718

## SCHEME: Maintenance Of Pregnant Desi/Indigenous Cow/Buffalo Ration Scheme For BPL Families Belonging To Scheduled Caste (SC) Category (ID: 1345)
### Original Text
**Description:** The scheme “**Maintenance of Pregnant Desi/Indigenous Cow/Buffalo Ration Scheme for BPL families belonging to Scheduled Caste (SC) category**” had been launched by the Department of Animal Husbandry, Government of Himachal Pradesh with the aim to provides a 50% subsidy on a balanced ration for pregn...
**Eligibility:**
```text
1. The beneficiary should be a permanent resident of Himachal Pradesh.
   1. Livestock owners belonging to BPL of Scheduled Caste category families rearing Desi/Indigenous/crossbred cows or buffaloes are eligible under the scheme.
   1. The subsidy will be provided to each BPL of Scheduled Caste category families for a maximum of up to two Desi/Indigenous cows/their crosses or buffaloes.
```
### Extracted Conditions (Pass 2 JSON)
```json
{
  "caste_category": [
    "SC"
  ],
  "is_bpl": true,
  "domicile_state": [
    "Himachal Pradesh"
  ],
  "occupation": [
    "farmer"
  ],
  "is_farmer": true,
  "is_individual_scheme": true,
  "custom_verification_required": true,
  "custom_verification_reason": "Do you currently own a Desi, Indigenous, or Crossbred cow or buffalo that is in its last trimester of pregnancy?",
  "extraction_confidence": "high",
  "extraction_notes": "Maintained SC category, BPL status, and Himachal Pradesh domicile constraints from Pass 1. Refined custom_verification_reason to a specific Yes/No question regarding the ownership of a pregnant animal in its last trimester to prevent ineligible applicants (those without livestock or whose livestock is not in the correct pregnancy stage) from passing the filter.",
  "conditions_found_in": [
    "name",
    "eligibility",
    "category"
  ]
}
```
**Critic's Notes:** Maintained SC category, BPL status, and Himachal Pradesh domicile constraints from Pass 1. Refined custom_verification_reason to a specific Yes/No question regarding the ownership of a pregnant animal in its last trimester to prevent ineligible applicants (those without livestock or whose livestock is not in the correct pregnancy stage) from passing the filter.
---

## SCHEME: Opening and Maintenance of Boys and Girls Hostels (ID: 254)
### Original Text
**Description:** The scheme "Opening and Maintenance of Boys and Girls Hostels” by the Adi Dravidar Welfare Department, Government of Puducherry, provides boarding/lodging and hostel facilities to the Scheduled Caste students in pursuance of their education and to dissuade dropping of education at school and college...
**Eligibility:**
```text
1. The applicant should be from a Scheduled Caste.
1. The applicant should be a Student.
1. The applicant should be a Native/Resident of the Union Territory of Puducherry for not less than 5 years.
1. For Other Economically Backward Classes, the Income of the parent/guardian should not exceed ₹ 75,000/-.
1. The Parent/Guardian of the applicant should not be living within a radius of 5 km from the hostel.
```
### Extracted Conditions (Pass 2 JSON)
```json
{
  "income_annual_max": 75000,
  "caste_category": [
    "SC",
    "SEBC"
  ],
  "domicile_state": [
    "Puducherry"
  ],
  "occupation": [
    "student"
  ],
  "is_student": true,
  "is_individual_scheme": true,
  "custom_verification_required": true,
  "custom_verification_reason": "Is the applicant a resident of Puducherry for at least 5 years and does the parent/guardian reside more than 5 km away from the hostel?",
  "extraction_confidence": "high",
  "extraction_notes": "Confirmed the scheme is for individual students. Mapped 'Other Economically Backward Classes' to SEBC and applied the 75,000 income limit. Explicitly captured the 5-year residency and the 5km proximity rule for parents/guardians in the custom verification section. Retained all student-specific constraints from Pass 1.",
  "conditions_found_in": [
    "name",
    "eligibility",
    "desc"
  ]
}
```
**Critic's Notes:** Confirmed the scheme is for individual students. Mapped 'Other Economically Backward Classes' to SEBC and applied the 75,000 income limit. Explicitly captured the 5-year residency and the 5km proximity rule for parents/guardians in the custom verification section. Retained all student-specific constraints from Pass 1.
---

## SCHEME: Tamil Nadu Naan Mudhalvan Scheme (ID: 56)
### Original Text
**Description:** Skill development for students....
**Eligibility:**
```text
Students in Tamil Nadu.
```
### Extracted Conditions (Pass 2 JSON)
```json
{
  "domicile_state": [
    "Tamil Nadu"
  ],
  "occupation": [
    "student"
  ],
  "is_student": true,
  "is_individual_scheme": true,
  "custom_verification_required": true,
  "custom_verification_reason": "Are you currently enrolled as a student in a recognized educational institution located in Tamil Nadu?",
  "extraction_confidence": "high",
  "extraction_notes": "Audited for loopholes. While the scheme is for individuals (students), it requires specific institutional enrollment. Performed anti-regression check: retained domicile and student status from Pass 1. Updated custom_verification_reason to a strict Yes/No question format to ensure only currently enrolled students in the specific state apply.",
  "conditions_found_in": [
    "name",
    "eligibility",
    "desc"
  ]
}
```
**Critic's Notes:** Audited for loopholes. While the scheme is for individuals (students), it requires specific institutional enrollment. Performed anti-regression check: retained domicile and student status from Pass 1. Updated custom_verification_reason to a strict Yes/No question format to ensure only currently enrolled students in the specific state apply.
---
