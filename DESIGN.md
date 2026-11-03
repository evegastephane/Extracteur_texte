---
name: Extracteur
description: A local seven-field extraction workbench in paper and forest green.
colors:
  paper: "#f6f5f0"
  ink: "#202c28"
  muted: "#5f6862"
  line: "#d6dcd4"
  accent: "#255e48"
  soft: "#eaf0e9"
  error: "#9e2924"
  white: "#fff"
  accent-hover: "#1b4937"
  upload-surface: "#f8f9f5"
  upload-line: "#a4b4a4"
  selection-surface: "#eef1eb"
typography:
  display:
    fontFamily: 'Georgia, "Times New Roman", serif'
    fontSize: "clamp(36px, 4.2vw, 58px)"
    fontWeight: 400
    lineHeight: 1.12
    letterSpacing: "-.035em"
  body:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "16px"
  title:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "17px"
    fontWeight: 650
  label:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "13px"
    fontWeight: 600
rounded:
  workspace: "12px"
  upload: "8px"
  control: "7px"
  field: "5px"
spacing:
  compact: "8px"
  control-gap: "10px"
  small: "12px"
  mobile: "20px"
  panel: "26px"
  desktop: "40px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.white}"
    rounded: "{rounded.control}"
    padding: "10px 17px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-secondary:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  workspace:
    backgroundColor: "{colors.white}"
    rounded: "{rounded.workspace}"
  upload:
    backgroundColor: "{colors.upload-surface}"
    textColor: "{colors.accent}"
    rounded: "{rounded.upload}"
  language:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 30px 8px 12px"
  engine:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 30px 8px 12px"
    width: "100%"
  preparation-field:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    height: "40px"
  retained-field:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px"
    height: "44px"
  editor:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    padding: "0 4px"
---

# Design System: Extracteur

## Overview

**Creative North Star: "Paper and forest-green workbench"** — a description of the implemented interface, not a separately established user preference.

The quiet paper background frames a white work surface. A serif introduction gives the page character; system typography keeps the image controls and seven editable fields familiar. The image and retained fields form a single working area, with forest green identifying the recognition action and interactive cues. The main heading is “De l’image aux champs.”

**Key characteristics:** paired source/result panels, restrained borders, local fonts, direct French instructions.

## Colors

### Primary

Forest green (`accent`) identifies extraction, upload cues, the local indicator and focus. `accent-hover` deepens the primary button; `soft` marks gentle hover and drag states. `error` is reserved for status errors.

### Neutral

`paper` surrounds the white workspace. `ink` carries readable text, `muted` supports instructions and metadata, and `line` separates regions. `upload-surface` and `upload-line` distinguish the empty image target. `selection-surface` supports the oriented canvas; green outlines, translucent fill and numbered handles show the selected quadrilateral.

## Typography

The display serif appears in the main heading; the bracketed brand mark also uses Georgia. System sans-serif serves controls, prose and extracted text without external font requests. Section titles use the title token; form labels use the label token. Introductory prose is slightly larger (17px, line height 1.6, maximum 70ch); mobile reduces it to 15px. The read-only summary uses 14px text with generous line height (1.8); retained-field labels are 13px and evidence/status notes are 11px.

## Layout

The header and main area share a centered maximum width (1280px), with desktop horizontal padding from `desktop`. The workspace grid pairs source and result in a 1:1.12 ratio, separated by a border; panel padding uses `panel`.

At widths up to 760px, panels stack source first, padding uses `mobile`, the divider becomes horizontal, and the language/action row stacks. The empty upload area reduces from 285px to 235px; once preparation is enabled it is 340px, reducing to 260px up to 420px. The retained fields use a two-column grid with gaps of 18px vertically and 16px horizontally, becoming one column up to 760px. The summary has a minimum height of 180px. Result actions wrap; the footer stacks. Preparation settings use two columns, stacking up to 420px; corner-coordinate groups use two columns. Optional keyboard coordinates use a native disclosure below the image tools; the read-only filtered summary has its own disclosure beneath the seven fields.

## Elevation & Depth

There are no shadows. White, paper and softly tinted upload surfaces establish depth through tone and thin borders. Focus is a visible green outline (3px, offset 4px); the upload target uses a 3px offset.

## Shapes

Use the workspace radius for the outer shared surface, upload radius for the image target and control radius for buttons and select. The image target has a dashed border; the workspace and controls have solid thin borders. Preview images remain contained within their target.

## Components

- **Extraction button:** “Repérer les champs”, forest green with white text; minimum height 46px. Disabled controls have opacity .48 and a disallowed cursor.
- **Result buttons:** compact outlined white copy/TXT/JSON controls; minimum height 40px, 13px text, soft hover fill. Outputs are restricted to the seven retained field keys.
- **Engine selector:** a full-width native select above preparation, using existing control tokens. Tesseract is the default; PaddleOCR is labeled optional. A muted hint explains language/layout behavior or missing installation/models, without suggesting validated accuracy or readiness. The control is disabled while extraction runs.
- **Language selector:** a native select with the three implemented French/English choices. PaddleOCR disables it and the layout select because its Latin model and automatic segmentation apply. Disabled selects use opacity .6 and a disallowed cursor; geometry and filter controls remain shared.
- **Upload target:** an accessible file label with centered instructions, hover/drag tint and image preview. Keyboard focus outlines the target.
- **Image preparation:** native selects and green-accent checkboxes extend the existing control language. Compact rotation/reset buttons precede the orientation canvas. Four numbered green handles are draggable; percentage X/Y fields offer keyboard editing in clockwise order. Rotation resets the selection. The canvas previews geometry, not tonal filters.
- **Preparation fields:** thin outlined inputs use the field radius; coordinate fields have minimum height 40px. Photo/Original/adaptive threshold, optional ±12° deskew and auto/block/sparse/line layout remain explicitly selectable.
- **Retained fields:** exactly seven labeled editable inputs with control radius, white fill, thin border and minimum height 44px. Muted notes beneath each input explain proposed/missing/ambiguous values and field-specific evidence; manual edits are identified. Never present an invented confidence percentage.
- **Filtered summary:** a borderless, vertically resizable read-only textarea in a native disclosure. It reflects only filled retained fields; users edit the fields above. Successful extraction replaces all seven propositions; failure preserves corrections. Free-form zone append controls are absent.
- **Status:** a reserved message area below the workspace, with a spinning busy indicator and error color when needed. Status updates are announced politely.

Button and upload color transitions use .18s ease-out; the busy indicator rotates over .8s. Reduced-motion preference removes transitions and animation.

## Do's and Don'ts

- **Do** keep extraction visually primary and copy/export secondary.
- **Do** preserve visible keyboard focus, clear disabled states and readable French instructions.
- **Do** keep source and result adjacent on desktop and sequential on mobile.
- **Do** preserve keyboard coordinate editing, field-specific evidence and corrections after failed reruns.
- **Do** keep the result surface and normal exports restricted to the seven fields; raw OCR belongs only to the explicit technical compatibility mode.
- **Do** keep optional-engine availability and errors explicit, preserving prior text on failure.
- **Don't** introduce external font requests or decorative shadows into this local, flat interface.
- **Don't** hide editing, copy or export behind an extra screen.

Source of truth: [app/static/style.css](app/static/style.css) and [app/templates/index.html](app/templates/index.html). Scope and limitations: [PRODUCT.md](PRODUCT.md).
