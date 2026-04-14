#!/usr/bin/env python3
import argparse
import json
import math
import random
import sys
import time
from typing import Dict, List, Tuple

COLORS = {
    "research": {"background": "#e3f2fd", "stroke": "#1565c0"},
    "analysis": {"background": "#ede7f6", "stroke": "#6a1b9a"},
    "review": {"background": "#fff3e0", "stroke": "#e65100"},
    "final": {"background": "#e8f5e9", "stroke": "#2e7d32"},
    "factcheck": {"background": "#e8f5e9", "stroke": "#2e7d32"},
    "input": {"background": "#ffebee", "stroke": "#d32f2f"},
    "default": {"background": "#f8f9fa", "stroke": "#495057"},
}

ARROW_COLOR = "#495057"
BG_COLOR = "#ffffff"

FONT_BLOCK = 18
FONT_STAGE = 20
FONT_TITLE = 28
FONT_FAMILY = 1
STROKE_WIDTH = 2
ROUGHNESS = 0


def rand_seed() -> int:
    return random.randint(1, 2_000_000_000)


def ex_id(prefix="el"):
    return f"{prefix}_{int(time.time()*1000)}_{random.randint(1000,9999)}"


def text_size(text: str, base_w=220, line_h=26, pad=24) -> Tuple[int, int]:
    lines = (text or "").split("\n")
    max_len = max((len(line) for line in lines), default=8)
    width = max(base_w, min(520, int(max_len * 11 + pad * 2)))
    height = max(64, int(len(lines) * line_h + pad))
    return width, height


def mk_rect(x, y, w, h, color):
    return {
        "id": ex_id("rect"),
        "type": "rectangle",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "angle": 0,
        "strokeColor": color["stroke"],
        "backgroundColor": color["background"],
        "fillStyle": "solid",
        "strokeWidth": STROKE_WIDTH,
        "strokeStyle": "solid",
        "roughness": ROUGHNESS,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": {"type": 3},
        "seed": rand_seed(),
        "version": 1,
        "versionNonce": rand_seed(),
        "isDeleted": False,
        "boundElements": [],
        "updated": int(time.time()*1000),
        "link": None,
        "locked": False,
    }


def mk_text(x, y, text, font_size, color="#1f2937", w=None, h=None):
    if w is None or h is None:
        w, h = text_size(text, base_w=120)
    return {
        "id": ex_id("txt"),
        "type": "text",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "angle": 0,
        "strokeColor": color,
        "backgroundColor": "transparent",
        "fillStyle": "hachure",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": None,
        "seed": rand_seed(),
        "version": 1,
        "versionNonce": rand_seed(),
        "isDeleted": False,
        "boundElements": [],
        "updated": int(time.time()*1000),
        "link": None,
        "locked": False,
        "text": text,
        "fontSize": font_size,
        "fontFamily": FONT_FAMILY,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": None,
        "originalText": text,
        "lineHeight": 1.25,
    }


def mk_arrow(x1, y1, x2, y2):
    return {
        "id": ex_id("arr"),
        "type": "arrow",
        "x": x1,
        "y": y1,
        "width": x2 - x1,
        "height": y2 - y1,
        "angle": 0,
        "strokeColor": ARROW_COLOR,
        "backgroundColor": "transparent",
        "fillStyle": "hachure",
        "strokeWidth": STROKE_WIDTH,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": None,
        "seed": rand_seed(),
        "version": 1,
        "versionNonce": rand_seed(),
        "isDeleted": False,
        "boundElements": [],
        "updated": int(time.time()*1000),
        "link": None,
        "locked": False,
        "points": [[0, 0], [x2 - x1, y2 - y1]],
        "lastCommittedPoint": None,
        "startBinding": None,
        "endBinding": None,
        "startArrowhead": None,
        "endArrowhead": "arrow",
    }


def color_of(name: str):
    return COLORS.get((name or "").lower(), COLORS["default"])


def build_pipeline(schema: Dict) -> List[Dict]:
    els = []
    title = schema.get("title", "Pipeline")
    stages = schema.get("stages", [])

    title_w, title_h = text_size(title, base_w=400, line_h=38, pad=20)
    els.append(mk_text(-title_w // 2, -260, title, FONT_TITLE, w=title_w, h=title_h))

    y = -120
    stage_gap = 190

    prev_center = None

    for s in stages:
        label = s.get("label", "Этап")
        subtitle = s.get("subtitle")
        blocks = s.get("blocks", [])
        stage_color = color_of(s.get("color", "default"))

        label_w, label_h = text_size(label, base_w=360, line_h=30, pad=24)
        label_rect = mk_rect(-label_w // 2, y, label_w, 70, stage_color)
        label_txt = mk_text(-label_w // 2 + 12, y + 16, label, FONT_STAGE, w=label_w - 24, h=36)
        els.extend([label_rect, label_txt])

        if subtitle:
            sub_w, sub_h = text_size(subtitle, base_w=220, line_h=24, pad=10)
            els.append(mk_text(-sub_w // 2, y + 78, subtitle, 16, color="#6b7280", w=sub_w, h=sub_h))

        block_y = y + 95
        n = max(1, len(blocks))
        gap = 40
        widths = []
        for b in blocks:
            w, _ = text_size(b.get("text", ""), base_w=220)
            widths.append(w)
        total_w = sum(widths) + gap * (n - 1)
        start_x = -total_w // 2

        for i, b in enumerate(blocks):
            btxt = b.get("text", "")
            bw, bh = text_size(btxt)
            bx = start_x + sum(widths[:i]) + i * gap
            bcolor = color_of(b.get("color", s.get("color", "default")))
            rect = mk_rect(bx, block_y, bw, bh, bcolor)
            txt = mk_text(bx + 12, block_y + 12, btxt, FONT_BLOCK, w=bw - 24, h=bh - 24)
            els.extend([rect, txt])
            els.append(mk_arrow(0, y + 70, bx + bw // 2, block_y))

        stage_center = (0, y + 35)
        if prev_center:
            els.append(mk_arrow(prev_center[0], prev_center[1] + 90, stage_center[0], stage_center[1]))
        prev_center = stage_center
        y += stage_gap + 40

    return els


def build_mindmap(schema: Dict) -> List[Dict]:
    els = []
    title = schema.get("title", "Mind Map")
    nodes = schema.get("nodes", [])

    cw, ch = text_size(title, base_w=280)
    c_rect = mk_rect(-cw // 2, -ch // 2, cw, ch, color_of("analysis"))
    c_txt = mk_text(-cw // 2 + 12, -ch // 2 + 12, title, FONT_STAGE, w=cw - 24, h=ch - 24)
    els.extend([c_rect, c_txt])

    radius = 320
    for i, n in enumerate(nodes):
        angle = (2 * math.pi * i) / max(1, len(nodes))
        nx = int(math.cos(angle) * radius)
        ny = int(math.sin(angle) * radius)
        txt = n.get("text", n.get("label", "Node"))
        col = color_of(n.get("color", "research"))
        w, h = text_size(txt, base_w=180)
        r = mk_rect(nx - w // 2, ny - h // 2, w, h, col)
        t = mk_text(nx - w // 2 + 12, ny - h // 2 + 12, txt, FONT_BLOCK, w=w - 24, h=h - 24)
        els.extend([r, t, mk_arrow(0, 0, nx, ny)])

    return els


def build_flowchart(schema: Dict) -> List[Dict]:
    els = []
    nodes = schema.get("nodes", [])
    edges = schema.get("edges", [])
    title = schema.get("title")

    if title:
        tw, th = text_size(title, base_w=420, line_h=38)
        els.append(mk_text(-tw // 2, -280, title, FONT_TITLE, w=tw, h=th))

    id_to_center = {}
    for n in nodes:
        nid = n.get("id", ex_id("n"))
        x = int(n.get("x", 0))
        y = int(n.get("y", 0))
        txt = n.get("text", n.get("label", nid))
        col = color_of(n.get("color", "default"))
        w, h = text_size(txt)
        r = mk_rect(x, y, w, h, col)
        t = mk_text(x + 12, y + 12, txt, FONT_BLOCK, w=w - 24, h=h - 24)
        els.extend([r, t])
        id_to_center[nid] = (x + w // 2, y + h // 2)

    for e in edges:
        s = id_to_center.get(e.get("from"))
        t = id_to_center.get(e.get("to"))
        if s and t:
            els.append(mk_arrow(s[0], s[1], t[0], t[1]))

    return els


def build(schema: Dict) -> Dict:
    kind = (schema.get("type") or "pipeline").lower()
    if kind == "pipeline":
        elements = build_pipeline(schema)
    elif kind in ("mindmap", "mind_map", "mind-map"):
        elements = build_mindmap(schema)
    elif kind == "flowchart":
        elements = build_flowchart(schema)
    else:
        raise ValueError(f"Unsupported type: {kind}")

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://openclaw.local/skills/excalidraw",
        "elements": elements,
        "appState": {
            "gridSize": None,
            "viewBackgroundColor": BG_COLOR,
        },
        "files": {},
    }


def load_input(path: str = None) -> Dict:
    if path:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("No input JSON provided via stdin or --input")
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(description="Generate Excalidraw .excalidraw files from simple JSON schema")
    parser.add_argument("--input", "-i", help="Input schema JSON file")
    parser.add_argument("--output", "-o", help="Output .excalidraw file")
    args = parser.parse_args()

    schema = load_input(args.input)
    doc = build(schema)
    out = json.dumps(doc, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
            f.write("\n")
    else:
        print(out)


if __name__ == "__main__":
    main()
