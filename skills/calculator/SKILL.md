---
name: calculator
version: 1.0.0
description: Mathematical computation and data analysis for numeric queries and calculations
author: AegisRAG Team
triggers:
  - calculate
  - compute
  - math
  - formula
  - percentage
  - convert
dependencies: []
permissions:
  - execute_code
resources:
  prompts: prompts/
---

# Calculator Skill

## Overview

The Calculator Skill provides mathematical computation capabilities for queries requiring numeric calculations, unit conversions, statistical analysis, or formula evaluation. It supports both simple arithmetic and complex expressions via safe Python evaluation.

## Capabilities

- **Basic Arithmetic**: Addition, subtraction, multiplication, division, exponentiation
- **Unit Conversion**: Length, weight, temperature, currency (with cached exchange rates)
- **Statistical Analysis**: Mean, median, mode, standard deviation, percentiles
- **Formula Evaluation**: Safe evaluation of mathematical expressions
- **Percentage Calculations**: Percentage of, percentage change, percentage difference
- **Bilingual Support**: Handle DE/EN calculation queries ("berechne", "rechne")

## When to Activate

This skill is triggered when queries contain:
- Calculation keywords: "calculate", "compute", "berechne", "rechne"
- Mathematical operators or numbers in query context
- Unit conversion requests
- Statistical analysis requests

## Integration

- **Safe Evaluation**: Uses sandboxed Python evaluation (no arbitrary code execution)
- **LLM Parsing**: Extracts mathematical intent from natural language queries
- **Result Formatting**: Presents results with appropriate precision and units

## Safety

- No arbitrary code execution — only mathematical expressions
- Input validation and sanitization
- Maximum expression complexity limits
- Timeout for long-running calculations
