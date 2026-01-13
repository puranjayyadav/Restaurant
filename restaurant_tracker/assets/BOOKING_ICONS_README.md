# Booking Platform Icons

This directory contains icons for restaurant booking platforms.

## Required Icons

### OpenTable
- **File**: `opentable_icon.png`
- **Size**: 48x48px minimum (will be scaled)
- **Format**: PNG with transparency
- **Brand Color**: #DA3743 (red)
- **Download from**: OpenTable brand assets or create a simple red circle with "OT" text

### Resy
- **File**: `resy_icon.png`
- **Size**: 48x48px minimum (will be scaled)
- **Format**: PNG with transparency
- **Brand Color**: #E94B3C (coral red)
- **Download from**: Resy brand assets or create a simple coral circle with "R" text

## Fallback

If icons are not found, the app will display a generic restaurant icon in the brand color.

## Adding Icons

1. Download or create the icon images
2. Place them in this directory (`assets/`)
3. Ensure they are referenced in `pubspec.yaml`:

```yaml
flutter:
  assets:
    - assets/opentable_icon.png
    - assets/resy_icon.png
```

## Brand Guidelines

- **OpenTable**: https://www.opentable.com/about/press
- **Resy**: https://resy.com/press

Always respect brand guidelines when using official logos.
