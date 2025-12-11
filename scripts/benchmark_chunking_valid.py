#!/usr/bin/env python3
"""
Valid Chunk-Size Benchmark
Uses a LARGE text sample (~12000 chars) so chunking actually has an effect.
Tests chunk sizes: 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 10000

The text is a concatenation of Wikipedia-style information about various topics.
"""
import json
import time
import requests
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ~12000 character sample with diverse entities and relationships
# Concatenated from multiple factual topics to simulate real document processing
LARGE_SAMPLE_TEXT = """
Albert Einstein (14 March 1879 - 18 April 1955) was a German-born theoretical physicist who is widely held to be one of the greatest and most influential scientists of all time. He is best known for developing the theory of relativity, but he also made important contributions to quantum mechanics, and was thus a central figure in the revolutionary reshaping of the scientific understanding of nature that modern physics accomplished in the first decades of the twentieth century. His mass-energy equivalence formula E = mc2, which arises from relativity theory, has been called "the world's most famous equation". He received the 1921 Nobel Prize in Physics "for his services to theoretical physics, and especially for his discovery of the law of the photoelectric effect", a pivotal step in the development of quantum theory. His work is also known for its influence on the philosophy of science. In a 1999 poll of 130 leading physicists worldwide by the British journal Physics World, Einstein was ranked the greatest physicist of all time. His intellectual achievements and originality have made the word Einstein broadly synonymous with genius.

Einstein was born in the German Empire, but moved to Switzerland in 1895, forsaking his German citizenship the following year. In 1897, at the age of seventeen, he enrolled in the mathematics and physics teaching diploma program at the Swiss federal polytechnic school in Zurich, graduating in 1900. In 1901, he acquired Swiss citizenship, which he kept for the rest of his life. In 1903, he secured a permanent position at the Swiss Patent Office in Bern. In 1905, he submitted his thesis and was awarded a PhD by the University of Zurich. In 1914, Einstein moved to Berlin in order to join the Prussian Academy of Sciences and the Humboldt University of Berlin. In 1917, Einstein became director of the Kaiser Wilhelm Institute for Physics.

The Oberoi Group is a hotel company with its head office in Delhi, India. Founded in 1934, the company owns and operates luxury hotels and cruisers in six countries under the luxury Oberoi Hotels & Resorts brand and five-star hotels under the Trident Hotels brand. The company also operates an airport hotel, Trident Jeddah, at King Abdulaziz International Airport in Jeddah, Saudi Arabia.

The company was founded by Rai Bahadur Mohan Singh Oberoi, who was born in 1898 in Bhaun, a small village in the Rawalpindi District of British India. He started his career as a clerk at The Cecil Hotel in Shimla and eventually acquired the hotel in 1934, marking the beginning of The Oberoi Group. Under his leadership, the company expanded significantly, acquiring and building numerous properties across India and internationally.

Prithvi Raj Singh Oberoi, commonly known as PRS Oberoi, is the current chairman of The Oberoi Group. Born in 1929, he is the son of Rai Bahadur Mohan Singh Oberoi. He has been instrumental in transforming The Oberoi Group into a global luxury hotel chain. Under his stewardship, the company has won numerous awards for service excellence and is recognized as one of the best hotel groups in the world.

Apple Inc. is an American multinational technology company headquartered in Cupertino, California. Apple is the world's largest technology company by revenue, with US$394.3 billion in 2022 revenue. As of March 2023, Apple is the world's biggest company by market capitalization. As of June 2022, Apple is the fourth-largest personal computer vendor by unit sales and the second-largest mobile phone manufacturer in the world.

Apple was founded as Apple Computer Company on April 1, 1976, by Steve Wozniak, Steve Jobs and Ronald Wayne to develop and sell Wozniak's Apple I personal computer. It was incorporated by Jobs and Wozniak as Apple Computer, Inc. in 1977. The company's second computer, the Apple II, became a best seller and one of the first mass-produced microcomputers. Apple went public in 1980 to instant financial success. The company developed computers featuring innovative graphical user interfaces, including the 1984 original Macintosh, announced that year in a critically acclaimed advertisement called "1984".

Steve Jobs (February 24, 1955 - October 5, 2011) was an American businessman and inventor who co-founded Apple Inc. and served as its chairman, chief executive officer, and, briefly, president. He was also chairman and majority shareholder of Pixar, a member of The Walt Disney Company's board of directors following its acquisition of Pixar, and the founder, chairman, and CEO of NeXT. He is widely recognized as a pioneer of the personal computer revolution of the 1970s and 1980s, along with his early business partner and fellow Apple co-founder Steve Wozniak.

The United Nations (UN) is an intergovernmental organization whose purpose is to maintain international peace and security, develop friendly relations among nations, achieve international cooperation, and serve as a centre for harmonizing the actions of nations. It is the world's largest international organization. The UN is headquartered in New York City, in international territory with certain privileges extraterritorial to the United States, and has other main offices in Geneva, Nairobi, Vienna, and The Hague.

The UN was established after World War II with the aim of preventing future world wars, and succeeded the League of Nations, which was characterized as ineffective. On 25 April 1945, 50 nations met in San Francisco, California for a conference and started drafting the UN Charter, which was adopted on 25 June 1945. The charter took effect on 24 October 1945, when the UN began operations. The organization's objectives include maintaining international peace and security, protecting human rights, delivering humanitarian aid, promoting sustainable development, and upholding international law.

Microsoft Corporation is an American multinational technology corporation headquartered in Redmond, Washington. Microsoft's best-known software products are the Windows line of operating systems, the Microsoft 365 suite of productivity applications, the Azure cloud computing platform, and the Edge web browser. Its flagship hardware products are the Xbox video game consoles and the Microsoft Surface lineup of touchscreen personal computers.

Microsoft was founded by Bill Gates and Paul Allen on April 4, 1975, to develop and sell BASIC interpreters for the Altair 8800. During his career at Microsoft, Gates held the positions of chairman, chief executive officer, president and chief software architect, while also being the largest individual shareholder until May 2014. Paul Allen remained with the company until 1983, when he left due to illness.

The Amazon River in South America is the largest river by discharge volume of water in the world, and the disputed longest river in the world in comparison to the Nile. The headwaters of the Apurimac River on Nevado Mismi had been considered for nearly a century as the Amazon's most distant source, until a 2014 study found it to be the headwaters of the Mantaro River on the Cordillera Rumi Cruz in Peru. The Mantaro and Apurimac rivers join, and with other tributaries form the Ucayali River, which in turn meets the Maranon River upstream of Iquitos, Peru, to form what countries other than Brazil consider to be the main stem of the Amazon.

Amazon.com, Inc., doing business as Amazon, is an American multinational technology company focusing on e-commerce, cloud computing, online advertising, digital streaming, and artificial intelligence. It is considered one of the Big Five American technology companies; the other four are Alphabet, Apple, Meta, and Microsoft. Amazon was founded by Jeff Bezos from his garage in Bellevue, Washington, on July 5, 1994. Initially an online marketplace for books, it has expanded into a multitude of product categories, a strategy that has earned it the moniker "The Everything Store".

SpaceX, founded by Elon Musk in 2002, is an American aerospace manufacturer and space transportation company headquartered in Hawthorne, California. SpaceX has developed several launch vehicles, the Starlink satellite internet constellation, the Dragon spacecraft, and Starship. SpaceX is developing Starlink, a satellite internet constellation intended to eventually consist of many thousands of satellites. SpaceX has launched commercial satellites and the company's Starlink satellites using its Falcon 9 rocket.

Tesla, Inc. is an American multinational automotive and clean energy company headquartered in Austin, Texas. Tesla designs and manufactures electric vehicles (cars and trucks), stationary battery energy storage devices from home to grid-scale, solar panels and solar roof tiles, and related products and services. Tesla is one of the world's most valuable companies and is the world's most valuable automaker. In 2022, the company had the most worldwide sales of battery electric vehicles and plug-in electric vehicles, capturing 18% of the battery-electric market and 14% of the plug-in market.

Google LLC is an American multinational technology company focusing on artificial intelligence, online advertising, search engine technology, cloud computing, computer software, quantum computing, e-commerce, and consumer electronics. It has been referred to as the most powerful company in the world and is one of the world's most valuable brands due to its market dominance, data collection, and technological advantages in the area of artificial intelligence. Google's parent company Alphabet Inc. is one of the five Big Tech companies, alongside Amazon, Apple, Meta, and Microsoft.

Google was founded on September 4, 1998, by American computer scientists Larry Page and Sergey Brin while they were PhD students at Stanford University in California. Together they own about 14% of its publicly listed shares and control 56% of its stockholder voting power through super-voting stock. The company went public via an initial public offering in 2004. In 2015, Google was reorganized as a wholly-owned subsidiary of Alphabet Inc. Google is Alphabet's largest subsidiary and is a holding company for Alphabet's internet properties and interests.

Meta Platforms, Inc., doing business as Meta, is an American multinational technology conglomerate headquartered in Menlo Park, California. The company owns and operates Facebook, Instagram, Threads, and WhatsApp, among other products and services. Meta is one of the world's most valuable companies and is among the Big Five American technology companies, alongside Alphabet (Google), Amazon, Apple, and Microsoft.

Meta was founded by Mark Zuckerberg, along with his Harvard College roommates and fellow students Eduardo Saverin, Andrew McCollum, Dustin Moskovitz, and Chris Hughes, originally as TheFacebook.com, today known as Facebook. The company went public in 2012 with one of the largest technology IPOs. In October 2021, the parent company of Facebook changed its name from Facebook, Inc. to Meta Platforms, Inc., reflecting its focus on building the metaverse.

NVIDIA Corporation is an American multinational corporation and technology company headquartered in Santa Clara, California, and incorporated in Delaware. It is a software and fabless company which designs and supplies graphics processing units (GPUs), application programming interfaces (APIs) for data science and high-performance computing, as well as system on a chip units (SoCs) for the mobile computing and automotive market. NVIDIA is also a dominant supplier of artificial intelligence hardware and software.

NVIDIA was founded on January 1993 by Jensen Huang, a Taiwanese-American electrical engineer who had been the director of CoreWare at LSI Logic and a microprocessor designer at AMD, together with Chris Malachowsky and Curtis Priem, both former engineers of Sun Microsystems. The company initially focused on developing graphics chips for the PC gaming market, where it has grown to become a major force in the industry.
"""

def chunk_text(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
    """Split text into chunks of approximately chunk_size characters."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end near chunk boundary
            for boundary in ['. ', '.\n', '? ', '! ']:
                last_boundary = text.rfind(boundary, start + chunk_size // 2, end + 100)
                if last_boundary != -1:
                    end = last_boundary + len(boundary)
                    break
        chunks.append(text[start:end].strip())
        start = end - overlap if overlap else end

    return [c for c in chunks if c]  # Remove empty chunks


# Entity extraction prompt
ENTITY_PROMPT = """Extract all named entities from the following text. Return ONLY a valid JSON array.

Each entity should have:
- "name": The entity name as it appears in the text
- "type": One of: PERSON, ORGANIZATION, LOCATION, PRODUCT, EVENT, CONCEPT, TECHNOLOGY
- "description": Brief description (1 sentence)

Text:
{text}

Return ONLY a JSON array like:
[
  {{"name": "Example", "type": "PERSON", "description": "A person mentioned"}}
]

JSON Output:"""

# Relationship extraction prompt
RELATION_PROMPT = """Extract relationships between entities from the text. Return ONLY a valid JSON array.

Each relationship should have:
- "source": Source entity name
- "target": Target entity name
- "type": Relationship type (e.g., LOCATED_IN, WORKS_FOR, PART_OF, FOUNDED_BY, CREATED)
- "description": Brief description

Text:
{text}

Entities found: {entities}

Return ONLY a JSON array like:
[
  {{"source": "Entity1", "target": "Entity2", "type": "WORKS_FOR", "description": "Entity1 works for Entity2"}}
]

JSON Output:"""


def parse_json_array(text: str) -> list | None:
    """Try to extract a JSON array from text."""
    import re
    text = text.strip()

    # Direct parse
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except:
        pass

    # Find JSON array
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return data
        except:
            pass

    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return data
        except:
            pass

    return None


def extract_from_chunk(model: str, chunk: str, chunk_id: int, timeout: int = 180) -> dict:
    """Extract entities and relationships from a single chunk."""
    result = {
        "chunk_id": chunk_id,
        "chunk_length": len(chunk),
        "entities": [],
        "relations": [],
        "entity_time": 0,
        "relation_time": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "error": None
    }

    # Entity extraction
    try:
        entity_start = time.time()
        prompt = ENTITY_PROMPT.format(text=chunk)
        result["tokens_in"] = len(prompt) // 4  # Rough estimate

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 4096}
            },
            timeout=timeout
        )

        if response.status_code != 200:
            result["error"] = f"HTTP {response.status_code}"
            return result

        data = response.json()
        raw_response = data.get("response", "")
        result["tokens_out"] = data.get("eval_count", 0)
        result["entity_time"] = time.time() - entity_start

        entities = parse_json_array(raw_response)
        if entities:
            result["entities"] = entities
    except Exception as e:
        result["error"] = str(e)
        return result

    # Relationship extraction
    try:
        rel_start = time.time()
        entity_names = [e.get("name", "") for e in (entities or [])]
        prompt = RELATION_PROMPT.format(text=chunk, entities=", ".join(entity_names))

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 4096}
            },
            timeout=timeout
        )

        if response.status_code == 200:
            data = response.json()
            raw_response = data.get("response", "")
            result["tokens_out"] += data.get("eval_count", 0)
            result["relation_time"] = time.time() - rel_start

            relations = parse_json_array(raw_response)
            if relations:
                result["relations"] = relations
    except:
        pass

    return result


def benchmark_chunk_size(model: str, text: str, chunk_size: int) -> dict:
    """Run benchmark for a specific chunk size."""
    chunks = chunk_text(text, chunk_size)

    print(f"\n  Chunk size {chunk_size}: {len(text)} chars -> {len(chunks)} chunks")

    all_entities = []
    all_relations = []
    total_time = 0
    total_tokens_in = 0
    total_tokens_out = 0
    chunk_results = []

    for i, chunk in enumerate(chunks):
        result = extract_from_chunk(model, chunk, i)
        chunk_results.append(result)

        all_entities.extend(result["entities"])
        all_relations.extend(result["relations"])
        total_time += result["entity_time"] + result["relation_time"]
        total_tokens_in += result["tokens_in"]
        total_tokens_out += result["tokens_out"]

        print(f"    Chunk {i+1}/{len(chunks)}: {len(result['entities'])} entities, "
              f"{len(result['relations'])} relations, "
              f"{result['entity_time'] + result['relation_time']:.1f}s")

    # Deduplicate entities by name
    unique_entities = {}
    for e in all_entities:
        name = e.get("name", "").lower()
        if name and name not in unique_entities:
            unique_entities[name] = e

    return {
        "chunk_size": chunk_size,
        "num_chunks": len(chunks),
        "total_entities": len(all_entities),
        "unique_entities": len(unique_entities),
        "total_relations": len(all_relations),
        "total_time": total_time,
        "tokens_in": total_tokens_in,
        "tokens_out": total_tokens_out,
        "avg_time_per_chunk": total_time / len(chunks) if chunks else 0,
        "entities_per_1k_chars": len(unique_entities) / (len(text) / 1000),
        "chunk_results": chunk_results
    }


def main():
    parser = argparse.ArgumentParser(description="Valid Chunk-Size Benchmark")
    parser.add_argument("--model", default="gemma3:4b", help="Model to benchmark")
    parser.add_argument("--chunk-sizes", default="500,1000,1500,2000,2500,3000,3500,4000,10000",
                       help="Comma-separated chunk sizes")
    args = parser.parse_args()

    chunk_sizes = [int(x) for x in args.chunk_sizes.split(",")]
    text = LARGE_SAMPLE_TEXT.strip()

    print("=" * 70)
    print("VALID CHUNK-SIZE BENCHMARK")
    print("=" * 70)
    print(f"Model: {args.model}")
    print(f"Text length: {len(text)} characters")
    print(f"Chunk sizes: {chunk_sizes}")
    print("=" * 70)

    results = []

    for chunk_size in chunk_sizes:
        result = benchmark_chunk_size(args.model, text, chunk_size)
        results.append(result)

    # Summary
    print("\n" + "=" * 90)
    print("BENCHMARK SUMMARY")
    print("=" * 90)
    print(f"\n{'Chunk Size':<12} {'Chunks':<8} {'Entities':<10} {'Unique':<8} {'Relations':<10} "
          f"{'Time (s)':<10} {'Tok In':<10} {'Tok Out':<10}")
    print("-" * 90)

    for r in results:
        print(f"{r['chunk_size']:<12} {r['num_chunks']:<8} {r['total_entities']:<10} "
              f"{r['unique_entities']:<8} {r['total_relations']:<10} {r['total_time']:<10.1f} "
              f"{r['tokens_in']:<10} {r['tokens_out']:<10}")

    print("-" * 90)

    # Save results
    output_file = f"reports/benchmark_valid_chunking_{args.model.replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "model": args.model,
            "text_length": len(text),
            "chunk_sizes": chunk_sizes,
            "results": results
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
