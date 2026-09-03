"""Seed the catalog tables (universities, programs, opportunities) with a
small, curated set of REAL, well-known entries so university_search and
opportunity_search have honest data to ground agents on, even with no web
search API key configured.

Deliberately NOT included: individual professor records. Named-person bios
and email addresses are the highest-risk hallucination surface and cannot be
live-verified from here -- professor_agent is left to rely on live web
search (when configured) and will honestly report "unverified" otherwise.

Deliberately NOT included: specific application deadlines. These recur
annually and change every cycle; a date baked into this script would go
stale and could mislead a student. `deadline` is left null everywhere here,
with a note in each description to check the official site.

This data reflects the author's general knowledge of these well-known,
long-running programs, not a live crawl -- periodic re-verification against
the official sites is recommended before relying on it for real advice.

Idempotent: safe to re-run; upserts by name/title.

Usage:
    cd backend && uv run python scripts/seed_catalog.py
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.modules.opportunities.models import Opportunity, Program, University
from app.infrastructure.database.session import AsyncSessionLocal

UNIVERSITIES: list[dict] = [
    {
        "name": "Massachusetts Institute of Technology",
        "country": "USA",
        "website_url": "https://www.eecs.mit.edu/academics/graduate-programs/",
        "faculty_directory_url": "https://www.eecs.mit.edu/role/faculty-cs/",
        "description": "MIT's EECS department runs one of the world's largest and most research-intensive PhD programs, spanning AI, systems, theory, and hardware.",
        "program": {"name": "PhD in Electrical Engineering and Computer Science", "degree_level": "PhD", "field": "Computer Science"},
    },
    {
        "name": "Stanford University",
        "country": "USA",
        "website_url": "https://cs.stanford.edu/academics/phd",
        "faculty_directory_url": None,  # not yet verified fetchable -- skipped honestly rather than guessed
        "description": "Stanford's Computer Science PhD program is a major hub for AI/ML research (Stanford AI Lab, HAI) alongside systems, theory, and HCI.",
        "program": {"name": "PhD in Computer Science", "degree_level": "PhD", "field": "Computer Science"},
    },
    {
        "name": "Carnegie Mellon University",
        "country": "USA",
        "website_url": "https://www.cs.cmu.edu/academics/doctoral",
        "faculty_directory_url": None,  # CMU's directory is a JavaScript-rendered search widget; no static faculty listing to fetch
        "description": "CMU's School of Computer Science is consistently ranked among the top programs worldwide, with deep strength in AI, ML, and robotics.",
        "program": {"name": "PhD in Computer Science", "degree_level": "PhD", "field": "Computer Science"},
    },
    {
        "name": "University of California, Berkeley",
        "country": "USA",
        "website_url": "https://www2.eecs.berkeley.edu/Programs/Grad/",
        "faculty_directory_url": "https://www2.eecs.berkeley.edu/Faculty/Lists/CS/faculty.html",
        "description": "UC Berkeley's EECS PhD program is a leading center for AI research (BAIR), systems, and theory.",
        "program": {"name": "PhD in Electrical Engineering and Computer Sciences", "degree_level": "PhD", "field": "Computer Science"},
    },
    {
        "name": "University of Washington",
        "country": "USA",
        "website_url": "https://www.cs.washington.edu/academics/phd",
        "faculty_directory_url": "https://www.cs.washington.edu/people/faculty",
        "description": "The Allen School at the University of Washington is a top-ranked CS PhD program with major AI, systems, and HCI groups.",
        "program": {"name": "PhD in Computer Science & Engineering", "degree_level": "PhD", "field": "Computer Science"},
    },
    {
        "name": "University of Toronto",
        "country": "Canada",
        "website_url": "https://web.cs.toronto.edu/graduate",
        "faculty_directory_url": "https://web.cs.toronto.edu/people/faculty-directory",
        "description": "University of Toronto's Department of Computer Science is a global leader in deep learning research, home to the Vector Institute.",
        "program": {"name": "PhD in Computer Science", "degree_level": "PhD", "field": "Computer Science"},
    },
    {
        "name": "University of Oxford",
        "country": "UK",
        "website_url": "https://www.cs.ox.ac.uk/study/phd/",
        "faculty_directory_url": "https://www.cs.ox.ac.uk/people/faculty.html",
        "description": "Oxford's Department of Computer Science offers a DPhil (PhD) program with strengths in AI, formal methods, and systems.",
        "program": {"name": "DPhil in Computer Science", "degree_level": "PhD", "field": "Computer Science"},
    },
    {
        "name": "University of Cambridge",
        "country": "UK",
        "website_url": "https://www.cst.cam.ac.uk/admissions/phd",
        "faculty_directory_url": "https://www.cst.cam.ac.uk/people",
        "description": "Cambridge's Department of Computer Science and Technology runs a research-intensive PhD program spanning AI, systems, and security.",
        "program": {"name": "PhD in Computer Science", "degree_level": "PhD", "field": "Computer Science"},
    },
    {
        "name": "ETH Zurich",
        "country": "Switzerland",
        "website_url": "https://cs.ethz.ch/studies/phd-studies.html",
        "faculty_directory_url": None,  # host unreachable from this environment at build time
        "description": "ETH Zurich's Department of Computer Science is one of Europe's top-ranked CS PhD programs, strong across AI, systems, and theory.",
        "program": {"name": "PhD in Computer Science", "degree_level": "PhD", "field": "Computer Science"},
    },
    {
        "name": "Technical University of Munich",
        "country": "Germany",
        "website_url": "https://www.in.tum.de/en/in/for-prospective-students/doctorate/",
        "faculty_directory_url": None,  # landing page didn't yield a parseable faculty listing
        "description": "TUM's Department of Informatics offers a structured doctoral program and is a leading German university for computer science research.",
        "program": {"name": "Doctorate in Informatics", "degree_level": "PhD", "field": "Computer Science"},
    },
    {
        "name": "National University of Singapore",
        "country": "Singapore",
        "website_url": "https://www.comp.nus.edu.sg/programmes/phd/",
        "faculty_directory_url": None,  # not yet verified fetchable
        "description": "NUS School of Computing runs Southeast Asia's top-ranked computer science PhD program, with strong AI and systems research groups.",
        "program": {"name": "PhD in Computer Science", "degree_level": "PhD", "field": "Computer Science"},
    },
    {
        "name": "University of Melbourne",
        "country": "Australia",
        "website_url": "https://study.unimelb.edu.au/find/courses/graduate-research/doctor-of-philosophy-computing-and-information-systems/",
        "faculty_directory_url": None,  # not yet verified fetchable
        "description": "The University of Melbourne's School of Computing and Information Systems is Australia's top-ranked CS department for research.",
        "program": {"name": "PhD in Computing and Information Systems", "degree_level": "PhD", "field": "Computer Science"},
    },
]

# Major, well-known, long-running scholarship/fellowship programs. `deadline`
# is intentionally omitted (see module docstring). `country` reflects where
# the funding is administered/tenable, not eligibility restrictions.
OPPORTUNITIES: list[dict] = [
    {
        "title": "Fulbright Foreign Student Program",
        "provider": "Fulbright Program (U.S. Department of State)",
        "country": "USA",
        "funding_type": "Fully Funded",
        "degree_level": "Graduate (primarily Master's; select doctoral research grants)",
        "field": None,
        "application_url": "https://foreign.fulbrightonline.org/",
        "source_url": "https://foreign.fulbrightonline.org/",
        "description": (
            "Flagship U.S. government international exchange program funding graduate study and research "
            "in the United States for international students. Primarily supports Master's study; doctoral "
            "applicants should confirm current program structure on the official site, since Fulbright is "
            "not a full PhD-to-completion funder for most fields. Deadlines vary by home country -- check "
            "the official site for current dates."
        ),
        "eligibility": {"citizenship": "Non-U.S. citizen, per home-country Fulbright Commission rules", "notes": "Country-specific eligibility and deadlines apply."},
    },
    {
        "title": "DAAD Research Grants - Doctoral Programmes in Germany",
        "provider": "German Academic Exchange Service (DAAD)",
        "country": "Germany",
        "funding_type": "Fully Funded",
        "degree_level": "PhD",
        "field": None,
        "application_url": "https://www.daad.de/en/",
        "source_url": "https://www.daad.de/en/",
        "description": (
            "DAAD funds doctoral research in Germany for international students, typically covering a monthly "
            "stipend, health insurance, and travel allowance. Requires an above-average degree and a research "
            "proposal, often with a supervising professor already identified. Deadlines vary by track -- check "
            "the official site for current dates."
        ),
        "eligibility": {"academic_record": "Above-average Bachelor's/Master's degree", "notes": "A research proposal and often a German host supervisor are required."},
    },
    {
        "title": "Commonwealth Scholarships (PhD)",
        "provider": "Commonwealth Scholarship Commission in the UK",
        "country": "UK",
        "funding_type": "Fully Funded",
        "degree_level": "PhD",
        "field": None,
        "application_url": "https://cscuk.fcdo.gov.uk/",
        "source_url": "https://cscuk.fcdo.gov.uk/",
        "description": (
            "UK government-funded scholarships for citizens of Commonwealth countries to pursue PhD study in "
            "the UK, covering tuition, living allowance, and travel. Aimed particularly at applicants from "
            "low- and middle-income Commonwealth countries. Deadlines vary by cycle -- check the official site."
        ),
        "eligibility": {"citizenship": "Citizen of an eligible Commonwealth country", "notes": "Typically requires the applicant to be unable to afford study in the UK without a scholarship."},
    },
    {
        "title": "Vanier Canada Graduate Scholarships",
        "provider": "Government of Canada",
        "country": "Canada",
        "funding_type": "Fully Funded",
        "degree_level": "PhD",
        "field": None,
        "application_url": "https://vanier.gc.ca/",
        "source_url": "https://vanier.gc.ca/",
        "description": (
            "Canada's flagship doctoral scholarship, funding PhD students of any nationality studying at a "
            "Canadian institution, evaluated on academic excellence, research potential, and leadership. "
            "Nomination is coordinated through the host institution's graduate school. Deadlines vary by "
            "institution -- check the official site."
        ),
        "eligibility": {"nomination": "Must be nominated by a Canadian degree-granting institution", "notes": "Open to Canadian and international PhD applicants."},
    },
    {
        "title": "Gates Cambridge Scholarship",
        "provider": "Gates Cambridge Trust",
        "country": "UK",
        "funding_type": "Fully Funded",
        "degree_level": "Graduate (Master's & PhD)",
        "field": None,
        "application_url": "https://www.gatescambridge.org/",
        "source_url": "https://www.gatescambridge.org/",
        "description": (
            "Full-cost postgraduate scholarship for outstanding international students (all countries "
            "outside the UK) to study any subject at the University of Cambridge, including PhD programs. "
            "Covers tuition, maintenance, and additional allowances. Deadlines vary by course -- check the "
            "official site."
        ),
        "eligibility": {"citizenship": "Any country outside the UK", "notes": "Requires admission to a Cambridge graduate course as a prerequisite."},
    },
    {
        "title": "Chevening Scholarships",
        "provider": "UK Foreign, Commonwealth & Development Office",
        "country": "UK",
        "funding_type": "Fully Funded",
        "degree_level": "Master's",
        "field": None,
        "application_url": "https://www.chevening.org/",
        "source_url": "https://www.chevening.org/",
        "description": (
            "UK government scholarship for a one-year Master's degree at any UK university -- this program "
            "funds Master's study, not PhDs. Included here because many PhD applicants use it as a stepping "
            "stone Master's year. Deadlines vary by country -- check the official site."
        ),
        "eligibility": {"work_experience": "Typically requires at least 2 years of work experience", "notes": "Country-specific eligibility applies."},
    },
    {
        "title": "Rhodes Scholarship",
        "provider": "Rhodes Trust",
        "country": "UK",
        "funding_type": "Fully Funded",
        "degree_level": "Graduate (incl. DPhil)",
        "field": None,
        "application_url": "https://www.rhodeshouse.ox.ac.uk/",
        "source_url": "https://www.rhodeshouse.ox.ac.uk/",
        "description": (
            "One of the oldest and most prestigious international postgraduate scholarships, funding study at "
            "the University of Oxford, including DPhil (PhD) study, for scholars selected by country/region "
            "constituency. Deadlines vary by constituency -- check the official site."
        ),
        "eligibility": {"age": "Constituency-specific age/eligibility rules apply", "notes": "Selection is highly competitive and considers academic merit plus leadership/character."},
    },
    {
        "title": "Knight-Hennessy Scholars",
        "provider": "Knight-Hennessy Scholars, Stanford University",
        "country": "USA",
        "funding_type": "Fully Funded",
        "degree_level": "Graduate (any Stanford graduate degree, incl. PhD)",
        "field": None,
        "application_url": "https://knight-hennessy.stanford.edu/",
        "source_url": "https://knight-hennessy.stanford.edu/",
        "description": (
            "Funds up to three years of any graduate degree at Stanford University, including PhD programs, "
            "for admitted students of any nationality, alongside a leadership development program. Requires "
            "separate admission to a Stanford graduate program. Deadlines vary -- check the official site."
        ),
        "eligibility": {"admission": "Requires separate admission to a Stanford graduate program", "notes": "Open to applicants of any nationality."},
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        university_ids: dict[str, object] = {}

        for entry in UNIVERSITIES:
            existing = await session.execute(select(University).where(University.name == entry["name"]))
            university = existing.scalar_one_or_none()
            if university is None:
                university = University(
                    name=entry["name"],
                    country=entry["country"],
                    website_url=entry["website_url"],
                    faculty_directory_url=entry.get("faculty_directory_url"),
                    description=entry["description"],
                )
                session.add(university)
                await session.flush()
            else:
                university.country = entry["country"]
                university.website_url = entry["website_url"]
                university.faculty_directory_url = entry.get("faculty_directory_url")
                university.description = entry["description"]
            university_ids[entry["name"]] = university.id

            program_info = entry["program"]
            existing_program = await session.execute(
                select(Program).where(Program.name == program_info["name"], Program.university_id == university.id)
            )
            program = existing_program.scalar_one_or_none()
            if program is None:
                session.add(
                    Program(
                        name=program_info["name"],
                        university_id=university.id,
                        degree_level=program_info["degree_level"],
                        field=program_info["field"],
                        country=entry["country"],
                        description=entry["description"],
                    )
                )

        for entry in OPPORTUNITIES:
            existing = await session.execute(select(Opportunity).where(Opportunity.title == entry["title"]))
            opportunity = existing.scalar_one_or_none()
            if opportunity is None:
                session.add(
                    Opportunity(
                        title=entry["title"],
                        provider=entry["provider"],
                        university=None,
                        degree_level=entry["degree_level"],
                        country=entry["country"],
                        field=entry["field"],
                        funding_type=entry["funding_type"],
                        amount=None,
                        deadline=None,
                        eligibility=entry["eligibility"],
                        application_url=entry["application_url"],
                        source_url=entry["source_url"],
                        description=entry["description"],
                    )
                )
            else:
                opportunity.provider = entry["provider"]
                opportunity.degree_level = entry["degree_level"]
                opportunity.country = entry["country"]
                opportunity.funding_type = entry["funding_type"]
                opportunity.eligibility = entry["eligibility"]
                opportunity.application_url = entry["application_url"]
                opportunity.source_url = entry["source_url"]
                opportunity.description = entry["description"]

        await session.commit()
        print(f"Seeded/updated {len(UNIVERSITIES)} universities+programs and {len(OPPORTUNITIES)} opportunities.")


if __name__ == "__main__":
    asyncio.run(seed())
