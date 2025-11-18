/**
 * Entity Extraction Utilities
 * Sprint 29 Feature 29.2: Extract entities from query sources
 */

import type { Source } from '../types/chat';

/**
 * Extract unique entity names from source documents
 *
 * Strategy:
 * 1. Check source.entities array (if available from backend)
 * 2. Extract capitalized words (simple heuristic for named entities)
 * 3. Filter out common words and short strings
 * 4. Return unique entity names
 *
 * @param sources Array of source documents from query results
 * @returns Array of unique entity names
 */
export function extractEntitiesFromSources(sources: Source[]): string[] {
  const entitySet = new Set<string>();

  // Common words to exclude from entity extraction
  const stopWords = new Set([
    'THE', 'AND', 'OR', 'BUT', 'IN', 'ON', 'AT', 'TO', 'FOR',
    'OF', 'WITH', 'BY', 'FROM', 'AS', 'IS', 'WAS', 'ARE', 'WERE',
    'BEEN', 'BE', 'HAVE', 'HAS', 'HAD', 'DO', 'DOES', 'DID',
    'WILL', 'WOULD', 'SHOULD', 'COULD', 'MAY', 'MIGHT', 'CAN',
    'THIS', 'THAT', 'THESE', 'THOSE', 'IT', 'ITS', 'THEIR',
    'THERE', 'WHERE', 'WHEN', 'WHO', 'WHAT', 'WHY', 'HOW'
  ]);

  sources.forEach((source) => {
    // Strategy 1: Use entities from backend if available
    if (source.entities && Array.isArray(source.entities)) {
      source.entities.forEach((entity) => {
        // Entity is { name: string; type?: string }
        if (entity && entity.name) {
          const trimmed = entity.name.trim();
          if (trimmed.length > 2) {
            entitySet.add(trimmed);
          }
        }
      });
    }

    // Strategy 2: Extract capitalized words from text (heuristic)
    if (source.text) {
      // Match sequences of capitalized words (e.g., "Artificial Intelligence", "John Doe")
      const capitalizedPattern = /\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b/g;
      const matches = source.text.match(capitalizedPattern);

      if (matches) {
        matches.forEach((match) => {
          const normalized = match.trim();
          // Filter: length > 2, not a stop word, not all caps
          if (
            normalized.length > 2 &&
            !stopWords.has(normalized.toUpperCase()) &&
            normalized !== normalized.toUpperCase()
          ) {
            entitySet.add(normalized);
          }
        });
      }
    }

    // Strategy 3: Extract from title if available
    if (source.title) {
      const titlePattern = /\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b/g;
      const titleMatches = source.title.match(titlePattern);

      if (titleMatches) {
        titleMatches.forEach((match) => {
          const normalized = match.trim();
          if (
            normalized.length > 2 &&
            !stopWords.has(normalized.toUpperCase()) &&
            normalized !== normalized.toUpperCase()
          ) {
            entitySet.add(normalized);
          }
        });
      }
    }
  });

  // Convert to array and limit to top 20 entities (to avoid overwhelming the graph)
  const entities = Array.from(entitySet).slice(0, 20);

  return entities;
}

/**
 * Extract entities with type information (if available)
 *
 * @param sources Array of source documents
 * @returns Array of entities with name and type
 */
export function extractTypedEntities(
  sources: Source[]
): Array<{ name: string; type?: string }> {
  const entityMap = new Map<string, string | undefined>();

  sources.forEach((source) => {
    if (source.entities && Array.isArray(source.entities)) {
      source.entities.forEach((entity) => {
        // Entity is { name: string; type?: string }
        if (entity && entity.name) {
          const trimmed = entity.name.trim();
          if (trimmed.length > 0) {
            entityMap.set(trimmed, entity.type);
          }
        }
      });
    }
  });

  return Array.from(entityMap.entries())
    .map(([name, type]) => ({ name, type }))
    .slice(0, 20); // Limit to 20 entities
}
