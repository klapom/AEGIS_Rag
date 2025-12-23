"""Training dataset fixtures for domain creation E2E tests.

This module provides fixtures for DSPy domain training:
- Sample training datasets in JSONL format with text, entities, relations
- Various domain types (legal, medical, technical)
- Dataset validation utilities

JSONL Format (per line):
{"text": "...", "entities": ["entity1", "entity2"], "relations": [...]}
"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def legal_domain_training_dataset(tmp_path: Path) -> Path:
    """Create a legal domain training dataset in JSONL format.

    This dataset contains legal text samples with entities and relations
    for training a legal domain classifier.

    Returns:
        Path to JSONL training dataset file
    """
    samples = [
        {
            "text": "A force majeure clause is a contract provision that relieves parties from performing their contractual obligations when certain circumstances beyond their control arise, making performance inadvisable, commercially impracticable, illegal, or impossible.",
            "entities": [
                "force majeure clause",
                "contract provision",
                "contractual obligations",
                "performance",
            ],
            "relations": [
                {
                    "subject": "force majeure clause",
                    "predicate": "is_a",
                    "object": "contract provision",
                },
                {
                    "subject": "force majeure clause",
                    "predicate": "relieves",
                    "object": "contractual obligations",
                },
            ],
        },
        {
            "text": "Indemnification clauses require one party to compensate the other for losses, damages, or liabilities arising from specific events or breaches of contract terms.",
            "entities": [
                "indemnification clauses",
                "compensation",
                "losses",
                "damages",
                "liabilities",
                "breaches",
            ],
            "relations": [
                {
                    "subject": "indemnification clauses",
                    "predicate": "require",
                    "object": "compensation",
                }
            ],
        },
        {
            "text": "Termination conditions typically include breach of contract, mutual agreement, completion of contract term, or occurrence of specified events that allow early termination.",
            "entities": [
                "termination conditions",
                "breach of contract",
                "mutual agreement",
                "early termination",
            ],
            "relations": [
                {
                    "subject": "termination conditions",
                    "predicate": "include",
                    "object": "breach of contract",
                }
            ],
        },
        {
            "text": "A representation is a statement of fact made before or at contract formation, while a warranty is a promise about the present or future state of facts that forms part of the contract terms.",
            "entities": [
                "representation",
                "statement of fact",
                "warranty",
                "promise",
                "contract terms",
            ],
            "relations": [
                {"subject": "representation", "predicate": "is_a", "object": "statement of fact"},
                {"subject": "warranty", "predicate": "is_a", "object": "promise"},
            ],
        },
        {
            "text": "Confidentiality obligations require parties to keep certain information secret, restrict disclosure to third parties, and use the information only for specified purposes.",
            "entities": [
                "confidentiality obligations",
                "secret information",
                "disclosure",
                "third parties",
            ],
            "relations": [
                {
                    "subject": "confidentiality obligations",
                    "predicate": "restrict",
                    "object": "disclosure",
                }
            ],
        },
        {
            "text": "A material breach is a significant violation of contract terms that undermines the contract's purpose and gives the non-breaching party the right to terminate the agreement and seek damages.",
            "entities": ["material breach", "contract terms", "non-breaching party", "damages"],
            "relations": [
                {
                    "subject": "material breach",
                    "predicate": "undermines",
                    "object": "contract terms",
                }
            ],
        },
        {
            "text": "Liquidated damages are predetermined amounts specified in a contract to be paid if a party breaches, serving as a reasonable estimate of anticipated or actual harm.",
            "entities": ["liquidated damages", "predetermined amounts", "breach", "harm"],
            "relations": [
                {"subject": "liquidated damages", "predicate": "estimate", "object": "harm"}
            ],
        },
        {
            "text": "An assignment clause governs whether and how parties can transfer their rights and obligations under the contract to third parties without consent.",
            "entities": ["assignment clause", "rights", "obligations", "third parties", "consent"],
            "relations": [
                {"subject": "assignment clause", "predicate": "governs", "object": "rights"}
            ],
        },
        {
            "text": "The statute of limitations sets the maximum time period after an event within which legal proceedings may be initiated, varying by jurisdiction and type of claim.",
            "entities": [
                "statute of limitations",
                "time period",
                "legal proceedings",
                "jurisdiction",
            ],
            "relations": [
                {"subject": "statute of limitations", "predicate": "sets", "object": "time period"}
            ],
        },
        {
            "text": "Arbitration is a private dispute resolution process with a neutral arbitrator, while litigation is a public court process with a judge or jury. Arbitration is typically faster and more confidential.",
            "entities": [
                "arbitration",
                "dispute resolution",
                "arbitrator",
                "litigation",
                "court process",
                "judge",
            ],
            "relations": [
                {"subject": "arbitration", "predicate": "is_a", "object": "dispute resolution"},
                {"subject": "litigation", "predicate": "is_a", "object": "court process"},
            ],
        },
        {
            "text": "IP indemnification protects a party from losses arising from claims that products or services infringe third-party patents, copyrights, trademarks, or trade secrets.",
            "entities": [
                "IP indemnification",
                "patents",
                "copyrights",
                "trademarks",
                "trade secrets",
            ],
            "relations": [
                {"subject": "IP indemnification", "predicate": "protects_from", "object": "patents"}
            ],
        },
        {
            "text": "A severability clause ensures that if one contract provision is found invalid or unenforceable, the remaining provisions continue in full force and effect.",
            "entities": ["severability clause", "contract provision", "invalid", "unenforceable"],
            "relations": [
                {
                    "subject": "severability clause",
                    "predicate": "ensures",
                    "object": "contract provision",
                }
            ],
        },
        {
            "text": "Consideration is something of value exchanged between parties that is essential for a contract to be legally binding - it can be money, services, goods, or a promise.",
            "entities": [
                "consideration",
                "value",
                "contract",
                "legally binding",
                "money",
                "services",
            ],
            "relations": [
                {"subject": "consideration", "predicate": "essential_for", "object": "contract"}
            ],
        },
        {
            "text": "Fraud requires: (1) false representation of material fact, (2) knowledge of falsity, (3) intent to deceive, (4) justifiable reliance by victim, and (5) resulting damages.",
            "entities": [
                "fraud",
                "false representation",
                "material fact",
                "intent to deceive",
                "damages",
            ],
            "relations": [
                {"subject": "fraud", "predicate": "requires", "object": "false representation"}
            ],
        },
        {
            "text": "The parol evidence rule prevents parties from introducing prior or contemporaneous oral or written statements to contradict or modify the terms of a written contract.",
            "entities": [
                "parol evidence rule",
                "oral statements",
                "written statements",
                "written contract",
            ],
            "relations": [
                {
                    "subject": "parol evidence rule",
                    "predicate": "prevents",
                    "object": "oral statements",
                }
            ],
        },
    ]

    dataset_path = tmp_path / "legal_training_dataset.jsonl"
    with open(dataset_path, "w") as f:
        for sample in samples:
            f.write(json.dumps(sample) + "\n")
    return dataset_path


@pytest.fixture
def medical_domain_training_dataset(tmp_path: Path) -> Path:
    """Create a medical domain training dataset in JSONL format.

    Returns:
        Path to JSONL training dataset file
    """
    samples = [
        {
            "text": "Common symptoms of Type 2 diabetes include increased thirst, frequent urination, increased hunger, unexplained weight loss, fatigue, blurred vision, slow-healing sores, and frequent infections.",
            "entities": [
                "Type 2 diabetes",
                "increased thirst",
                "frequent urination",
                "fatigue",
                "blurred vision",
            ],
            "relations": [
                {
                    "subject": "Type 2 diabetes",
                    "predicate": "has_symptom",
                    "object": "increased thirst",
                },
                {"subject": "Type 2 diabetes", "predicate": "has_symptom", "object": "fatigue"},
            ],
        },
        {
            "text": "ACE inhibitors block angiotensin-converting enzyme, preventing conversion of angiotensin I to angiotensin II, leading to vasodilation and reduced blood pressure.",
            "entities": [
                "ACE inhibitors",
                "angiotensin-converting enzyme",
                "angiotensin I",
                "angiotensin II",
                "vasodilation",
                "blood pressure",
            ],
            "relations": [
                {
                    "subject": "ACE inhibitors",
                    "predicate": "block",
                    "object": "angiotensin-converting enzyme",
                },
                {"subject": "ACE inhibitors", "predicate": "reduces", "object": "blood pressure"},
            ],
        },
        {
            "text": "MRI uses magnetic fields and radio waves to create detailed soft tissue images without radiation, while CT uses X-rays to produce cross-sectional images and is faster but involves radiation exposure.",
            "entities": ["MRI", "magnetic fields", "radio waves", "CT", "X-rays", "radiation"],
            "relations": [
                {"subject": "MRI", "predicate": "uses", "object": "magnetic fields"},
                {"subject": "CT", "predicate": "uses", "object": "X-rays"},
            ],
        },
        {
            "text": "Wound healing occurs in four stages: hemostasis (blood clotting), inflammation (immune response), proliferation (tissue growth), and remodeling (scar maturation).",
            "entities": [
                "wound healing",
                "hemostasis",
                "inflammation",
                "proliferation",
                "remodeling",
            ],
            "relations": [
                {"subject": "wound healing", "predicate": "has_stage", "object": "hemostasis"},
                {"subject": "wound healing", "predicate": "has_stage", "object": "inflammation"},
            ],
        },
        {
            "text": "Heart failure occurs when the heart cannot pump sufficient blood to meet the body's needs, leading to fluid accumulation, reduced cardiac output, and activation of compensatory mechanisms.",
            "entities": [
                "heart failure",
                "blood",
                "fluid accumulation",
                "cardiac output",
                "compensatory mechanisms",
            ],
            "relations": [
                {"subject": "heart failure", "predicate": "causes", "object": "fluid accumulation"}
            ],
        },
        {
            "text": "NSAID contraindications include active peptic ulcer disease, severe renal impairment, severe heart failure, history of NSAID-induced asthma, and third trimester pregnancy.",
            "entities": [
                "NSAID",
                "contraindications",
                "peptic ulcer disease",
                "renal impairment",
                "heart failure",
            ],
            "relations": [
                {
                    "subject": "NSAID",
                    "predicate": "contraindicated_in",
                    "object": "peptic ulcer disease",
                }
            ],
        },
        {
            "text": "HbA1c measures average blood glucose levels over the past 2-3 months by assessing glycated hemoglobin percentage. Target for diabetics is typically below 7%.",
            "entities": ["HbA1c", "blood glucose", "glycated hemoglobin", "diabetics"],
            "relations": [{"subject": "HbA1c", "predicate": "measures", "object": "blood glucose"}],
        },
        {
            "text": "FAST stands for Face drooping, Arm weakness, Speech difficulty, Time to call emergency services. It's a quick stroke recognition tool for immediate intervention.",
            "entities": ["FAST", "Face drooping", "Arm weakness", "Speech difficulty", "stroke"],
            "relations": [
                {"subject": "FAST", "predicate": "assesses", "object": "Face drooping"},
                {"subject": "FAST", "predicate": "diagnoses", "object": "stroke"},
            ],
        },
        {
            "text": "Systolic pressure (top number) measures arterial pressure during heart contraction, while diastolic pressure (bottom number) measures pressure between heartbeats when the heart relaxes.",
            "entities": [
                "systolic pressure",
                "diastolic pressure",
                "arterial pressure",
                "heart contraction",
            ],
            "relations": [
                {
                    "subject": "systolic pressure",
                    "predicate": "measures_during",
                    "object": "heart contraction",
                }
            ],
        },
        {
            "text": "Common corticosteroid side effects include weight gain, increased appetite, mood changes, elevated blood sugar, osteoporosis, increased infection risk, and adrenal suppression with long-term use.",
            "entities": [
                "corticosteroid",
                "side effects",
                "weight gain",
                "osteoporosis",
                "adrenal suppression",
            ],
            "relations": [
                {"subject": "corticosteroid", "predicate": "causes", "object": "weight gain"},
                {"subject": "corticosteroid", "predicate": "causes", "object": "osteoporosis"},
            ],
        },
    ]

    dataset_path = tmp_path / "medical_training_dataset.jsonl"
    with open(dataset_path, "w") as f:
        for sample in samples:
            f.write(json.dumps(sample) + "\n")
    return dataset_path


@pytest.fixture
def technical_domain_training_dataset(tmp_path: Path) -> Path:
    """Create a technical domain training dataset in JSONL format.

    Returns:
        Path to JSONL training dataset file
    """
    samples = [
        {
            "text": "REST uses multiple endpoints with fixed data structures, while GraphQL uses a single endpoint where clients specify exactly what data they need, reducing over-fetching.",
            "entities": ["REST", "endpoints", "GraphQL", "data structures", "over-fetching"],
            "relations": [
                {"subject": "REST", "predicate": "uses", "object": "endpoints"},
                {"subject": "GraphQL", "predicate": "reduces", "object": "over-fetching"},
            ],
        },
        {
            "text": "CAP theorem states distributed systems can only guarantee two of three properties: Consistency (all nodes see same data), Availability (system always responds), and Partition tolerance (system works despite network failures).",
            "entities": [
                "CAP theorem",
                "distributed systems",
                "Consistency",
                "Availability",
                "Partition tolerance",
            ],
            "relations": [
                {
                    "subject": "CAP theorem",
                    "predicate": "applies_to",
                    "object": "distributed systems",
                }
            ],
        },
        {
            "text": "Container orchestration automates deployment, scaling, networking, and management of containerized applications using platforms like Kubernetes, Docker Swarm, or ECS.",
            "entities": [
                "container orchestration",
                "deployment",
                "scaling",
                "Kubernetes",
                "Docker Swarm",
                "ECS",
            ],
            "relations": [
                {
                    "subject": "container orchestration",
                    "predicate": "automates",
                    "object": "deployment",
                },
                {"subject": "Kubernetes", "predicate": "is_a", "object": "container orchestration"},
            ],
        },
        {
            "text": "SQL databases use structured schemas with ACID properties and are ideal for complex queries, while NoSQL databases offer flexible schemas, horizontal scaling, and are optimized for specific data models.",
            "entities": [
                "SQL databases",
                "ACID properties",
                "NoSQL databases",
                "horizontal scaling",
                "data models",
            ],
            "relations": [
                {"subject": "SQL databases", "predicate": "has", "object": "ACID properties"},
                {
                    "subject": "NoSQL databases",
                    "predicate": "offers",
                    "object": "horizontal scaling",
                },
            ],
        },
        {
            "text": "CI/CD automates code integration, testing, and deployment. CI merges code changes frequently with automated tests, while CD automatically deploys tested code to production.",
            "entities": ["CI/CD", "code integration", "testing", "deployment", "production"],
            "relations": [
                {"subject": "CI/CD", "predicate": "automates", "object": "code integration"},
                {"subject": "CI/CD", "predicate": "automates", "object": "deployment"},
            ],
        },
        {
            "text": "SOLID principles are: Single Responsibility, Open-Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion - fundamental object-oriented design principles for maintainable code.",
            "entities": [
                "SOLID principles",
                "Single Responsibility",
                "Open-Closed",
                "Liskov Substitution",
                "Interface Segregation",
                "Dependency Inversion",
            ],
            "relations": [
                {
                    "subject": "SOLID principles",
                    "predicate": "includes",
                    "object": "Single Responsibility",
                }
            ],
        },
        {
            "text": "Authentication verifies who you are (identity verification), while authorization determines what you can access (permission verification) after authentication.",
            "entities": [
                "authentication",
                "identity verification",
                "authorization",
                "permission verification",
            ],
            "relations": [
                {
                    "subject": "authentication",
                    "predicate": "performs",
                    "object": "identity verification",
                },
                {
                    "subject": "authorization",
                    "predicate": "determines",
                    "object": "permission verification",
                },
            ],
        },
        {
            "text": "Microservices architecture decomposes applications into small, independent services that communicate via APIs, enabling independent deployment, scaling, and technology choices.",
            "entities": [
                "microservices architecture",
                "applications",
                "services",
                "APIs",
                "deployment",
            ],
            "relations": [
                {
                    "subject": "microservices architecture",
                    "predicate": "decomposes",
                    "object": "applications",
                }
            ],
        },
        {
            "text": "A reverse proxy sits between clients and servers, handling requests by load balancing, caching, SSL termination, and providing security, improving performance and reliability.",
            "entities": [
                "reverse proxy",
                "clients",
                "servers",
                "load balancing",
                "caching",
                "SSL termination",
            ],
            "relations": [
                {"subject": "reverse proxy", "predicate": "provides", "object": "load balancing"},
                {"subject": "reverse proxy", "predicate": "provides", "object": "caching"},
            ],
        },
        {
            "text": "Horizontal scaling adds more machines to distribute load, while vertical scaling increases resources (CPU, RAM) on existing machines. Horizontal scaling offers better fault tolerance.",
            "entities": ["horizontal scaling", "vertical scaling", "CPU", "RAM", "fault tolerance"],
            "relations": [
                {
                    "subject": "horizontal scaling",
                    "predicate": "provides",
                    "object": "fault tolerance",
                }
            ],
        },
    ]

    dataset_path = tmp_path / "technical_training_dataset.jsonl"
    with open(dataset_path, "w") as f:
        for sample in samples:
            f.write(json.dumps(sample) + "\n")
    return dataset_path


def validate_training_dataset(dataset_path: Path) -> bool:
    """Validate training dataset structure (JSONL format).

    Args:
        dataset_path: Path to training dataset JSONL file

    Returns:
        True if dataset is valid, raises ValueError otherwise
    """
    try:
        samples = []
        with open(dataset_path) as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    sample = json.loads(line)
                    samples.append(sample)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON on line {line_num}: {e}")

        # Validate minimum samples
        if len(samples) < 10:
            raise ValueError(
                f"Training dataset must contain at least 10 samples (found {len(samples)})"
            )

        # Validate each sample
        for i, sample in enumerate(samples):
            if "text" not in sample:
                raise ValueError(f"Sample {i+1} missing 'text' field")
            if "entities" not in sample or not isinstance(sample["entities"], list):
                raise ValueError(f"Sample {i+1} missing or invalid 'entities' field")

        return True

    except FileNotFoundError:
        raise ValueError(f"Dataset file not found: {dataset_path}")
