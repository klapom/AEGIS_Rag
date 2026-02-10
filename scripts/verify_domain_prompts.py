#!/usr/bin/env python3
"""Domain Prompt Verification Benchmark — All 35 Domains.

Sprint 128: Verifies that all domain-enriched extraction prompts work correctly
on DGX Spark with Nemotron model after the Sprint 128 prompt rewrite.

Phase 1 (fast, no LLM): Format verification — templates render, placeholders present
Phase 2 (slow, ~40-60 min): Quality verification — extract from example texts via vLLM

Usage (inside API container):
    python /app/scripts/verify_domain_prompts.py              # Both phases
    python /app/scripts/verify_domain_prompts.py --format-only # Phase 1 only
    python /app/scripts/verify_domain_prompts.py --domains computer_science_it,medicine_health
"""

import argparse
import asyncio
import json
import os
import sys
import time
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

# Environment setup
os.environ.setdefault("AEGIS_EXTRACTION_WORKERS", "2")
os.environ.setdefault("AEGIS_USE_CROSS_SENTENCE", "1")

sys.path.insert(0, "/app")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

from src.prompts.extraction_prompts import get_domain_enriched_extraction_prompts

# ============================================================================
# Domain Example Texts — 35 domains with expected entities and relations
# ============================================================================

DOMAIN_EXAMPLES = {
    "computer_science_it": {
        "text": "TensorFlow 2.12, developed by Google Brain, runs on CUDA GPUs. The framework uses Python 3.11 and depends on NumPy for tensor operations.",
        "expected_entities": [
            {"name": "TensorFlow", "type": "SOFTWARE"},
            {"name": "Google Brain", "type": "ORGANIZATION"},
            {"name": "CUDA", "type": "TECHNOLOGY"},
            {"name": "Python", "type": "PROGRAMMING_LANGUAGE"},
            {"name": "NumPy", "type": "SOFTWARE"},
        ],
        "expected_relations": ["DEVELOPED_BY", "RUNS_ON", "USES", "DEPENDS_ON"],
    },
    "mathematics": {
        "text": "Andrew Wiles proved Fermat's Last Theorem in 1995 using modular elliptic curves. The proof built on the Taniyama-Shimura conjecture formulated in 1957.",
        "expected_entities": [
            {"name": "Andrew Wiles", "type": "PERSON"},
            {"name": "Fermat's Last Theorem", "type": "THEOREM"},
            {"name": "modular elliptic curves", "type": "CONCEPT"},
            {"name": "Taniyama-Shimura conjecture", "type": "THEOREM"},
        ],
        "expected_relations": ["PROVES", "USES", "BUILDS_ON"],
    },
    "physics": {
        "text": "CERN's Large Hadron Collider detected the Higgs boson in 2012. The particle has a mass of 125.1 GeV, confirming the Standard Model prediction.",
        "expected_entities": [
            {"name": "CERN", "type": "ORGANIZATION"},
            {"name": "Large Hadron Collider", "type": "INSTRUMENT"},
            {"name": "Higgs boson", "type": "PARTICLE"},
            {"name": "Standard Model", "type": "THEORY"},
        ],
        "expected_relations": ["DETECTED", "CONFIRMS", "PART_OF"],
    },
    "chemistry": {
        "text": "Platinum catalyzes the Haber-Bosch process, converting nitrogen and hydrogen into ammonia at 450 degrees Celsius. Fritz Haber developed the process in 1909.",
        "expected_entities": [
            {"name": "Platinum", "type": "CATALYST"},
            {"name": "Haber-Bosch process", "type": "REACTION"},
            {"name": "ammonia", "type": "COMPOUND"},
            {"name": "Fritz Haber", "type": "PERSON"},
        ],
        "expected_relations": ["CATALYZES", "PRODUCES", "DEVELOPED_BY"],
    },
    "biology_life_sciences": {
        "text": "The BRCA1 gene encodes a tumor suppressor protein that repairs DNA damage. Mutations in BRCA1 increase breast cancer risk by 70 percent.",
        "expected_entities": [
            {"name": "BRCA1", "type": "GENE"},
            {"name": "tumor suppressor protein", "type": "PROTEIN"},
            {"name": "breast cancer", "type": "DISEASE"},
        ],
        "expected_relations": ["ENCODES", "REPAIRS", "CAUSES"],
    },
    "earth_environmental_sciences": {
        "text": "The 2010 Eyjafjallajokull eruption released 250 million tonnes of CO2. Iceland's volcanic activity is driven by the Mid-Atlantic Ridge.",
        "expected_entities": [
            {"name": "Eyjafjallajokull", "type": "GEOLOGICAL_FEATURE"},
            {"name": "CO2", "type": "COMPOUND"},
            {"name": "Mid-Atlantic Ridge", "type": "GEOLOGICAL_FORMATION"},
        ],
        "expected_relations": ["RELEASES", "DRIVES", "LOCATED_IN"],
    },
    "astronomy_space": {
        "text": "The James Webb Space Telescope observed galaxy JADES-GS-z13-0 at redshift 13.2. NASA launched JWST in December 2021 from Kourou, French Guiana.",
        "expected_entities": [
            {"name": "James Webb Space Telescope", "type": "TELESCOPE"},
            {"name": "JADES-GS-z13-0", "type": "CELESTIAL_BODY"},
            {"name": "NASA", "type": "ORGANIZATION"},
        ],
        "expected_relations": ["OBSERVES", "LAUNCHED_BY", "LOCATED_IN"],
    },
    "engineering": {
        "text": "The Millau Viaduct uses cable-stayed suspension across the Tarn Valley. Michel Virlogeux designed the 343-meter tall bridge using high-strength steel.",
        "expected_entities": [
            {"name": "Millau Viaduct", "type": "STRUCTURE"},
            {"name": "Michel Virlogeux", "type": "PERSON"},
            {"name": "high-strength steel", "type": "MATERIAL"},
        ],
        "expected_relations": ["DESIGNED_BY", "USES", "LOCATED_IN"],
    },
    "medicine_health": {
        "text": "Metformin treats Type 2 diabetes by reducing hepatic glucose production. The FDA approved metformin in 1994 after clinical trials showed 30 percent HbA1c reduction.",
        "expected_entities": [
            {"name": "Metformin", "type": "MEDICATION"},
            {"name": "Type 2 diabetes", "type": "DISEASE"},
            {"name": "FDA", "type": "ORGANIZATION"},
            {"name": "HbA1c", "type": "BIOMARKER"},
        ],
        "expected_relations": ["TREATS", "APPROVED_BY", "REDUCES"],
    },
    "agriculture_food": {
        "text": "Nitrogen fertilizer increases wheat yield by 40 percent in clay soils. The Punjab region produces 35 million tonnes of wheat annually using irrigation from the Indus River.",
        "expected_entities": [
            {"name": "Nitrogen fertilizer", "type": "NUTRIENT"},
            {"name": "wheat", "type": "CROP"},
            {"name": "Punjab", "type": "LOCATION"},
            {"name": "Indus River", "type": "LOCATION"},
        ],
        "expected_relations": ["INCREASES", "PRODUCES", "IRRIGATED_BY"],
    },
    "materials_science": {
        "text": "Ti-6Al-4V titanium alloy has a tensile strength of 1000 MPa and is used in Boeing 787 airframes. Annealing at 700 degrees improves its fatigue resistance.",
        "expected_entities": [
            {"name": "Ti-6Al-4V", "type": "ALLOY"},
            {"name": "Boeing 787", "type": "PRODUCT"},
            {"name": "tensile strength", "type": "MATERIAL_PROPERTY"},
        ],
        "expected_relations": ["HAS_PROPERTY", "USED_IN", "IMPROVES"],
    },
    "manufacturing_industry": {
        "text": "Toyota's lean manufacturing system uses Kanban for just-in-time inventory. Six Sigma methodology reduced defect rates to 3.4 per million at Motorola.",
        "expected_entities": [
            {"name": "Toyota", "type": "COMPANY"},
            {"name": "Kanban", "type": "METHODOLOGY"},
            {"name": "Six Sigma", "type": "METHODOLOGY"},
            {"name": "Motorola", "type": "COMPANY"},
        ],
        "expected_relations": ["USES", "REDUCES", "DEVELOPED_BY"],
    },
    "energy_resources": {
        "text": "The Three Gorges Dam generates 22500 MW of hydroelectric power. China invested 31 billion dollars in the Yangtze River project completed in 2006.",
        "expected_entities": [
            {"name": "Three Gorges Dam", "type": "POWER_PLANT"},
            {"name": "hydroelectric power", "type": "ENERGY_SOURCE"},
            {"name": "China", "type": "LOCATION"},
        ],
        "expected_relations": ["GENERATES", "INVESTED_IN", "LOCATED_IN"],
    },
    "architecture_construction": {
        "text": "Frank Lloyd Wright designed Fallingwater in 1935 using reinforced concrete cantilevers. The building integrates with Bear Run waterfall in Pennsylvania.",
        "expected_entities": [
            {"name": "Frank Lloyd Wright", "type": "ARCHITECT"},
            {"name": "Fallingwater", "type": "BUILDING"},
            {"name": "reinforced concrete", "type": "MATERIAL"},
        ],
        "expected_relations": ["DESIGNED", "USES", "LOCATED_IN"],
    },
    "telecommunications": {
        "text": "5G NR operates on millimeter wave frequencies between 24 and 100 GHz. Ericsson deployed 5G base stations for T-Mobile using Massive MIMO antenna arrays.",
        "expected_entities": [
            {"name": "5G NR", "type": "PROTOCOL"},
            {"name": "Ericsson", "type": "ORGANIZATION"},
            {"name": "T-Mobile", "type": "ORGANIZATION"},
            {"name": "Massive MIMO", "type": "TECHNOLOGY"},
        ],
        "expected_relations": ["OPERATES_ON", "DEPLOYED_BY", "USES"],
    },
    "transportation_logistics": {
        "text": "Maersk's Triple-E class container ships carry 18340 TEU on the Asia-Europe route. The vessels use slow steaming at 17 knots to reduce fuel consumption by 35 percent.",
        "expected_entities": [
            {"name": "Maersk", "type": "COMPANY"},
            {"name": "Triple-E class", "type": "VEHICLE"},
            {"name": "Asia-Europe route", "type": "ROUTE"},
        ],
        "expected_relations": ["CARRIES", "OPERATES_ON", "REDUCES"],
    },
    "psychology": {
        "text": "Cognitive Behavioral Therapy treats generalized anxiety disorder by restructuring maladaptive thought patterns. Aaron Beck developed CBT at the University of Pennsylvania in 1960.",
        "expected_entities": [
            {"name": "Cognitive Behavioral Therapy", "type": "THERAPY"},
            {"name": "generalized anxiety disorder", "type": "DISORDER"},
            {"name": "Aaron Beck", "type": "PERSON"},
        ],
        "expected_relations": ["TREATS", "DEVELOPED_BY", "EMPLOYS"],
    },
    "economics_business": {
        "text": "The Federal Reserve raised interest rates to 5.25 percent in 2023. Apple's market capitalization reached 3 trillion dollars, surpassing Microsoft and Saudi Aramco.",
        "expected_entities": [
            {"name": "Federal Reserve", "type": "ORGANIZATION"},
            {"name": "interest rates", "type": "ECONOMIC_INDICATOR"},
            {"name": "Apple", "type": "COMPANY"},
            {"name": "Microsoft", "type": "COMPANY"},
        ],
        "expected_relations": ["ADJUSTS", "SURPASSES", "REACHES"],
    },
    "law_legal": {
        "text": "The Supreme Court ruled in Brown v. Board of Education (1954) that racial segregation violates the 14th Amendment. Chief Justice Earl Warren wrote the unanimous opinion.",
        "expected_entities": [
            {"name": "Supreme Court", "type": "COURT"},
            {"name": "Brown v. Board of Education", "type": "CASE"},
            {"name": "14th Amendment", "type": "STATUTE"},
            {"name": "Earl Warren", "type": "PERSON"},
        ],
        "expected_relations": ["RULED", "VIOLATES", "AUTHORED_BY"],
    },
    "political_science": {
        "text": "The European Union implemented the Lisbon Treaty in 2009, strengthening the European Parliament. Germany and France led the ratification process across 27 member states.",
        "expected_entities": [
            {"name": "European Union", "type": "POLITICAL_ENTITY"},
            {"name": "Lisbon Treaty", "type": "TREATY"},
            {"name": "European Parliament", "type": "POLITICAL_ENTITY"},
            {"name": "Germany", "type": "LOCATION"},
        ],
        "expected_relations": ["IMPLEMENTED", "STRENGTHENS", "LED"],
    },
    "education": {
        "text": "MIT OpenCourseWare provides free access to 2500 courses online. The PISA assessment by OECD ranks Finland's education system among the top 5 globally.",
        "expected_entities": [
            {"name": "MIT", "type": "INSTITUTION"},
            {"name": "OpenCourseWare", "type": "PROGRAM"},
            {"name": "PISA", "type": "ASSESSMENT"},
            {"name": "OECD", "type": "ORGANIZATION"},
        ],
        "expected_relations": ["PROVIDES", "RANKS", "DEVELOPED_BY"],
    },
    "sociology": {
        "text": "Max Weber's theory of bureaucracy explains organizational hierarchy in modern institutions. Emile Durkheim studied social cohesion through the concept of collective consciousness.",
        "expected_entities": [
            {"name": "Max Weber", "type": "PERSON"},
            {"name": "bureaucracy", "type": "THEORY"},
            {"name": "Emile Durkheim", "type": "PERSON"},
            {"name": "collective consciousness", "type": "CONCEPT"},
        ],
        "expected_relations": ["FORMULATED", "STUDIES", "EXPLAINS"],
    },
    "media_communication": {
        "text": "Netflix's recommendation algorithm processes 1 billion ratings daily using collaborative filtering. The New York Times reached 10 million digital subscribers in 2023.",
        "expected_entities": [
            {"name": "Netflix", "type": "PLATFORM"},
            {"name": "collaborative filtering", "type": "ALGORITHM"},
            {"name": "New York Times", "type": "PUBLICATION"},
        ],
        "expected_relations": ["USES", "PROCESSES", "REACHED"],
    },
    "philosophy_ethics": {
        "text": "Immanuel Kant formulated the categorical imperative in his Critique of Pure Reason. John Stuart Mill's utilitarianism argues that actions should maximize overall happiness.",
        "expected_entities": [
            {"name": "Immanuel Kant", "type": "PHILOSOPHER"},
            {"name": "categorical imperative", "type": "CONCEPT"},
            {"name": "Critique of Pure Reason", "type": "WORK"},
            {"name": "John Stuart Mill", "type": "PHILOSOPHER"},
        ],
        "expected_relations": ["FORMULATED", "ARGUES", "PUBLISHED_IN"],
    },
    "history_archaeology": {
        "text": "Howard Carter discovered Tutankhamun's tomb in the Valley of the Kings in 1922. The burial chamber contained the golden death mask weighing 11 kilograms.",
        "expected_entities": [
            {"name": "Howard Carter", "type": "PERSON"},
            {"name": "Tutankhamun's tomb", "type": "ARTIFACT"},
            {"name": "Valley of the Kings", "type": "ARCHAEOLOGICAL_SITE"},
            {"name": "golden death mask", "type": "ARTIFACT"},
        ],
        "expected_relations": ["DISCOVERED", "CONTAINS", "LOCATED_IN"],
    },
    "linguistics_languages": {
        "text": "Noam Chomsky proposed Universal Grammar in 1957, arguing all languages share an innate structure. The Indo-European language family connects 445 languages across Europe and South Asia.",
        "expected_entities": [
            {"name": "Noam Chomsky", "type": "PERSON"},
            {"name": "Universal Grammar", "type": "THEORY"},
            {"name": "Indo-European", "type": "LANGUAGE_FAMILY"},
        ],
        "expected_relations": ["PROPOSED", "CONNECTS", "CONTAINS"],
    },
    "literature": {
        "text": "Gabriel Garcia Marquez wrote One Hundred Years of Solitude in 1967, pioneering magical realism. The novel chronicles the Buendia family in the fictional town of Macondo.",
        "expected_entities": [
            {"name": "Gabriel Garcia Marquez", "type": "AUTHOR"},
            {"name": "One Hundred Years of Solitude", "type": "WORK"},
            {"name": "magical realism", "type": "GENRE"},
        ],
        "expected_relations": ["WROTE", "EMPLOYS", "CHRONICLES"],
    },
    "visual_arts_design": {
        "text": "Pablo Picasso painted Guernica in 1937 as a response to the Spanish Civil War. The oil painting hangs in the Museo Reina Sofia in Madrid.",
        "expected_entities": [
            {"name": "Pablo Picasso", "type": "ARTIST"},
            {"name": "Guernica", "type": "ARTWORK"},
            {"name": "Museo Reina Sofia", "type": "MUSEUM"},
        ],
        "expected_relations": ["PAINTED", "EXHIBITED_IN", "RESPONDS_TO"],
    },
    "music_performing_arts": {
        "text": "Ludwig van Beethoven composed Symphony No. 9 in 1824, featuring the Ode to Joy choral finale. The Berlin Philharmonic under Herbert von Karajan recorded the definitive 1962 performance.",
        "expected_entities": [
            {"name": "Beethoven", "type": "COMPOSER"},
            {"name": "Symphony No. 9", "type": "COMPOSITION"},
            {"name": "Berlin Philharmonic", "type": "ENSEMBLE"},
            {"name": "Herbert von Karajan", "type": "PERSON"},
        ],
        "expected_relations": ["COMPOSED", "PERFORMED_BY", "FEATURES"],
    },
    "religion_theology": {
        "text": "Martin Luther published his 95 Theses in 1517, challenging the Catholic Church's practice of indulgences. The Protestant Reformation spread across Northern Europe within decades.",
        "expected_entities": [
            {"name": "Martin Luther", "type": "PERSON"},
            {"name": "95 Theses", "type": "TEXT"},
            {"name": "Protestant Reformation", "type": "RELIGIOUS_MOVEMENT"},
            {"name": "Catholic Church", "type": "ORGANIZATION"},
        ],
        "expected_relations": ["PUBLISHED", "CHALLENGED", "SPREAD_TO"],
    },
    "defense_security": {
        "text": "Lockheed Martin developed the F-35 Lightning II using stealth technology. The Joint Strike Fighter program cost 1.7 trillion dollars across NATO allies.",
        "expected_entities": [
            {"name": "Lockheed Martin", "type": "DEFENSE_CONTRACTOR"},
            {"name": "F-35 Lightning II", "type": "WEAPON_SYSTEM"},
            {"name": "Joint Strike Fighter", "type": "MILITARY_PROGRAM"},
            {"name": "NATO", "type": "ORGANIZATION"},
        ],
        "expected_relations": ["DEVELOPED", "COSTS", "USES"],
    },
    "sports_recreation": {
        "text": "Usain Bolt set the 100m world record of 9.58 seconds at the 2009 Berlin World Championships. The Jamaican sprinter won 8 Olympic gold medals across three Games.",
        "expected_entities": [
            {"name": "Usain Bolt", "type": "ATHLETE"},
            {"name": "100m world record", "type": "RECORD"},
            {"name": "Berlin World Championships", "type": "COMPETITION"},
        ],
        "expected_relations": ["SET", "WON", "COMPETED_IN"],
    },
    "hospitality_tourism": {
        "text": "The Ritz-Carlton operates 108 luxury hotels across 30 countries. Marriott International acquired the brand in 1998 for 290 million dollars.",
        "expected_entities": [
            {"name": "Ritz-Carlton", "type": "HOTEL_CHAIN"},
            {"name": "Marriott International", "type": "COMPANY"},
        ],
        "expected_relations": ["OPERATES", "ACQUIRED"],
    },
    "real_estate_urban": {
        "text": "The Burj Khalifa stands 828 meters tall in Dubai's Downtown district. Emaar Properties developed the 1.5 billion dollar skyscraper, completed in 2010.",
        "expected_entities": [
            {"name": "Burj Khalifa", "type": "BUILDING"},
            {"name": "Dubai", "type": "LOCATION"},
            {"name": "Emaar Properties", "type": "DEVELOPER"},
        ],
        "expected_relations": ["DEVELOPED_BY", "LOCATED_IN", "COSTS"],
    },
    "environmental_policy": {
        "text": "The Paris Agreement of 2015 commits 196 nations to limit global warming to 1.5 degrees Celsius. The EU's Green Deal aims to achieve net-zero carbon emissions by 2050.",
        "expected_entities": [
            {"name": "Paris Agreement", "type": "AGREEMENT"},
            {"name": "EU", "type": "ORGANIZATION"},
            {"name": "Green Deal", "type": "POLICY"},
        ],
        "expected_relations": ["COMMITS", "AIMS", "TARGETS"],
    },
}


# ============================================================================
# Utility functions
# ============================================================================


def fuzzy_match(expected: str, actual: str, threshold: float = 0.7) -> bool:
    """Check if two strings are similar enough."""
    return SequenceMatcher(None, expected.lower(), actual.lower()).ratio() >= threshold


def load_seed_domains(yaml_path: Path | None = None) -> list[dict]:
    """Load all domains from seed_domains.yaml."""
    if yaml_path is None:
        yaml_path = Path(__file__).resolve().parent.parent / "data" / "seed_domains.yaml"
    with open(yaml_path) as f:
        catalog = yaml.safe_load(f)
    return catalog.get("domains", [])


# ============================================================================
# Phase 1: Format Verification (no LLM)
# ============================================================================


def phase1_format_verification(domains: list[dict], filter_ids: set | None = None) -> dict:
    """Verify all domain prompt templates format correctly."""
    print("\n" + "=" * 80)
    print("PHASE 1: FORMAT VERIFICATION (no LLM)")
    print("=" * 80)

    results = {}
    passed = 0
    failed = 0

    for domain in domains:
        domain_id = domain.get("domain_id", "unknown")
        if filter_ids and domain_id not in filter_ids:
            continue

        name = domain.get("name", "")
        sub_types = domain.get("entity_sub_types", [])
        sub_type_mapping = domain.get("entity_sub_type_mapping", {})
        relation_hints = domain.get("relation_hints", [])

        checks = {
            "domain_id": domain_id,
            "name": name,
            "entity_sub_types_count": len(sub_types),
            "relation_hints_count": len(relation_hints),
        }

        # Check 1: Prompt generation doesn't crash
        try:
            entity_prompt, relation_prompt = get_domain_enriched_extraction_prompts(
                domain=domain_id,
                entity_sub_types=sub_types,
                entity_sub_type_mapping=sub_type_mapping,
                relation_hints=relation_hints,
            )
            checks["generation_ok"] = True
        except Exception as e:
            checks["generation_ok"] = False
            checks["generation_error"] = str(e)
            results[domain_id] = {**checks, "pass": False}
            failed += 1
            print(f"  FAIL  {domain_id}: generation error: {e}")
            continue

        # Check 2: Placeholders can be replaced (use str.replace to avoid JSON brace conflicts)
        try:
            test_entity = entity_prompt.replace("{text}", "SAMPLE_TEXT").replace(
                "{domain}", domain_id
            )
            checks["entity_format_ok"] = (
                "SAMPLE_TEXT" in test_entity and "{text}" not in test_entity
            )
        except Exception as e:
            checks["entity_format_ok"] = False
            checks["entity_format_error"] = str(e)

        try:
            test_rel = (
                relation_prompt.replace("{text}", "SAMPLE_TEXT")
                .replace("{domain}", domain_id)
                .replace("{entities}", "- Entity1 (PERSON)\n- Entity2 (ORGANIZATION)")
            )
            checks["relation_format_ok"] = "SAMPLE_TEXT" in test_rel and "{text}" not in test_rel
        except Exception as e:
            checks["relation_format_ok"] = False
            checks["relation_format_error"] = str(e)

        # Check 3: Placeholders present
        checks["entity_has_text"] = "{text}" in entity_prompt
        checks["relation_has_text"] = "{text}" in relation_prompt
        checks["relation_has_entities"] = "{entities}" in relation_prompt

        # Check 4: Domain-specific types injected
        if sub_types:
            injected_count = sum(1 for st in sub_types if st in entity_prompt)
            checks["sub_types_injected"] = injected_count
            checks["sub_types_injection_pct"] = round(injected_count / len(sub_types) * 100, 1)
        else:
            checks["sub_types_injected"] = 0
            checks["sub_types_injection_pct"] = 0.0

        # Check 5: Relation hints injected
        if relation_hints:
            hint_count = sum(
                1 for h in relation_hints if h.split("→")[0].strip() in relation_prompt
            )
            checks["hints_injected"] = hint_count
            checks["hints_injection_pct"] = round(hint_count / len(relation_hints) * 100, 1)
        else:
            checks["hints_injected"] = 0
            checks["hints_injection_pct"] = 0.0

        # Log full prompts
        checks["entity_prompt"] = entity_prompt
        checks["relation_prompt"] = relation_prompt
        checks["entity_prompt_chars"] = len(entity_prompt)
        checks["relation_prompt_chars"] = len(relation_prompt)

        # Determine pass/fail
        all_ok = (
            checks.get("generation_ok", False)
            and checks.get("entity_format_ok", False)
            and checks.get("relation_format_ok", False)
            and checks.get("entity_has_text", False)
            and checks.get("relation_has_text", False)
            and checks.get("relation_has_entities", False)
        )
        checks["pass"] = all_ok

        if all_ok:
            passed += 1
            status = "OK"
        else:
            failed += 1
            status = "FAIL"

        print(
            f"  {status:4s}  {domain_id:35s}  "
            f"sub_types={checks['sub_types_injected']}/{checks['entity_sub_types_count']}  "
            f"hints={checks['hints_injected']}/{checks['relation_hints_count']}  "
            f"entity={checks['entity_prompt_chars']}c  "
            f"relation={checks['relation_prompt_chars']}c"
        )

        results[domain_id] = checks

    total = passed + failed
    print(f"\nPhase 1 Summary: {passed}/{total} passed ({passed / total * 100:.0f}%)")
    if failed > 0:
        print(f"  FAILURES: {[d for d, r in results.items() if not r['pass']]}")

    return {"phase": 1, "passed": passed, "failed": failed, "total": total, "domains": results}


# ============================================================================
# Phase 2: Quality Verification (with LLM)
# ============================================================================


async def clear_redis_cache():
    """Clear the Redis prompt cache."""
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url("redis://redis:6379/0", decode_responses=True)
        keys = await r.keys("prompt_cache:*")
        if keys:
            await r.delete(*keys)
            print(f"  Cleared {len(keys)} Redis prompt cache keys")
        else:
            print("  Redis prompt cache already empty")
        await r.close()
    except Exception as e:
        print(f"  Redis cache clear failed: {e}")


async def verify_single_domain(
    service,
    domain_id: str,
    domain_config: dict,
    example: dict,
    semaphore: asyncio.Semaphore,
) -> dict:
    """Verify extraction quality for a single domain."""
    async with semaphore:
        result = {
            "domain_id": domain_id,
            "input_text": example["text"],
            "expected_entities": example["expected_entities"],
            "expected_relations": example["expected_relations"],
        }

        # --- Entity Extraction ---
        t0 = time.time()
        try:
            entities = await service.extract_entities(
                text=example["text"],
                document_id=f"verify_{domain_id}",
                domain=domain_id,
            )
            entity_time = time.time() - t0
            result["entity_extraction_time_s"] = round(entity_time, 1)
            result["entity_count"] = len(entities)
            result["entities"] = [
                {
                    "name": getattr(e, "name", ""),
                    "type": getattr(e, "entity_type", getattr(e, "type", "")),
                    "description": getattr(e, "description", ""),
                    "confidence": getattr(e, "confidence", None),
                }
                for e in entities
            ]
            result["entity_extraction_ok"] = True
            print(f"    {domain_id}: entities={len(entities)} ({entity_time:.1f}s)")
        except Exception as e:
            entity_time = time.time() - t0
            result["entity_extraction_ok"] = False
            result["entity_extraction_error"] = repr(e)
            result["entity_extraction_time_s"] = round(entity_time, 1)
            result["entities"] = []
            result["entity_count"] = 0
            print(f"    {domain_id}: entity extraction FAILED: {e}")
            entities = []

        # --- Relation Extraction ---
        if entities:
            t1 = time.time()
            try:
                relations = await service.extract_relationships(
                    text=example["text"],
                    entities=entities,
                    document_id=f"verify_{domain_id}",
                    domain=domain_id,
                )
                rel_time = time.time() - t1
                result["relation_extraction_time_s"] = round(rel_time, 1)
                result["relation_count"] = len(relations)
                result["relations"] = [
                    {
                        "source": getattr(r, "source", getattr(r, "source_entity", "")),
                        "target": getattr(r, "target", getattr(r, "target_entity", "")),
                        "type": getattr(r, "relation_type", getattr(r, "type", "")),
                        "description": getattr(r, "description", ""),
                        "strength": getattr(r, "strength", None),
                    }
                    for r in relations
                ]
                result["relation_extraction_ok"] = True
                print(f"    {domain_id}: relations={len(relations)} ({rel_time:.1f}s)")
            except Exception as e:
                rel_time = time.time() - t1
                result["relation_extraction_ok"] = False
                result["relation_extraction_error"] = repr(e)
                result["relation_extraction_time_s"] = round(rel_time, 1)
                result["relations"] = []
                result["relation_count"] = 0
                print(f"    {domain_id}: relation extraction FAILED: {e}")
        else:
            result["relation_extraction_ok"] = False
            result["relation_extraction_error"] = "No entities extracted"
            result["relation_extraction_time_s"] = 0
            result["relations"] = []
            result["relation_count"] = 0

        # --- Scoring ---
        scores = score_domain(result, example)
        result["scores"] = scores

        return result


def score_domain(result: dict, example: dict) -> dict:
    """Score extraction quality against expected outputs."""
    scores = {}

    # Entity Recall: % of expected entities found (fuzzy name match)
    expected_ents = example["expected_entities"]
    actual_ents = result.get("entities", [])
    matched = 0
    matched_pairs = []
    for exp in expected_ents:
        for act in actual_ents:
            if fuzzy_match(exp["name"], act["name"]):
                matched += 1
                matched_pairs.append((exp, act))
                break
    scores["entity_recall"] = round(matched / len(expected_ents), 2) if expected_ents else 0
    scores["entity_recall_detail"] = f"{matched}/{len(expected_ents)}"

    # Entity Type Accuracy: % of matched entities with correct type
    type_correct = 0
    for exp, act in matched_pairs:
        exp_type = exp["type"].upper()
        act_type = (act.get("type") or "").upper()
        # Accept exact match OR universal type match
        if act_type == exp_type or act_type in _get_acceptable_types(exp_type):
            type_correct += 1
    scores["entity_type_accuracy"] = (
        round(type_correct / len(matched_pairs), 2) if matched_pairs else 0
    )
    scores["entity_type_accuracy_detail"] = f"{type_correct}/{len(matched_pairs)}"

    # Relation Specificity: % of relations NOT RELATED_TO
    actual_rels = result.get("relations", [])
    if actual_rels:
        specific = sum(
            1
            for r in actual_rels
            if (r.get("type") or "").upper() not in ("RELATED_TO", "RELATES_TO")
        )
        scores["relation_specificity"] = round(specific / len(actual_rels), 2)
        scores["relation_specificity_detail"] = f"{specific}/{len(actual_rels)}"
    else:
        scores["relation_specificity"] = 0
        scores["relation_specificity_detail"] = "0/0"

    # Relation type distribution
    if actual_rels:
        rel_types = Counter((r.get("type") or "UNKNOWN").upper() for r in actual_rels)
        scores["relation_type_distribution"] = dict(rel_types.most_common())
    else:
        scores["relation_type_distribution"] = {}

    # Entity type distribution
    if actual_ents:
        ent_types = Counter((e.get("type") or "UNKNOWN").upper() for e in actual_ents)
        scores["entity_type_distribution"] = dict(ent_types.most_common())
    else:
        scores["entity_type_distribution"] = {}

    # Field Completeness: confidence (entities) and strength (relations)
    if actual_ents:
        has_confidence = sum(
            1
            for e in actual_ents
            if e.get("confidence") is not None and 0.0 <= float(e["confidence"]) <= 1.0
        )
        scores["confidence_completeness"] = round(has_confidence / len(actual_ents), 2)
    else:
        scores["confidence_completeness"] = 0

    if actual_rels:
        has_strength = sum(
            1
            for r in actual_rels
            if r.get("strength") is not None and 1 <= int(float(r["strength"])) <= 10
        )
        scores["strength_completeness"] = round(has_strength / len(actual_rels), 2)
    else:
        scores["strength_completeness"] = 0

    # Overall pass
    scores["pass"] = (
        scores["entity_recall"] >= 0.50
        and scores["entity_type_accuracy"] >= 0.50
        and scores["relation_specificity"] >= 0.40
        and scores["confidence_completeness"] >= 0.70
        and (scores["strength_completeness"] >= 0.50 or not actual_rels)
    )

    return scores


def _get_acceptable_types(domain_type: str) -> set:
    """Get universal types that are acceptable for a domain-specific type."""
    # Domain sub-types map to universal types — both are acceptable
    universal_mapping = {
        # CS/IT
        "SOFTWARE": {"TECHNOLOGY", "PRODUCT"},
        "PROGRAMMING_LANGUAGE": {"TECHNOLOGY"},
        "FRAMEWORK": {"TECHNOLOGY"},
        "ALGORITHM": {"CONCEPT", "TECHNOLOGY", "PROCESS"},
        "DATABASE": {"TECHNOLOGY", "PRODUCT"},
        "PROTOCOL": {"TECHNOLOGY", "CONCEPT"},
        # Sciences
        "THEOREM": {"CONCEPT", "DOCUMENT"},
        "THEORY": {"CONCEPT"},
        "PARTICLE": {"CONCEPT", "MATERIAL"},
        "INSTRUMENT": {"TECHNOLOGY", "PRODUCT"},
        "CATALYST": {"MATERIAL", "CONCEPT"},
        "REACTION": {"PROCESS", "CONCEPT"},
        "COMPOUND": {"MATERIAL", "CONCEPT"},
        "GENE": {"CONCEPT"},
        "PROTEIN": {"CONCEPT", "MATERIAL"},
        "DISEASE": {"CONCEPT"},
        "BIOMARKER": {"METRIC", "CONCEPT"},
        "GEOLOGICAL_FEATURE": {"LOCATION", "CONCEPT"},
        "GEOLOGICAL_FORMATION": {"LOCATION", "CONCEPT"},
        "CELESTIAL_BODY": {"LOCATION", "CONCEPT"},
        "TELESCOPE": {"TECHNOLOGY", "PRODUCT"},
        # Engineering
        "STRUCTURE": {"PRODUCT", "LOCATION"},
        "ALLOY": {"MATERIAL"},
        "MATERIAL_PROPERTY": {"METRIC", "CONCEPT"},
        "POWER_PLANT": {"ORGANIZATION", "LOCATION", "PRODUCT"},
        "ENERGY_SOURCE": {"CONCEPT", "TECHNOLOGY"},
        # Social
        "METHODOLOGY": {"CONCEPT", "PROCESS"},
        "COMPANY": {"ORGANIZATION"},
        "INSTITUTION": {"ORGANIZATION"},
        "THERAPY": {"CONCEPT", "PROCESS"},
        "DISORDER": {"CONCEPT"},
        "ECONOMIC_INDICATOR": {"METRIC", "CONCEPT"},
        "COURT": {"ORGANIZATION"},
        "CASE": {"DOCUMENT", "EVENT", "CONCEPT"},
        "STATUTE": {"DOCUMENT", "REGULATION"},
        "POLITICAL_ENTITY": {"ORGANIZATION"},
        "TREATY": {"DOCUMENT", "REGULATION"},
        "PROGRAM": {"CONCEPT", "PRODUCT"},
        "ASSESSMENT": {"CONCEPT", "PROCESS", "DOCUMENT"},
        "PHILOSOPHER": {"PERSON"},
        "WORK": {"DOCUMENT", "PRODUCT"},
        # Arts
        "AUTHOR": {"PERSON"},
        "ARTIST": {"PERSON"},
        "COMPOSER": {"PERSON"},
        "ARTWORK": {"PRODUCT", "DOCUMENT"},
        "COMPOSITION": {"PRODUCT", "DOCUMENT"},
        "GENRE": {"CONCEPT", "FIELD"},
        "MUSEUM": {"ORGANIZATION", "LOCATION"},
        "ENSEMBLE": {"ORGANIZATION"},
        "PUBLICATION": {"ORGANIZATION", "DOCUMENT"},
        "PLATFORM": {"ORGANIZATION", "TECHNOLOGY", "PRODUCT"},
        # Military/Sports/Tourism
        "DEFENSE_CONTRACTOR": {"ORGANIZATION"},
        "WEAPON_SYSTEM": {"PRODUCT", "TECHNOLOGY"},
        "MILITARY_PROGRAM": {"CONCEPT", "PROCESS"},
        "ATHLETE": {"PERSON"},
        "COMPETITION": {"EVENT"},
        "RECORD": {"METRIC", "EVENT"},
        "HOTEL_CHAIN": {"ORGANIZATION"},
        "BUILDING": {"LOCATION", "PRODUCT"},
        "DEVELOPER": {"ORGANIZATION"},
        "AGREEMENT": {"DOCUMENT", "REGULATION"},
        "POLICY": {"CONCEPT", "REGULATION", "DOCUMENT"},
        "ARCHITECT": {"PERSON"},
        "ROUTE": {"LOCATION", "CONCEPT"},
        "VEHICLE": {"PRODUCT", "TECHNOLOGY"},
        "NUTRIENT": {"MATERIAL", "CONCEPT"},
        "CROP": {"MATERIAL", "PRODUCT"},
        "TEXT": {"DOCUMENT"},
        "RELIGIOUS_MOVEMENT": {"CONCEPT", "EVENT"},
        "LANGUAGE_FAMILY": {"CONCEPT"},
    }
    return universal_mapping.get(domain_type, set())


async def phase2_quality_verification(
    domains: list[dict],
    filter_ids: set | None = None,
    workers: int = 2,
) -> dict:
    """Run LLM-based quality verification for all domains."""
    print("\n" + "=" * 80)
    print("PHASE 2: QUALITY VERIFICATION (with LLM)")
    print("=" * 80)

    # Clear Redis cache
    print("\nClearing Redis prompt cache...")
    await clear_redis_cache()

    # Initialize ExtractionService
    print("Initializing ExtractionService...")
    from src.components.graph_rag.extraction_service import ExtractionService

    service = ExtractionService()

    semaphore = asyncio.Semaphore(workers)
    total_start = time.time()

    # Build domain lookup
    domain_lookup = {d["domain_id"]: d for d in domains}

    # Filter to domains that have examples
    tasks = []
    for domain_id, example in DOMAIN_EXAMPLES.items():
        if filter_ids and domain_id not in filter_ids:
            continue
        domain_config = domain_lookup.get(domain_id, {})
        tasks.append(verify_single_domain(service, domain_id, domain_config, example, semaphore))

    print(f"\nRunning {len(tasks)} domain extractions ({workers} workers)...\n")

    # Run all extractions
    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    total_time = time.time() - total_start

    # Process results
    results = {}
    passed = 0
    failed = 0

    for r in results_list:
        if isinstance(r, Exception):
            print(f"  Exception: {r}")
            failed += 1
            continue
        domain_id = r["domain_id"]
        results[domain_id] = r
        if r.get("scores", {}).get("pass", False):
            passed += 1
        else:
            failed += 1

    total = passed + failed

    # Print summary table
    print("\n" + "=" * 80)
    print("PHASE 2 RESULTS")
    print("=" * 80)
    print(
        f"{'Domain':<35s}  {'Ent':>3s}  {'Rel':>3s}  "
        f"{'Recall':>6s}  {'Type%':>5s}  {'Spec%':>5s}  "
        f"{'Conf%':>5s}  {'Str%':>5s}  {'Pass':>4s}"
    )
    print("-" * 108)

    for domain_id in DOMAIN_EXAMPLES:
        if domain_id not in results:
            continue
        r = results[domain_id]
        s = r.get("scores", {})
        print(
            f"{domain_id:<35s}  "
            f"{r.get('entity_count', 0):>3d}  "
            f"{r.get('relation_count', 0):>3d}  "
            f"{s.get('entity_recall', 0):>5.0%}  "
            f"{s.get('entity_type_accuracy', 0):>5.0%}  "
            f"{s.get('relation_specificity', 0):>5.0%}  "
            f"{s.get('confidence_completeness', 0):>5.0%}  "
            f"{s.get('strength_completeness', 0):>5.0%}  "
            f"{'OK' if s.get('pass') else 'FAIL':>4s}"
        )

    print("-" * 108)
    print(
        f"\nPhase 2 Summary: {passed}/{total} passed ({passed / total * 100:.0f}%) "
        f"in {total_time:.0f}s ({total_time / 60:.1f} min)"
    )

    if failed > 0:
        print(f"\nFAILED domains:")
        for domain_id, r in results.items():
            if not r.get("scores", {}).get("pass", False):
                s = r["scores"]
                reasons = []
                if s["entity_recall"] < 0.50:
                    reasons.append(f"recall={s['entity_recall']:.0%}")
                if s["entity_type_accuracy"] < 0.50:
                    reasons.append(f"type_acc={s['entity_type_accuracy']:.0%}")
                if s["relation_specificity"] < 0.40:
                    reasons.append(f"specificity={s['relation_specificity']:.0%}")
                if s["confidence_completeness"] < 0.70:
                    reasons.append(f"confidence={s['confidence_completeness']:.0%}")
                if s["strength_completeness"] < 0.50:
                    reasons.append(f"strength={s['strength_completeness']:.0%}")
                print(f"  {domain_id}: {', '.join(reasons)}")

    return {
        "phase": 2,
        "passed": passed,
        "failed": failed,
        "total": total,
        "total_duration_s": round(total_time, 1),
        "workers": workers,
        "domains": results,
    }


# ============================================================================
# Main
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="Verify domain extraction prompts")
    parser.add_argument("--format-only", action="store_true", help="Run Phase 1 only (no LLM)")
    parser.add_argument(
        "--domains", type=str, default=None, help="Comma-separated domain IDs to test"
    )
    parser.add_argument(
        "--workers", type=int, default=2, help="Parallel extraction workers (default: 2)"
    )
    args = parser.parse_args()

    filter_ids = set(args.domains.split(",")) if args.domains else None

    # Load domains
    domains = load_seed_domains()
    print(f"Loaded {len(domains)} domains from seed_domains.yaml")
    print(f"Example texts defined for {len(DOMAIN_EXAMPLES)} domains")
    if filter_ids:
        print(f"Filtering to: {filter_ids}")

    output_dir = Path(__file__).resolve().parent.parent / "data" / "evaluation" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Phase 1
    p1_results = phase1_format_verification(domains, filter_ids)

    p1_path = output_dir / "domain_prompt_format_verification.json"
    with open(p1_path, "w") as f:
        json.dump(p1_results, f, indent=2, default=str)
    print(f"\nPhase 1 results saved to: {p1_path}")

    if args.format_only:
        print("\n--format-only: Skipping Phase 2")
        return

    # Phase 2
    p2_results = asyncio.run(phase2_quality_verification(domains, filter_ids, args.workers))

    p2_path = output_dir / "domain_prompt_quality_verification.json"
    with open(p2_path, "w") as f:
        json.dump(p2_results, f, indent=2, default=str)
    print(f"\nPhase 2 results saved to: {p2_path}")

    # Overall summary
    print("\n" + "=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    print(f"Phase 1 (Format): {p1_results['passed']}/{p1_results['total']} passed")
    print(f"Phase 2 (Quality): {p2_results['passed']}/{p2_results['total']} passed")
    overall_pass = p1_results["passed"] == p1_results["total"] and p2_results["passed"] >= 28
    print(f"Overall: {'PASS' if overall_pass else 'NEEDS ATTENTION'}")


if __name__ == "__main__":
    main()
