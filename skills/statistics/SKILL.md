---
name: statistics
version: 1.0.0
description: Statistical analysis and data processing for numeric datasets
author: AegisRAG Team
triggers:
  - statistics
  - analyze data
  - mean
  - median
  - standard deviation
  - correlation
  - distribution
dependencies:
  - numpy
  - pandas
permissions:
  - execute_code
  - invoke_llm
resources:
  prompts: prompts/
---

# Statistics Skill

## Overview

The Statistics Skill provides statistical analysis capabilities for queries involving data processing, descriptive statistics, hypothesis testing, and trend analysis. It operates on numeric data extracted from documents or provided directly by the user.

## Capabilities

- **Descriptive Statistics**: Mean, median, mode, standard deviation, quartiles, percentiles
- **Distribution Analysis**: Normality tests, skewness, kurtosis, histograms
- **Correlation Analysis**: Pearson, Spearman, and Kendall correlation coefficients
- **Trend Detection**: Time series trends, moving averages, growth rates
- **Data Summarization**: Statistical summaries of tabular data from retrieved documents
- **Bilingual Support**: Handle DE/EN queries ("Durchschnitt", "Standardabweichung")

## When to Activate

This skill is triggered when queries contain:
- Statistical terms: "average", "mean", "median", "deviation", "correlation"
- Data analysis intent: "analyze data", "trend", "distribution", "Statistik"
- Numeric aggregation: "how many", "percentage", "rate", "count"

## Integration

- **Calculator Skill**: Delegates basic arithmetic to calculator skill
- **Data Extraction**: Parses tables and numeric data from retrieved documents
- **Safe Evaluation**: Uses sandboxed NumPy/Pandas for computation

## Limitations

- Maximum dataset size: 10,000 rows (memory constraints)
- No interactive plotting (use data_viz skill for visualization)
- Requires structured numeric input for advanced statistical tests
