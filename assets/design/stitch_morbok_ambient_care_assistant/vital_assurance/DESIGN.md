---
name: Vital Assurance
colors:
  surface: '#f9f9ff'
  surface-dim: '#cfdaf1'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f0f3ff'
  surface-container: '#e7eeff'
  surface-container-high: '#dee8ff'
  surface-container-highest: '#d8e3fa'
  on-surface: '#111c2c'
  on-surface-variant: '#43474f'
  inverse-surface: '#263142'
  inverse-on-surface: '#ebf1ff'
  outline: '#737780'
  outline-variant: '#c3c6d1'
  surface-tint: '#3a5f94'
  primary: '#001e40'
  on-primary: '#ffffff'
  primary-container: '#003366'
  on-primary-container: '#799dd6'
  inverse-primary: '#a7c8ff'
  secondary: '#006d33'
  on-secondary: '#ffffff'
  secondary-container: '#75f999'
  on-secondary-container: '#007236'
  tertiary: '#1a1f22'
  on-tertiary: '#ffffff'
  tertiary-container: '#2f3437'
  on-tertiary-container: '#989ca0'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d5e3ff'
  primary-fixed-dim: '#a7c8ff'
  on-primary-fixed: '#001b3c'
  on-primary-fixed-variant: '#1f477b'
  secondary-fixed: '#78fc9c'
  secondary-fixed-dim: '#5adf82'
  on-secondary-fixed: '#00210b'
  on-secondary-fixed-variant: '#005225'
  tertiary-fixed: '#dfe3e7'
  tertiary-fixed-dim: '#c3c7cb'
  on-tertiary-fixed: '#171c1f'
  on-tertiary-fixed-variant: '#43474b'
  background: '#f9f9ff'
  on-background: '#111c2c'
  surface-variant: '#d8e3fa'
typography:
  headline-lg:
    fontFamily: Manrope
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Manrope
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-bold:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter-mobile: 16px
  margin-mobile: 20px
  max-width-mobile: 480px
---

## Brand & Style

The design system is engineered for the healthcare sector, specifically tailored for the 'MorBok' web application. The brand personality is rooted in **Reliability, Compassion, and Clarity**. It aims to evoke a sense of professional security and calm efficiency, which is critical when users are navigating health-related information or seeking medical assistance.

The visual style is a blend of **Corporate Modernism** and **Minimalism**. By utilizing heavy whitespace and a restricted, authoritative color palette derived from the provided logo, the interface prioritizes content legibility and ease of use on mobile devices. The aesthetic avoids unnecessary decoration, favoring functional clarity and a systematic structure that communicates trustworthiness and medical precision.

## Colors

The palette is anchored by a **Deep Marine Blue** (#003366), representing authority and professional stability. This is complemented by **Vitality Green** (#00A651), used strategically for positive actions, health indicators, and primary call-to-actions.

*   **Primary (Deep Blue):** Used for headers, navigation, and primary branding elements to establish a solid foundation.
*   **Secondary (Green):** Reserved for "Success" states, confirmation buttons, and health-related iconography to inspire growth and wellness.
*   **Neutral Palette:** High-contrast charcoal for text (#4A5568) and very light cool greys for backgrounds and borders to maintain a clean, clinical feel without the harshness of pure black-on-white.
*   **Background:** A pure white or extremely subtle off-white (#FAFAFA) is used to maximize the sense of hygiene and space.

## Typography

This design system employs a dual-font strategy to balance character with utility. **Manrope** is used for headings to provide a modern, friendly yet professional geometric touch. **Inter** is utilized for all body copy and labels due to its exceptional readability on small screens and neutral, systematic appearance.

On mobile devices, headlines are scaled down slightly to prevent excessive line-breaking, while body text remains at a comfortable 16px to ensure accessibility for all users, including those with visual impairments. High contrast between weights (700 for headers vs 400 for body) is used to establish a clear information hierarchy.

## Layout & Spacing

The layout follows a **Fluid Grid** model optimized for smartphone portrait orientation. It uses a 4px base increment to ensure consistent mathematical relationships between elements.

*   **Mobile Grid:** A 4-column system with 16px gutters and 20px side margins.
*   **Vertical Rhythm:** Generous vertical spacing (minimum 24px between distinct sections) is used to prevent the interface from feeling cluttered, which can be stressful in a healthcare context.
*   **Safe Areas:** All critical interactive elements (buttons, inputs) must be placed within the safe horizontal margins, keeping the "thumb zone" in mind for easy one-handed operation.

## Elevation & Depth

Visual hierarchy is established primarily through **Tonal Layers** and **Low-Contrast Outlines** rather than heavy shadows. This maintains the minimal, professional "clinical" look.

*   **Surfaces:** The primary background is Level 0 (White). Cards and containers are Level 1 (White with a 1px border of #E2E8F0).
*   **Interactive Elevation:** Only primary buttons and high-priority cards (like urgent notifications) use a very soft, diffused ambient shadow (Color: #003366 at 8% opacity, Y: 4px, Blur: 12px) to suggest clickability.
*   **Separation:** Use subtle background fills (#F8FAFC) to differentiate page sections instead of lines where possible to maintain an open feel.

## Shapes

The shape language is **Rounded**, using a consistent 8px (0.5rem) corner radius for most UI components. This softens the "corporate" feel of the deep blue, making the application appear more approachable and human-centric.

*   **Standard (rounded-md):** 8px for buttons, input fields, and cards.
*   **Large (rounded-lg):** 16px for major modal containers and bottom sheets.
*   **Pill:** Reserved specifically for status tags (e.g., "Confirmed", "Active") and search bars to distinguish them from action buttons.

## Components

### Buttons
*   **Primary:** Solid Green (#00A651) with white text. High-contrast, bold weight.
*   **Secondary:** Solid Deep Blue (#003366) with white text for secondary global actions.
*   **Ghost/Outline:** Deep Blue border and text for less critical actions like "Cancel" or "Edit."

### Input Fields
*   **Design:** White background with a 1px #CBD5E0 border. On focus, the border transitions to Deep Blue with a 2px stroke.
*   **Labels:** Always visible above the field in `label-bold` style. Never rely solely on placeholder text.

### Cards
*   Used for patient records, appointment slots, and health tips. 
*   Feature an 8px radius and a subtle 1px border.
*   Internal padding is fixed at 16px to ensure content doesn't feel cramped.

### Chips & Tags
*   Small, pill-shaped elements with light background tints (e.g., light green background for a "Healthy" status) and darker text of the same hue.

### Bottom Sheets
*   The primary mobile navigation pattern for complex inputs or selection menus. They should have a 16px top-corner radius and a visible "drag handle" at the top center.

### Lists
*   List items should have a minimum height of 56px to ensure a large enough tap target for mobile users. Use 1px #EDF2F7 dividers between items.