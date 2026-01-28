---
name: data_viz
version: 1.0.0
description: Data visualization and chart generation for visual data analysis
author: AegisRAG Team
triggers:
  - visualize
  - chart
  - plot
  - graph data
  - diagram
  - histogram
dependencies:
  - matplotlib
  - seaborn
permissions:
  - execute_code
  - file_write
  - invoke_llm
resources:
  prompts: prompts/
---

# Data Visualization Skill

## Overview

The Data Visualization Skill generates charts, plots, and diagrams from numeric data and retrieved documents. It produces visual representations to aid in data understanding and presentation.

## Capabilities

- **Chart Types**: Bar, line, scatter, pie, histogram, box plot, heatmap
- **Auto-Detection**: Automatically selects appropriate chart type based on data structure
- **Styling**: Consistent AegisRAG visual theme with customizable colors
- **Multi-Series**: Support for multi-variable comparison plots
- **Export Formats**: PNG, SVG, PDF output
- **Bilingual Labels**: DE/EN axis labels and titles ("Diagramm", "Achse")

## When to Activate

This skill is triggered when queries contain:
- Visualization keywords: "chart", "plot", "visualize", "graph", "diagram"
- Visual analysis: "show me", "display", "illustrate", "Diagramm erstellen"
- Comparison visuals: "compare visually", "side by side", "trend chart"

## Integration

- **Statistics Skill**: Receives computed data for visualization
- **Safe Execution**: Sandboxed matplotlib/seaborn rendering
- **File Output**: Saves generated charts to configurable output directory

## Limitations

- No interactive charts (static image output only)
- Maximum 10 series per chart for readability
- Requires numeric data input (no automatic OCR of chart images)
