"""
Candidate profile, eligibility rules, and scoring rubric.
Edit THIS file when your CV/profile changes. Do not edit the prompt-building
logic in eligibility_scoring.py for profile updates.
"""

CANDIDATE_PROFILE = """
CANDIDATE: Md Akram Hussain
LOCATION: Sylhet, Bangladesh
GENDER: Male
NATIONALITY: Bangladeshi

EDUCATION:
- MSS in Social Work, Shahjalal University of Science and Technology
- BSS in Social Work, Shahjalal University of Science and Technology

CURRENT ROLE: Programme Associate, Muslim Hands International Bangladesh
TOTAL PROFESSIONAL EXPERIENCE: ~4+ years

RELEVANT SKILLS / EXPERIENCE AREAS:
Programme design and implementation; programme/project coordination; child
protection; social work; education; safeguarding; community engagement;
MEAL; research; needs assessments; KIIs and FGDs; government/NGO
coordination; capacity building; training/facilitation;
reporting/documentation; proposal/concept-note development; beneficiary
management; child sponsorship; psychosocial support; case follow-up;
disability inclusion; WASH; humanitarian/development programming.

PROGRAMME ASSOCIATE ACHIEVEMENTS (current role):
- 10 concept notes
- 3 project proposals
- 15+ needs assessments
- 26+ programme activities
- Baseline surveys
- KIIs/FGDs
- Monitoring and follow-up
- Programme/donor reporting
- Government and NGO coordination
- Safeguarding and capacity building

SCHOOL SOCIAL WORK EXPERIENCE:
- 130 students supported
- 10+ parent meetings
- 20+ home visits
- 50+ coaching/support sessions
- 60+ teachers/SMC members trained
- 1,200+ people reached through awareness activities
- Work on child marriage, dowry, child rights, substance abuse, internet-related risks
- Contributed to reducing school dropout

TARGET CAREER AREAS (priority order not implied):
Programme Management; Child Protection / Protection; Social Work / Social
Development; Education; Safeguarding; MEAL / Programme Quality; Research &
Learning; Gender / Social Inclusion; Community Engagement;
Partnerships / Stakeholder Coordination; Advocacy; Social Protection.

TARGET ORGANIZATIONS: UN agencies, INGOs, reputable national development
organizations.
"""

ELIGIBILITY_RULES = """
ELIGIBILITY MUST BE DETERMINED BEFORE SCORING. Check, in order:
1. Gender/sex restriction (candidate is MALE — exclude female-only roles)
2. Nationality requirement
3. Work authorization requirement
4. Location requirement
5. Minimum education requirement
6. Required specialization / field of study
7. Minimum years of experience
8. Required TYPE of experience (not just years)
9. Mandatory qualifications (e.g. specific certifications)
10. Mandatory technical skills (e.g. CPIMS+/Primero, specific software)
11. Language requirements
12. Age restrictions, if explicitly stated
13. Any other explicit restriction stated in the text

RULES:
- Do NOT infer eligibility from the job title alone. Base it only on
  explicit text provided.
- If the provided job text is incomplete (e.g. no requirements/qualification
  section was captured), you MUST return eligibility_status =
  "UNVERIFIED" and explain what is missing in eligibility_reasons. Do NOT
  assume a missing section means "no restrictions".
- Do not confuse general NGO/programme experience with specialized
  experience. 4+ years of general NGO experience does NOT equal 4 years of
  cash-based transfer experience, GBV programming, WASH engineering,
  gender-mainstreaming, or CPIMS+/Primero experience. Only count experience
  that is explicitly demonstrated in the candidate profile above.
"""

SCORING_RUBRIC = """
For jobs with eligibility_status = "ELIGIBLE" only, compute a 0-100 score:
- Technical/functional match: 30%
- Relevant experience: 25%
- Mandatory requirements met: 20%
- Education match: 10%
- Sector/context relevance: 10%
- Career progression/value: 5%

Score bands:
90-100 Exceptional | 85-89 Excellent | 80-84 Strong | 75-79 Good |
70-74 Stretch | <70 Generally do not recommend.

Also estimate shortlist_probability (High/Medium/Low) and
career_value (High/Medium/Low). Do NOT score jobs that are INELIGIBLE or
UNVERIFIED — leave their score fields null.

If multiple eligible jobs share the same organization + project + location
such that the candidate should only apply to one, still score each
individually but set "duplicate_group" to a shared label (e.g. the org +
project name) so the calling code can pick the single best one.
"""

