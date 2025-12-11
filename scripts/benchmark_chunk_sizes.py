#!/usr/bin/env python3
"""
Benchmark different chunk sizes for UNIFIED extraction.
Tests chunk sizes from 500 to 4000 chars in 500-char steps.
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.components.graph_rag.extraction_benchmark import ExtractionBenchmark, ExtractionStrategy


def chunk_text_by_size(text: str, max_chars: int) -> list[str]:
    """Split text into chunks of approximately max_chars size."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    paragraphs = text.split('\n\n')
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_chars:
            current_chunk += ("\n\n" if current_chunk else "") + para
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # If paragraph itself is too long, split by sentences
            if len(para) > max_chars:
                sentences = para.replace('. ', '.\n').split('\n')
                current_chunk = ""
                for sent in sentences:
                    if len(current_chunk) + len(sent) + 1 <= max_chars:
                        current_chunk += (" " if current_chunk else "") + sent
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sent
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


async def run_chunk_size_benchmark(sample_text: str, sample_id: str, chunk_sizes: list[int]) -> dict:
    """Run benchmark for different chunk sizes on same sample."""
    benchmark = ExtractionBenchmark(max_tokens=8192)
    results = {
        "sample_id": sample_id,
        "original_text_length": len(sample_text),
        "chunk_size_results": []
    }

    for chunk_size in chunk_sizes:
        print(f"\n{'='*60}")
        print(f"Testing chunk size: {chunk_size} chars")
        print(f"{'='*60}")

        chunks = chunk_text_by_size(sample_text, chunk_size)
        print(f"  Split into {len(chunks)} chunks")

        chunk_results = {
            "chunk_size": chunk_size,
            "num_chunks": len(chunks),
            "chunks": []
        }

        total_entities = 0
        total_rels = 0
        total_time_ms = 0
        total_output_tokens = 0

        for i, chunk in enumerate(chunks):
            print(f"\n  Chunk {i+1}/{len(chunks)}: {len(chunk)} chars")

            start = time.time()
            chunk_id = f"{sample_id}_chunk{i}"
            result = await benchmark.extract(chunk, chunk_id=chunk_id, strategy=ExtractionStrategy.UNIFIED)
            elapsed_ms = (time.time() - start) * 1000

            # ExtractionResult has entities, typed_relationships, semantic_relations, metrics
            entities = len(result.entities) if hasattr(result, 'entities') else 0
            rels = len(result.typed_relationships) if hasattr(result, 'typed_relationships') else 0
            output_tokens = result.metrics.total_output_tokens if hasattr(result, 'metrics') else 0

            print(f"    → Entities: {entities}, Rels: {rels}, Time: {elapsed_ms:.0f}ms, Out tokens: {output_tokens}")

            chunk_results["chunks"].append({
                "chunk_index": i,
                "chunk_chars": len(chunk),
                "entities": entities,
                "relationships": rels,
                "time_ms": elapsed_ms,
                "output_tokens": output_tokens
            })

            total_entities += entities
            total_rels += rels
            total_time_ms += elapsed_ms
            total_output_tokens += output_tokens

        chunk_results["totals"] = {
            "total_entities": total_entities,
            "total_relationships": total_rels,
            "total_time_ms": total_time_ms,
            "total_output_tokens": total_output_tokens,
            "avg_entities_per_chunk": total_entities / len(chunks) if chunks else 0,
            "avg_time_per_chunk_ms": total_time_ms / len(chunks) if chunks else 0
        }

        print(f"\n  TOTALS for {chunk_size} chars: {total_entities} entities, {total_rels} rels, {total_time_ms/1000:.1f}s")

        results["chunk_size_results"].append(chunk_results)

    return results


async def async_main():
    parser = argparse.ArgumentParser(description="Benchmark different chunk sizes")
    parser.add_argument("--min-chunk", type=int, default=500, help="Minimum chunk size (chars)")
    parser.add_argument("--max-chunk", type=int, default=4000, help="Maximum chunk size (chars)")
    parser.add_argument("--step", type=int, default=500, help="Chunk size step (chars)")
    args = parser.parse_args()

    print("="*80)
    print("CHUNK SIZE BENCHMARK")
    print(f"Chunk sizes: {args.min_chunk} to {args.max_chunk} chars (step {args.step})")
    print("="*80)

    # Use Sample 8 text directly (Q1064 - Leaving Las Vegas) from previous test
    # This has known good extraction results - FULL TEXT ~7700 chars
    sample_text = """Leaving Las Vegas is a 1995 American drama film written and directed by Mike Figgis and based on the semi-autobiographical 1990 novel of the same name by John O'Brien. It stars Nicolas Cage as a suicidal alcoholic in Los Angeles who, having lost his family and been fired from his job, has decided to move to Las Vegas and drink himself to death. He meets a prostitute played by Elisabeth Shue and they become close.

== Plot ==
Ben Sanderson is a Hollywood screenwriter who has destroyed his career and lost his wife and son because of his alcoholism. After being fired, he receives a severance check and decides to take all his money to Las Vegas, where he plans to drink himself to death. In Las Vegas, Ben meets Sera, a prostitute who works under the control of a violent Latvian pimp named Yuri Butsov. Despite Sera's profession and Ben's alcoholism, the two begin a relationship. Ben agrees to never ask Sera to stop prostituting, and Sera agrees to never ask Ben to stop drinking.

After Yuri is killed by Russian mobsters seeking repayment for debts, Sera invites Ben to move in with her. They get along well despite Ben's constant drinking. However, Ben's condition deteriorates rapidly. One night, he destroys Sera's house while she is out; she tells him he must move out, though she still loves him. Later, Sera is gang-raped by a group of college students and is beaten badly. Her landlord evicts her from her apartment because of the incident. Sera receives a call from Ben, who is on his deathbed. Sera visits Ben, the two make love, and he dies shortly thereafter. Later, Sera explains to her therapist that she accepted Ben for who he was and loved him.

== Cast ==
Nicolas Cage as Ben Sanderson
Elisabeth Shue as Sera
Julian Sands as Yuri Butsov

== Production ==
=== Development ===
Mike Figgis based Leaving Las Vegas on a 1990 autobiographical novel by John O'Brien, who died of suicide in April 1994, shortly after finding out his novel was being used as the basis for a film. Despite basing most of his screenplay on O'Brien's novel, Figgis was also inspired by a poem O'Brien wrote, as it was included in the novel. O'Brien's family fully supported the film, and his father and sister appeared as extras in a casino scene. His ex-wife Erin O'Brien acted as consultant for the production.

=== Filming ===
The film was shot in super 16 mm instead of 35 mm film as a result of its relatively low budget. Locations used in the film include the Las Vegas Strip (the Boomtown hotel is visible from their motel room), the Hoover Dam, and St. Thomas, Nevada (scene of the couple's picnic by a tree). Nicolas Cage says that for the scene in which Ben visits a Las Vegas bank to cash his severance check, Cage made a practice of getting drunk in a Dublin pub and then having a friend videotape his actions while intoxicated to perfect his alcoholic swagger. Shue worked with prostitutes from Los Angeles to prepare for her role.

=== Music ===
Mike Figgis composed and performed the original music score for the film with the help of some friends. Sting sang the original song "Angel Eyes" for the film. The soundtrack also included songs from the likes of Don Henley, Sting, Michael McDonald, and Rickie Lee Jones.

== Release ==
Leaving Las Vegas was released on October 27, 1995, in limited release and began a wide release in the United States on February 9, 1996, 15 weeks later. During its opening weekend in wide release in the United States and Canada, Leaving Las Vegas made US$3.5 million from 760 screens; by the end of its run it made $32 million. United Artists released the film theatrically in North America, while RCV Film Distribution and Atalanta Filmes handled the European release and 21st Century Film Corporation handled the Australian release. MGM/UA, which bought the distribution rights for the film in 1995, has since been the film's main distributor. It was first released on Region 1 DVD on January 22, 2002, and the MGM Special Edition DVD was released on February 3, 2004. Both DVD releases are currently out of print.

== Reception ==
=== Critical response ===
Leaving Las Vegas received critical acclaim from critics. Review aggregator website Rotten Tomatoes gives the film a score of 89% based on 75 reviews, with an average rating of 7.8/10. The website's critics consensus states: "Powered by the Oscar-winning performances of Nicolas Cage and Elisabeth Shue, Leaving Las Vegas is a dark, unsentimental look at the effects of alcoholism." On Metacritic, another review aggregator, the film has a weighted average score of 81 out of 100 based on 23 critics, indicating "universal acclaim".

Roger Ebert, on the television show Siskel & Ebert, gave the film a 'thumbs up' and later named it among the best films of 1995; in his written review, he awarded the film 4 out of 4 stars and stated "they represent a triumph over the odds facing the filmmakers."

=== Awards and nominations ===
Nicolas Cage won the Golden Globe Award for Best Actor - Motion Picture Drama and the Academy Award for Best Actor for his role in the film; Elisabeth Shue was nominated in the same categories for Best Actress. The film was also nominated for the Academy Award for Best Adapted Screenplay, and for the Academy Award for Best Director for Figgis."""

    sample_id = "Q1064"
    print(f"\nUsing sample: {sample_id} (Leaving Las Vegas)")
    print(f"Text length: {len(sample_text)} chars")
    print(f"Preview: {sample_text[:150]}...")

    # Generate chunk sizes
    chunk_sizes = list(range(args.min_chunk, args.max_chunk + 1, args.step))
    print(f"\nChunk sizes to test: {chunk_sizes}")

    # Run benchmark
    results = await run_chunk_size_benchmark(sample_text, sample_id, chunk_sizes)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = Path(f"reports/chunk_size_benchmark_{timestamp}.json")
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*80}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*80}")

    # Print summary table
    print("\n\nSUMMARY TABLE:")
    print("-" * 100)
    print(f"{'Chunk Size':>12} | {'Chunks':>6} | {'Entities':>8} | {'Rels':>6} | {'Time (s)':>10} | {'Ent/Chunk':>10} | {'s/Chunk':>8}")
    print("-" * 100)

    for r in results["chunk_size_results"]:
        t = r["totals"]
        print(f"{r['chunk_size']:>12} | {r['num_chunks']:>6} | {t['total_entities']:>8} | {t['total_relationships']:>6} | {t['total_time_ms']/1000:>10.1f} | {t['avg_entities_per_chunk']:>10.1f} | {t['avg_time_per_chunk_ms']/1000:>8.1f}")

    print("-" * 100)


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
