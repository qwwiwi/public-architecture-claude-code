---
name: datawrapper
description: Create charts, tables, and data visualizations via Datawrapper API
---

# Datawrapper -- Charts and Tables

Create interactive charts, tables, and maps using the Datawrapper API.

## Usage

When the user asks to create a chart, table, or data visualization:

1. Get API token from `~/.claude-lab/shared/secrets/datawrapper.env`
2. Create chart via Datawrapper API: `POST https://api.datawrapper.de/v3/charts`
3. Upload data: `PUT https://api.datawrapper.de/v3/charts/{id}/data`
4. Publish: `POST https://api.datawrapper.de/v3/charts/{id}/publish`

## API Key

- Free tier: datawrapper.de (sign up, create API token)
- Store token in: `~/.claude-lab/shared/secrets/datawrapper.env`

## Chart Types

- `d3-bars` -- bar chart
- `d3-lines` -- line chart
- `d3-pie` -- pie chart
- `d3-scatter` -- scatter plot
- `tables` -- data table
- `locator-map` -- map

## Example

```bash
DW_TOKEN=$(cat ~/.claude-lab/shared/secrets/datawrapper.env)
curl -X POST "https://api.datawrapper.de/v3/charts" \
  -H "Authorization: Bearer $DW_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"My Chart","type":"d3-bars"}'
```
