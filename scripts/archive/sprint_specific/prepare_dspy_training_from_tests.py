#!/usr/bin/env python3
"""Prepare DSPy Training Data from Test Files.

This script creates gold-standard training data from our HuggingFace test files
for DSPy MIPROv2 optimization.

Sprint 86 Feature: DSPy Prompt Optimization
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

BASE_PATH = Path("/home/admin/projects/aegisrag/AEGIS_Rag")
OUTPUT_PATH = BASE_PATH / "data/dspy_training"

# Gold standard annotations for our test files
# These are manually curated based on the document content
GOLD_ANNOTATIONS = [
    # ============================================================================
    # Re-DocRED Files (Wikipedia) - Best performing domain (ER 1.04)
    # ============================================================================
    {
        "file": "redocred/redocred_0002.txt",
        "domain": "organizational",  # Geographic/administrative content
        "entities": [
            {"name": "Goght", "type": "LOCATION", "description": "Village in Armenia"},
            {"name": "Kotayk Province", "type": "LOCATION", "description": "Province of Armenia"},
            {"name": "Armenia", "type": "LOCATION", "description": "Country in South Caucasus"},
            {"name": "Azat River", "type": "LOCATION", "description": "River in Armenia"},
            {"name": "Garni", "type": "LOCATION", "description": "Town near Goght"},
            {"name": "Geghard Monastery", "type": "LOCATION", "description": "Medieval monastery"},
            {"name": "Havuts Tar", "type": "LOCATION", "description": "11th-13th century monastery"},
            {"name": "Garni Gorge", "type": "LOCATION", "description": "Gorge near Garni"},
            {"name": "basilica", "type": "BUILDING", "description": "17th-18th century church"},
            {"name": "khachkars", "type": "ARTIFACT", "description": "Armenian cross-stones"},
        ],
        "relations": [
            {"source": "Goght", "target": "Kotayk Province", "type": "LOCATED_IN", "strength": 10},
            {"source": "Kotayk Province", "target": "Armenia", "type": "PART_OF", "strength": 10},
            {"source": "Goght", "target": "Azat River", "type": "NEAR", "strength": 9},
            {"source": "Goght", "target": "Garni", "type": "NEAR", "strength": 9},
            {"source": "Garni", "target": "Geghard Monastery", "type": "CONNECTED_TO", "strength": 8},
            {"source": "Goght", "target": "Havuts Tar", "type": "OVERLOOKS", "strength": 8},
            {"source": "Havuts Tar", "target": "Garni Gorge", "type": "ACCESSIBLE_FROM", "strength": 7},
            {"source": "basilica", "target": "Goght", "type": "LOCATED_IN", "strength": 9},
            {"source": "khachkars", "target": "basilica", "type": "PART_OF", "strength": 8},
            {"source": "Goght", "target": "Armenia", "type": "LOCATED_IN", "strength": 10},
        ],
    },
    {
        "file": "redocred/redocred_0003.txt",
        "domain": "organizational",
        "entities": [
            {"name": "Adam Irigoyen", "type": "PERSON", "description": "American actor and dancer"},
            {"name": "United States", "type": "LOCATION", "description": "Country"},
            {"name": "Shake It Up", "type": "WORK", "description": "Disney Channel series"},
            {"name": "Disney Channel", "type": "ORGANIZATION", "description": "TV network"},
        ],
        "relations": [
            {"source": "Adam Irigoyen", "target": "United States", "type": "CITIZEN_OF", "strength": 10},
            {"source": "Adam Irigoyen", "target": "Shake It Up", "type": "ACTED_IN", "strength": 10},
            {"source": "Shake It Up", "target": "Disney Channel", "type": "BROADCAST_ON", "strength": 9},
        ],
    },
    # ============================================================================
    # CNN/DailyMail Files (News) - ER 0.91
    # ============================================================================
    {
        "file": "docred/cnn_0024.txt",
        "domain": "organizational",  # News/legal content
        "entities": [
            {"name": "Christina Mejia", "type": "PERSON", "description": "Mother of victim"},
            {"name": "Jessica Mejia", "type": "PERSON", "description": "Crash victim, 20 years old"},
            {"name": "Nicholas Sord", "type": "PERSON", "description": "Ex-boyfriend, driver"},
            {"name": "Cook County Sheriff's Office", "type": "ORGANIZATION", "description": "Law enforcement"},
            {"name": "Illinois", "type": "LOCATION", "description": "US State"},
            {"name": "Chicago", "type": "LOCATION", "description": "City in Illinois"},
            {"name": "University of Illinois at Chicago", "type": "ORGANIZATION", "description": "University"},
            {"name": "December 31, 2009", "type": "DATE", "description": "Date of crash"},
            {"name": "Don Perry", "type": "PERSON", "description": "Family attorney"},
            {"name": "Cara Smith", "type": "PERSON", "description": "Sheriff's spokeswoman"},
            {"name": "Denis Savard", "type": "PERSON", "description": "Former Chicago Blackhawks player"},
            {"name": "Bryan Sord", "type": "PERSON", "description": "Nicholas's father, developer"},
            {"name": "Chicago Blackhawks", "type": "ORGANIZATION", "description": "Hockey team"},
        ],
        "relations": [
            {"source": "Christina Mejia", "target": "Jessica Mejia", "type": "MOTHER_OF", "strength": 10},
            {"source": "Nicholas Sord", "target": "Jessica Mejia", "type": "EX_BOYFRIEND_OF", "strength": 10},
            {"source": "Nicholas Sord", "target": "Jessica Mejia", "type": "KILLED", "strength": 10},
            {"source": "Jessica Mejia", "target": "December 31, 2009", "type": "DIED_ON", "strength": 10},
            {"source": "Christina Mejia", "target": "Cook County Sheriff's Office", "type": "SUED", "strength": 9},
            {"source": "Don Perry", "target": "Christina Mejia", "type": "ATTORNEY_FOR", "strength": 9},
            {"source": "Cara Smith", "target": "Cook County Sheriff's Office", "type": "WORKS_FOR", "strength": 9},
            {"source": "Jessica Mejia", "target": "University of Illinois at Chicago", "type": "STUDIED_AT", "strength": 8},
            {"source": "Cook County Sheriff's Office", "target": "Illinois", "type": "LOCATED_IN", "strength": 9},
            {"source": "Nicholas Sord", "target": "Bryan Sord", "type": "SON_OF", "strength": 10},
            {"source": "Nicholas Sord", "target": "Denis Savard", "type": "BUSINESS_PARTNER_OF", "strength": 8},
            {"source": "Denis Savard", "target": "Chicago Blackhawks", "type": "PLAYED_FOR", "strength": 9},
            {"source": "Chicago", "target": "Illinois", "type": "LOCATED_IN", "strength": 10},
            {"source": "University of Illinois at Chicago", "target": "Chicago", "type": "LOCATED_IN", "strength": 10},
        ],
    },
    # ============================================================================
    # Technical Domain Examples
    # ============================================================================
    {
        "file": None,  # Synthetic example
        "domain": "technical",
        "text": """TensorFlow is an open-source machine learning framework developed by Google Brain team.
It was released in November 2015 and supports both Python and C++ programming languages.
TensorFlow 2.0, released in 2019, introduced Keras as its high-level API.
PyTorch, developed by Facebook AI Research, is the main competitor to TensorFlow.
Both frameworks support GPU acceleration via NVIDIA CUDA.""",
        "entities": [
            {"name": "TensorFlow", "type": "SOFTWARE", "description": "Open-source ML framework"},
            {"name": "Google Brain", "type": "ORGANIZATION", "description": "AI research team at Google"},
            {"name": "November 2015", "type": "DATE", "description": "TensorFlow release date"},
            {"name": "Python", "type": "LANGUAGE", "description": "Programming language"},
            {"name": "C++", "type": "LANGUAGE", "description": "Programming language"},
            {"name": "TensorFlow 2.0", "type": "SOFTWARE", "description": "Major TensorFlow version"},
            {"name": "Keras", "type": "SOFTWARE", "description": "High-level neural network API"},
            {"name": "PyTorch", "type": "SOFTWARE", "description": "ML framework by Facebook"},
            {"name": "Facebook AI Research", "type": "ORGANIZATION", "description": "AI research lab"},
            {"name": "NVIDIA CUDA", "type": "TECHNOLOGY", "description": "GPU computing platform"},
        ],
        "relations": [
            {"source": "Google Brain", "target": "TensorFlow", "type": "DEVELOPED", "strength": 10},
            {"source": "TensorFlow", "target": "November 2015", "type": "RELEASED_ON", "strength": 10},
            {"source": "TensorFlow", "target": "Python", "type": "SUPPORTS", "strength": 9},
            {"source": "TensorFlow", "target": "C++", "type": "SUPPORTS", "strength": 9},
            {"source": "TensorFlow 2.0", "target": "TensorFlow", "type": "VERSION_OF", "strength": 10},
            {"source": "TensorFlow 2.0", "target": "Keras", "type": "INTEGRATES", "strength": 9},
            {"source": "Facebook AI Research", "target": "PyTorch", "type": "DEVELOPED", "strength": 10},
            {"source": "PyTorch", "target": "TensorFlow", "type": "COMPETES_WITH", "strength": 8},
            {"source": "TensorFlow", "target": "NVIDIA CUDA", "type": "USES", "strength": 8},
            {"source": "PyTorch", "target": "NVIDIA CUDA", "type": "USES", "strength": 8},
        ],
    },
    {
        "file": None,  # Synthetic example
        "domain": "technical",
        "text": """Neo4j is a graph database management system developed by Neo4j, Inc.
It uses the Cypher query language for data manipulation. Neo4j supports ACID transactions
and is written in Java. The database is commonly used for recommendation engines,
fraud detection, and knowledge graphs. GraphQL can be used as an API layer on top of Neo4j.
LightRAG and GraphRAG are both retrieval-augmented generation systems that leverage Neo4j.""",
        "entities": [
            {"name": "Neo4j", "type": "SOFTWARE", "description": "Graph database system"},
            {"name": "Neo4j, Inc.", "type": "ORGANIZATION", "description": "Company behind Neo4j"},
            {"name": "Cypher", "type": "LANGUAGE", "description": "Graph query language"},
            {"name": "Java", "type": "LANGUAGE", "description": "Programming language"},
            {"name": "GraphQL", "type": "TECHNOLOGY", "description": "API query language"},
            {"name": "LightRAG", "type": "SOFTWARE", "description": "RAG system"},
            {"name": "GraphRAG", "type": "SOFTWARE", "description": "RAG system by Microsoft"},
        ],
        "relations": [
            {"source": "Neo4j, Inc.", "target": "Neo4j", "type": "DEVELOPED", "strength": 10},
            {"source": "Neo4j", "target": "Cypher", "type": "USES", "strength": 10},
            {"source": "Neo4j", "target": "Java", "type": "WRITTEN_IN", "strength": 10},
            {"source": "GraphQL", "target": "Neo4j", "type": "INTEGRATES_WITH", "strength": 7},
            {"source": "LightRAG", "target": "Neo4j", "type": "USES", "strength": 9},
            {"source": "GraphRAG", "target": "Neo4j", "type": "USES", "strength": 9},
        ],
    },
    # ============================================================================
    # Scientific Domain Examples
    # ============================================================================
    {
        "file": None,  # Synthetic example
        "domain": "scientific",
        "text": """BERT (Bidirectional Encoder Representations from Transformers) was introduced
by Google AI Language in 2018. It achieved state-of-the-art results on 11 NLP benchmarks
including GLUE, SQuAD, and CoNLL-2003. The model uses a masked language model (MLM)
pre-training objective. GPT-3, released by OpenAI in 2020, has 175 billion parameters
compared to BERT's 340 million. Both models are based on the Transformer architecture
introduced in the "Attention Is All You Need" paper by Vaswani et al. in 2017.""",
        "entities": [
            {"name": "BERT", "type": "MODEL", "description": "Bidirectional language model"},
            {"name": "Google AI Language", "type": "ORGANIZATION", "description": "Research team"},
            {"name": "2018", "type": "DATE", "description": "BERT release year"},
            {"name": "GLUE", "type": "DATASET", "description": "NLP benchmark"},
            {"name": "SQuAD", "type": "DATASET", "description": "Question answering dataset"},
            {"name": "CoNLL-2003", "type": "DATASET", "description": "NER dataset"},
            {"name": "GPT-3", "type": "MODEL", "description": "Large language model"},
            {"name": "OpenAI", "type": "ORGANIZATION", "description": "AI research company"},
            {"name": "2020", "type": "DATE", "description": "GPT-3 release year"},
            {"name": "Transformer", "type": "ARCHITECTURE", "description": "Neural network architecture"},
            {"name": "Vaswani et al.", "type": "AUTHOR", "description": "Transformer paper authors"},
            {"name": "2017", "type": "DATE", "description": "Transformer paper year"},
        ],
        "relations": [
            {"source": "Google AI Language", "target": "BERT", "type": "INTRODUCED", "strength": 10},
            {"source": "BERT", "target": "2018", "type": "RELEASED_IN", "strength": 10},
            {"source": "BERT", "target": "GLUE", "type": "EVALUATED_ON", "strength": 9},
            {"source": "BERT", "target": "SQuAD", "type": "EVALUATED_ON", "strength": 9},
            {"source": "BERT", "target": "CoNLL-2003", "type": "EVALUATED_ON", "strength": 9},
            {"source": "OpenAI", "target": "GPT-3", "type": "RELEASED", "strength": 10},
            {"source": "GPT-3", "target": "2020", "type": "RELEASED_IN", "strength": 10},
            {"source": "BERT", "target": "Transformer", "type": "BASED_ON", "strength": 10},
            {"source": "GPT-3", "target": "Transformer", "type": "BASED_ON", "strength": 10},
            {"source": "Vaswani et al.", "target": "Transformer", "type": "CREATED", "strength": 10},
            {"source": "Transformer", "target": "2017", "type": "INTRODUCED_IN", "strength": 10},
            {"source": "GPT-3", "target": "BERT", "type": "LARGER_THAN", "strength": 8},
        ],
    },
    # ============================================================================
    # Hard Negatives (NO RELATIONS - teach precision)
    # ============================================================================
    {
        "file": None,
        "domain": "technical",
        "text": "Python and Java are popular programming languages. Both are used widely in enterprise development.",
        "entities": [
            {"name": "Python", "type": "LANGUAGE", "description": "Programming language"},
            {"name": "Java", "type": "LANGUAGE", "description": "Programming language"},
        ],
        "relations": [],  # NO RELATIONS - just enumeration
    },
    {
        "file": None,
        "domain": "organizational",
        "text": "The meeting is scheduled for Monday. TensorFlow performance will be discussed during the session.",
        "entities": [
            {"name": "Monday", "type": "DATE", "description": "Day of week"},
            {"name": "TensorFlow", "type": "SOFTWARE", "description": "ML framework"},
        ],
        "relations": [],  # NO RELATIONS - different contexts
    },
    {
        "file": None,
        "domain": "organizational",
        "text": "Apple announced new iPhone models. Google released Android 15. Microsoft updated Windows.",
        "entities": [
            {"name": "Apple", "type": "ORGANIZATION", "description": "Tech company"},
            {"name": "iPhone", "type": "PRODUCT", "description": "Smartphone"},
            {"name": "Google", "type": "ORGANIZATION", "description": "Tech company"},
            {"name": "Android 15", "type": "SOFTWARE", "description": "Mobile OS"},
            {"name": "Microsoft", "type": "ORGANIZATION", "description": "Tech company"},
            {"name": "Windows", "type": "SOFTWARE", "description": "Operating system"},
        ],
        "relations": [
            # Only internal relations, no cross-company relations
            {"source": "Apple", "target": "iPhone", "type": "PRODUCES", "strength": 10},
            {"source": "Google", "target": "Android 15", "type": "RELEASED", "strength": 10},
            {"source": "Microsoft", "target": "Windows", "type": "PRODUCES", "strength": 10},
        ],
    },
]


def load_file_content(file_path: str) -> str:
    """Load text content from file, removing header comments."""
    full_path = BASE_PATH / "data/hf_relation_datasets" / file_path
    if not full_path.exists():
        return None

    text = full_path.read_text()
    # Remove header comments
    lines = text.split("\n")
    content_lines = [l for l in lines if not l.startswith("#")]
    return "\n".join(content_lines).strip()


def create_training_data():
    """Create DSPy training data from gold annotations."""
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

    training_data = []

    for annotation in GOLD_ANNOTATIONS:
        # Get text content
        if annotation.get("file"):
            text = load_file_content(annotation["file"])
            if text is None:
                print(f"Warning: File not found: {annotation['file']}")
                continue
        else:
            text = annotation.get("text", "")

        if not text:
            continue

        # Create training example
        example = {
            "text": text.strip(),
            "domain": annotation["domain"],
            "entities": annotation["entities"],
            "relations": annotation["relations"],
            "metadata": {
                "source_file": annotation.get("file", "synthetic"),
                "entity_count": len(annotation["entities"]),
                "relation_count": len(annotation["relations"]),
                "er_ratio": len(annotation["relations"]) / max(len(annotation["entities"]), 1),
            }
        }

        training_data.append(example)

    # Split into train/val/test (70/15/15)
    n = len(training_data)
    train_idx = int(n * 0.7)
    val_idx = int(n * 0.85)

    train_data = training_data[:train_idx]
    val_data = training_data[train_idx:val_idx]
    test_data = training_data[val_idx:]

    # Ensure we have at least 1 sample in each split
    if len(train_data) < 1:
        train_data = training_data[:1]
    if len(val_data) < 1 and len(training_data) > 1:
        val_data = [training_data[1]] if len(training_data) > 1 else training_data[:1]
    if len(test_data) < 1 and len(training_data) > 2:
        test_data = [training_data[2]] if len(training_data) > 2 else training_data[:1]

    # Save to JSONL files
    def save_jsonl(data: list, filename: str):
        filepath = OUTPUT_PATH / filename
        with open(filepath, "w") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")
        print(f"Saved {len(data)} examples to {filepath}")

    save_jsonl(train_data, "train.jsonl")
    save_jsonl(val_data, "val.jsonl")
    save_jsonl(test_data, "test.jsonl")
    save_jsonl(training_data, "all.jsonl")

    # Summary
    print("\n" + "=" * 60)
    print("TRAINING DATA SUMMARY")
    print("=" * 60)
    print(f"Total examples: {len(training_data)}")
    print(f"  Train: {len(train_data)}")
    print(f"  Validation: {len(val_data)}")
    print(f"  Test: {len(test_data)}")

    # Domain distribution
    domains = {}
    for example in training_data:
        d = example["domain"]
        domains[d] = domains.get(d, 0) + 1

    print("\nDomain distribution:")
    for domain, count in sorted(domains.items()):
        print(f"  {domain}: {count}")

    # ER ratio statistics
    er_ratios = [e["metadata"]["er_ratio"] for e in training_data]
    avg_er = sum(er_ratios) / len(er_ratios) if er_ratios else 0

    print(f"\nER Ratio statistics:")
    print(f"  Average: {avg_er:.2f}")
    print(f"  Min: {min(er_ratios):.2f}")
    print(f"  Max: {max(er_ratios):.2f}")

    # Hard negatives count
    hard_negatives = sum(1 for e in training_data if len(e["relations"]) == 0)
    print(f"\nHard negatives (no relations): {hard_negatives}")

    print(f"\nOutput directory: {OUTPUT_PATH}")

    return training_data


if __name__ == "__main__":
    create_training_data()
