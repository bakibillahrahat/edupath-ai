# EduPath AI — Design System v1.0

## Overview

EduPath AI uses a clean, minimal design system inspired by **Notion** + **Modern AI SaaS** + **Premium Education**. The system prioritizes clarity, hierarchy, and trust while maintaining visual polish.

**Key Principles:**
- Minimal, calm interface (not busy)
- Strong typography hierarchy
- Excellent whitespace
- Subtle, elegant interactions
- Professional & credible
- Accessible & responsive

---

## Color Palette

### Core Colors

```
Navy (Primary dark)         #0B1220
Navy Soft                   #131C31
Slate                       #F1F5F9

Indigo (Primary accent)     #4F46E5
Indigo Soft (Background)    #EEF2FF

Purple (Secondary accent)   #7C3AED
Purple Soft                 #F5F3FF
```

### Semantic Colors

```
Success                     #16A34A
Success Soft                #ECFDF5

Warning                     #F59E0B
Warning Soft                #FFFBEB

Danger                      #DC2626
Danger Soft                 #FEF2F2

Border                      #E5E7EB
Text Muted                  #64748B
```

### Usage

- **Navy** — Main text, sidebar backgrounds, dark surfaces
- **Indigo** — Primary action, highlights, focus states
- **Purple** — Secondary accents, hover states
- **Slate** — Light backgrounds, subtle surfaces
- **Semantic** — Status indicators, validation messages

---

## Typography

### Font Stack

```css
font-family: Inter, "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
```

### Scale (Fluid)

| Use Case | Size (Desktop) | Size (Mobile) | Weight | Line Height |
|----------|----------------|---------------|--------|-------------|
| Page Title | 2.6rem | 1.8rem | 800 | 1.1 |
| Section Title | 1.85rem | 1.5rem | 800 | 1.15 |
| Card Title | 1.2rem | 1rem | 700 | 1.25 |
| Body Large | 1rem | 0.95rem | 500 | 1.6 |
| Body | 0.96rem | 0.9rem | 500 | 1.5 |
| Body Small | 0.86rem | 0.82rem | 500 | 1.5 |
| Eyebrow | 0.7rem | 0.68rem | 700 | 1 |
| Caption | 0.75rem | 0.7rem | 500 | 1.4 |
| Label | 0.78rem | 0.74rem | 600 | 1 |

### Usage

- **Page Title** — Main heading on each page
- **Section Title** — Major content sections
- **Card Title** — Opportunity/result cards
- **Body Large** — Introduction text
- **Body** — Default text content
- **Body Small** — Secondary information
- **Eyebrow** — Category/tag labels
- **Caption** — Image captions, footnotes
- **Label** — Form labels, metric labels

### Letter Spacing

- Headings: -0.04em (tight)
- Body: normal
- Labels: +0.06em (wide)

---

## Spacing System

**Grid:** 8px base unit

### Spacing Scale

```
XS:  0.25rem (2px)    — Small gaps, tight spacing
SM:  0.5rem  (4px)    — Compact elements
MD:  0.75rem (6px)    — Default element padding
LG:  1rem    (8px)    — Standard section margin
XL:  1.5rem  (12px)   — Large section margin
2XL: 2rem    (16px)   — Major section break
3XL: 3rem    (24px)   — Large vertical spacing
4XL: 4rem    (32px)   — Page-level spacing
```

### Container Padding

- Desktop: 1.2rem
- Tablet: 1rem
- Mobile: 0.75rem

### Card Padding

- Default: 1.1rem 1.25rem
- Dense: 0.8rem 1rem
- Spacious: 1.5rem 1.75rem

---

## Border & Radius

### Border Radius

```
Subtle:   8px   — Inputs, badges
Default:  12px  — Most elements, cards (sidebar)
Rounded:  16px  — Large cards, containers
Pill:     999px — Badges, chips, pills
Minimal:  2px   — Subtle dividers
```

### Borders

```
Default:  1px solid #E5E7EB
Soft:     1px solid #F1F5F9
Strong:   2px solid #C7D2FE (focus state)
```

---

## Shadows & Elevation

### Shadow System

```css
/* No shadow (default) */
box-shadow: none;

/* Subtle (cards, hoverable) */
box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 
            0 8px 24px -12px rgba(15, 23, 42, 0.12);

/* Hover (interactive) */
box-shadow: 0 4px 10px rgba(15, 23, 42, 0.06), 
            0 16px 32px -12px rgba(79, 70, 229, 0.18);

/* Focus (emphasis) */
box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);

/* Deep (modals, popovers) */
box-shadow: 0 20px 50px rgba(15, 23, 42, 0.2);
```

### Elevation Levels

| Level | Usage | Shadow |
|-------|-------|--------|
| 0 | Background surfaces | none |
| 1 | Default cards | Subtle |
| 2 | Hover state | Hover |
| 3 | Active/focus | Focus |
| 4 | Modals, popovers | Deep |

---

## Component Patterns

### Buttons

**Primary Button**
- Background: Indigo gradient (#4F46E5 → #7C3AED)
- Text: White
- Padding: 0.65rem 1.2rem
- Radius: 10px
- Font Weight: 600
- Hover: Slightly darker, shadow-hover

**Secondary Button**
- Background: Slate (#F1F5F9)
- Text: Navy (#0B1220)
- Border: 1px #E5E7EB
- Padding: 0.65rem 1.2rem
- Hover: Border → Indigo, bg → indigo-soft

**Ghost Button**
- Background: Transparent
- Text: Indigo
- Border: 1px Indigo
- Hover: Indigo-soft background

### Forms

**Input Fields**
- Background: White
- Border: 1px #E5E7EB
- Padding: 0.65rem 0.85rem
- Radius: 8px
- Font: Body (0.96rem)
- Focus: Border → strong (2px #C7D2FE), shadow-focus
- Transition: 150ms

**Labels**
- Font: Label (0.78rem, 600)
- Color: Navy
- Margin Bottom: 0.4rem
- Required indicator: Red

### Cards

**Standard Card**
- Background: White
- Border: 1px #E5E7EB
- Radius: 16px
- Padding: 1.1rem 1.25rem
- Shadow: Subtle
- Hover: Shadow-hover, border → #C7D2FE, transform up 2px

**Metric Card**
- Background: White
- Layout: Label on top, metric value large
- Label: 0.78rem, uppercase, muted
- Value: 1.85rem, weight 800

**Opportunity Card**
- Title: 1.05rem, weight 700
- Score badges: Indigo soft background
- Tags: Neutral gray badges
- Footer: "View Details" link
- Hover: Lift effect

### Badges & Tags

**Badge Colors**
- Indigo: Primary, info
- Purple: Secondary
- Success: Completed, verified
- Warning: Pending review
- Danger: Error, blocked
- Neutral: Default, neutral

**Sizes**
- Standard: 0.74rem, 0.28rem 0.6rem padding
- Small: 0.7rem, 0.2rem 0.5rem padding
- Large: 0.85rem, 0.35rem 0.75rem padding

### Progress Indicators

**Progress Bar**
- Height: 8px
- Background: #EEF0F6 (light)
- Fill: Indigo gradient
- Radius: 999px

**Status Dot**
- Size: 8px
- Colors: Green (online), Red (offline), Blue (pending)
- Glow: Subtle box-shadow

### Empty States

- Large illustration or icon (subtle)
- Heading: "No [items] yet"
- Description: 1-2 sentence explanation
- CTA button: Optional
- Color: Navy text on light background

### Loading States

- Spinner: Indigo, 24px
- Label: "Loading..."
- Optional skeleton cards
- Never show for < 200ms

### Error States

- Red accent border or icon
- Heading: "Something went wrong"
- Description: User-friendly error message
- No technical jargon
- Retry button

---

## Layout System

### Desktop (≥ 1024px)

- Main container: max-width 1180px
- Sidebar: 260px fixed
- Content: Remaining width
- Padding: 1.2rem

### Tablet (768px - 1023px)

- Sidebar: Collapsible (hamburger toggle)
- Content: Full width when open
- Padding: 1rem
- Font sizes: Scaled down 5-10%

### Mobile (< 768px)

- Sidebar: Drawer (full-screen overlay)
- Content: Full width
- Padding: 0.75rem
- Font sizes: Scaled down 10-15%
- Modals: Full height
- Buttons: Wider touch targets (44px min)

### Sidebar

- Width: 260px (desktop)
- Background: Navy (#0B1220)
- Text: Light
- Logo: 38px icon + title
- Nav items: 0.85rem, 0.6rem padding
- Hover: Subtle highlight (#1E293B)
- Active: Indigo accent on left

### Navigation

- Top bar: Light background (#F6F7FB)
- Logo/brand: Left
- User menu: Right
- Sticky on scroll
- Height: 60px

---

## Micro-Interactions

### Transitions

```css
/* Default transition (fast, clean) */
transition: all 150ms ease-out;

/* For heavy properties (avoid) */
transition: opacity 150ms ease, transform 150ms ease;

/* For color changes */
transition: background-color 150ms ease, color 150ms ease;
```

### Hover States

- Cards: +2px translateY, shadow-hover, border-color → indigo
- Buttons: Darker shade, shadow increase
- Links: Color → indigo, underline
- Forms: Border → indigo, shadow-focus

### Focus States

- All interactive elements: 2px outline (#C7D2FE)
- Never remove focus indicator
- Maintain keyboard navigation

### Page Transitions

- Fade in: 200ms opacity (0 → 1)
- Slide from right: 300ms translateX (100px → 0)
- Never both simultaneously (avoid janky)

---

## Accessibility

### Contrast

- Text on white: Min 4.5:1 ratio (WCAG AA)
- Navy text: Yes ✓
- Indigo text on white: Needs check, may need darker
- Always test with contrast checker

### Font Sizes

- Never below 12px (10px minimum for captions)
- Zoom support: Maintain at 200%
- Line height: Min 1.4 for body text

### Focus Indicators

- Visible on all interactive elements
- Never use outline: none
- Use 2px border or outline

### Semantic HTML

- Use `<button>` for buttons, not `<div>`
- Use `<form>` for forms
- Use `<label>` for form labels
- Use heading hierarchy (h1 → h6)

### Colors as Only Indicator

- Never rely on color alone to convey info
- Use icon + color for status
- Use label + badge for category

---

## Component Checklist

When building any component, ensure:

- [ ] Responsive (mobile, tablet, desktop)
- [ ] Accessible (contrast, focus, labels)
- [ ] Error state designed
- [ ] Loading state designed
- [ ] Empty state designed
- [ ] Hover/focus states working
- [ ] Touch-friendly (44px min targets)
- [ ] Works without JavaScript
- [ ] Keyboard navigation supported
- [ ] Dark mode compatible (if needed)

---

## File Structure

```
streamlit_app/
├── styles/
│   ├── main.css              ← Base design system
│   ├── components.css        ← Component-specific styles
│   └── responsive.css        ← Breakpoint overrides
├── components/
│   ├── navbar.py
│   ├── sidebar.py
│   ├── cards.py              ← Opportunity, metric, etc.
│   ├── forms.py              ← Profile form, filters
│   ├── buttons.py            ← Button components
│   └── states.py             ← Empty, loading, error
└── pages/
    ├── landing.py            ← Marketing page
    ├── dashboard.py          ← Main dashboard
    ├── profile.py            ← Profile builder
    └── [other pages]
```

---

## CSS Variables Reference

```css
:root {
    /* Colors */
    --ep-navy: #0B1220;
    --ep-indigo: #4F46E5;
    --ep-purple: #7C3AED;
    --ep-border: #E5E7EB;
    --ep-text-muted: #64748B;
    --ep-success: #16A34A;
    --ep-warning: #F59E0B;
    --ep-danger: #DC2626;
    
    /* Gradients */
    --ep-gradient: linear-gradient(120deg, #4F46E5 0%, #7C3AED 100%);
    
    /* Shadows */
    --ep-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 8px 24px -12px rgba(15, 23, 42, 0.12);
    --ep-shadow-hover: 0 4px 10px rgba(15, 23, 42, 0.06), 0 16px 32px -12px rgba(79, 70, 229, 0.18);
    
    /* Transitions */
    --ep-transition-fast: 150ms ease-out;
    --ep-transition-smooth: 300ms ease-out;
    
    /* Spacing */
    --ep-spacing-xs: 0.25rem;
    --ep-spacing-sm: 0.5rem;
    --ep-spacing-md: 0.75rem;
    --ep-spacing-lg: 1rem;
    --ep-spacing-xl: 1.5rem;
    --ep-spacing-2xl: 2rem;
}
```

---

## Implementation Guidelines

### When Building Pages:

1. **Start with structure** — Layout, grid, containers
2. **Apply typography** — Headings, body, labels
3. **Add spacing** — Use spacing scale, not arbitrary values
4. **Apply colors** — Navy for text, indigo for accents
5. **Add shadows & borders** — Polish surfaces
6. **Test responsiveness** — Mobile, tablet, desktop
7. **Add interactions** — Hover, focus, transitions
8. **Validate contrast** — Check WCAG compliance
9. **Test keyboard navigation** — Tab, enter, escape
10. **Final polish** — Micro-interactions, smoothness

### Code Style:

```css
/* Good ✓ */
.component {
    padding: var(--ep-spacing-lg);
    color: var(--ep-navy);
    border-radius: 12px;
    transition: all var(--ep-transition-fast);
}

/* Avoid */
.component {
    padding: 10px;
    color: #0B1220;
    border-radius: 12px;
    transition: all 0.15s ease;
}
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Aug 29, 2026 | Initial design system foundation |

---

## Questions & Updates

Design system is living document. Update as:
- New components added
- Color palette refined
- Typography adjusted
- Spacing guidelines clarified

Contact: [EduPath AI Design Lead]
