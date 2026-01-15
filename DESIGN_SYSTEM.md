# Plandit Design System

This document outlines the design system for the Plandit application, including the overall design pattern, color palette, typography, and common components.

## Overall Design Pattern

The Plandit app employs a minimalist, warm-neutral theme with a "premium Modern Classic" aesthetic. The design emphasizes clarity and readability, with a focus on content and a clean, uncluttered user interface. The layout is structured and consistent, with a clear hierarchy of information.

## Color Palette

The app uses two main color palettes, `AppColors` for general UI elements and `PlanditColors` for a more premium, branded look.

### AppColors

- **Background:** `0xFFF9F9F9` (Bone / Off-White)
- **Surface:** `0xFFFFFFFF` (White)
- **Primary:** `0xFF007AFF` (Electric Blue)
- **Secondary:** `0xFF8B5CF6` (Lavender Accent)
- **Accent:** `0xFFFF6B35` (Warm Accent for CTAs)
- **Text Primary:** `0xFF1C1C1E` (Deep Slate)
- **Text Secondary:** `0xFF8E8E93` (Mid-grey)
- **Border:** `0xFFE5E5EA`

### PlanditColors

- **Canvas:** `0xFFFFFFFF`
- **Background:** `0xFFF9F7F2` (Warm off-white)
- **Primary Text:** `0xFF1A1A1A` (Dark Charcoal)
- **Secondary Text:** `0xFF6E6E73` (Cool Slate Gray)
- **Accent Gold:** `0xFFD4AF37` (Muted Gold/Bronze)

## Typography

The app uses a range of font sizes to create a clear visual hierarchy.

- **Display Large:** 48.0
- **Display Medium:** 36.0
- **Headline Large:** 32.0
- **Headline Medium:** 28.0
- **Headline Small:** 24.0
- **Title Large:** 22.0
- **Title Medium:** 18.0
- **Title Small:** 16.0
- **Body Large:** 16.0
- **Body Medium:** 14.0
- **Body Small:** 12.0
- **Label Large:** 14.0
- **Label Medium:** 12.0
- **Label Small:** 10.0

## Spacing

Consistent spacing is used throughout the app to ensure a balanced and harmonious layout.

- **XS:** 4.0
- **SM:** 8.0
- **MD:** 16.0
- **LG:** 24.0
- **XL:** 32.0
- **XXL:** 48.0

## Border Radius

- **Small:** 8.0
- **Medium:** 12.0
- **Large:** 16.0
- **X-Large:** 24.0

## Elevation and Shadows

- **Low:** 2.0
- **Medium:** 4.0
- **High:** 8.0

The app also uses custom shadows to create a sense of depth and dimension.

## Gradients

- **Button Gradient:** A linear gradient from `AppColors.orange` to `AppColors.teal`.
- **Overlay Gradient:** A linear gradient used for overlays, creating a subtle fading effect.

## Common Components

The app utilizes a variety of reusable widgets to maintain consistency and streamline development.

- **Cards:** The app uses cards to display information about itineraries, places, and restaurants. These cards typically include an image, a title, and a brief description.
- **Buttons:** The app features a variety of button styles, including primary, secondary, and accent buttons, as well as like buttons.
- **Input Fields:** Text input fields are used for search, location autocomplete, and other forms.
- **Badges:** Badges are used to display additional information or to highlight certain features.
- **Map Widgets:** The app includes map widgets for displaying routes and heatmaps.
