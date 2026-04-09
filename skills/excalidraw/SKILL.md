---
name: excalidraw
description: "Generate Excalidraw diagrams from JSON. Pipeline, mindmap, flowchart. Use when: draw diagram, visualize, architecture schema, mindmap."
user-invocable: true
argument-hint: "[diagram-type] [description]"
---

# Excalidraw Diagram Generator

Generates valid `.excalidraw` JSON files from simple JSON input.

## Diagram Types

| Type | Layout | Use Case |
|------|--------|----------|
| `pipeline` | Vertical stages with blocks | Workflows, CI/CD, data pipelines |
| `mindmap` | Radial from center | Brainstorming, topic exploration |
| `flowchart` | Custom node positions | Architecture, decision trees |

## Usage

```bash
# From JSON file
python3 $CLAUDE_SKILL_DIR/scripts/excalidraw_gen.py --input schema.json --output diagram.excalidraw

# From stdin
echo '{"type":"mindmap","center":"AI Agents","nodes":["Memory","Skills","Tools"]}' | \
    python3 $CLAUDE_SKILL_DIR/scripts/excalidraw_gen.py --output diagram.excalidraw
```

## Input Format

### Pipeline
```json
{
  "type": "pipeline",
  "title": "Data Pipeline",
  "stages": [
    {"name": "Input", "type": "input", "blocks": ["API", "Webhook"]},
    {"name": "Process", "type": "analysis", "blocks": ["Transform", "Validate"]},
    {"name": "Output", "type": "final", "blocks": ["Database", "Cache"]}
  ]
}
```

### Mindmap
```json
{
  "type": "mindmap",
  "center": "Architecture",
  "nodes": ["Frontend", "Backend", "Database", "Cache", "CDN"]
}
```

### Flowchart
```json
{
  "type": "flowchart",
  "nodes": [
    {"id": "a", "text": "Start", "x": 0, "y": 0},
    {"id": "b", "text": "Process", "x": 0, "y": 200},
    {"id": "c", "text": "End", "x": 0, "y": 400}
  ],
  "edges": [
    {"from": "a", "to": "b"},
    {"from": "b", "to": "c"}
  ]
}
```

## Color Scheme

| Type | Color |
|------|-------|
| research | Blue |
| analysis | Purple |
| review | Orange |
| final | Green |
| factcheck | Green |
| input | Red |
| default | Grey |

## Setup

Requires Python 3 (standard library only, no pip install needed).

## Output

Opens in [excalidraw.com](https://excalidraw.com) -- drag and drop the `.excalidraw` file.
