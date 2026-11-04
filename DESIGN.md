---
name: Extracteur CNI
description: A local recto-verso wizard in paper and forest green.
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
typography:
  display:
    fontFamily: 'Georgia, "Times New Roman", serif'
    fontSize: "clamp(32px, 4vw, 48px)"
    fontWeight: 400
    lineHeight: 1.15
    letterSpacing: "-.035em"
  body:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "16px"
  title:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "23px"
    fontWeight: 650
    lineHeight: 1.3
  label:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "13px"
    fontWeight: 650
rounded:
  panel: "12px"
  upload: "8px"
  control: "7px"
  photo: "6px"
spacing:
  compact: "8px"
  small: "12px"
  medium: "16px"
  mobile: "20px"
  section: "24px"
  panel: "30px"
  desktop: "40px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.white}"
    rounded: "{rounded.control}"
    padding: "10px 17px"
    height: "46px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-secondary:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 17px"
  panel:
    backgroundColor: "{colors.white}"
    rounded: "{rounded.panel}"
    padding: "30px"
  upload:
    backgroundColor: "{colors.upload-surface}"
    textColor: "{colors.accent}"
    rounded: "{rounded.upload}"
    height: "315px"
  retained-field:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
    height: "46px"
  notice:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.accent}"
    rounded: "{rounded.control}"
    padding: "13px 16px"
---

# Design System: Extracteur CNI

## Overview

**Creative North Star: "Paper and forest-green workbench"** — the existing visual identity now supports a sequential wizard. Paper, white panels, a serif introduction and system controls remain the incumbent language.

The heading “Votre carte, étape par étape.” introduces Recto, Verso and Résultats. One panel is visible at a time, including a dedicated reading state. Direct French instructions guide photo confirmation and review of seven editable values.

**Key characteristics:** single active step, restrained borders, local fonts, explicit coverage limits.

## Colors

### Primary

Forest green (`accent`) identifies progression, primary actions and focus. `accent-hover` deepens hover; `soft` supports upload hover and preparation notices. `error` marks failures and field warnings.

### Neutral

`paper` surrounds white panels. `ink` carries text, `muted` explains state and limits, and `line` separates steps/actions. The empty upload target retains `upload-surface` and a dashed `upload-line` border.

## Typography

Georgia supplies the main heading and bracketed brand mark. System sans-serif serves all instructions, navigation and fields without external font requests. Panel titles use the title token, reducing to 21px on mobile. Field labels use the label token; notes use 12px with line height 1.5. Explanatory paragraphs use line height 1.6 and a maximum 70ch where applied.

## Layout

The header is centered within 1120px; main content within 920px, with desktop horizontal padding from `desktop`. A three-part progress row precedes one white panel. The source/results split layout is replaced by Recto → Verso → Résultats. The panel uses `panel` padding, a contained photo target, wrapping photo tools and a divided navigation row; “Suivant” aligns right with minimum width 140px.

Results use a two-column field grid (22px vertical and 20px horizontal gaps). An optional photo-review disclosure shows both faces side by side, explicitly labeling the verso as not read automatically. At widths up to 620px, main/panel padding uses `mobile`, fields and photo review stack, the upload target reduces from 315px to 235px and navigation wraps.

## Elevation & Depth

There are no shadows. White, paper, thin borders and soft notices supply depth. Focus remains a green outline (3px, offset 4px), including within the upload label. State transitions use .18s ease-out; the loading spinner uses .8s linear rotation. Reduced motion removes animation and transitions.

## Shapes

The main panel retains the broad panel radius, upload targets the upload radius, and inputs/buttons the control radius. Photos in the review disclosure use the photo radius. Numbered progress markers are circular; the active marker is green with white text.

## Components

- **Progress navigation:** three equal steps with numbered markers; `aria-current="step"` adds green text, a stronger bottom border and filled marker. Current headings receive focus during navigation.
- **Photo panel:** one PNG/JPEG face at a time. A dashed upload label accepts click/drop; automatic alignment produces a contained image preview. Compact secondary controls change the photo or flip it by 180°. There are no engine/filter/language/corner settings.
- **Navigation:** primary “Suivant” and “Nouvelle carte”, secondary back/review actions. Buttons have minimum height 46px; compact photo tools use 40px. Disabled buttons use opacity .45. Busy states disable photo/navigation actions.
- **Loading panel:** centered spinner and plain reading instructions, with busy semantics. The preparation notice allows photo collection while clearly explaining that Paddle must be prepared for reading.
- **Seven fields:** white, outlined editable inputs with minimum height 46px. Muted notes distinguish proposed, missing and manually edited values; uncertain-field notes use error color. No artificial accuracy percentage appears.
- **Results:** copy/TXT/JSON are limited to seven fields. A native photo disclosure and support-scope disclosure expose coverage honestly; verso capture is never described as verso OCR. Unchanged-photo review preserves edits and reuses the result without OCR. Photo changes invalidate it; a new recto also clears the old verso.

## Do's and Don'ts

- **Do** show one wizard panel and one active progress step at a time.
- **Do** preserve keyboard focus, clear busy/disabled states and explicit preparation errors.
- **Do** keep photo review, field correction and the seven-field exports easy to reach.
- **Do** state that the profile is provisional and the verso is captured without automatic reading.
- **Don't** reintroduce technical settings, free-form OCR output or zone-append controls into this wizard.
- **Don't** imply automatic card classification, identity verification, trained CNI weights or validated real Paddle accuracy.
- **Don't** introduce external fonts or decorative shadows.

Source: [stylesheet](app/static/style.css), [template](app/templates/index.html) and [wizard behavior](app/static/app.js). Product scope: [PRODUCT.md](PRODUCT.md).
