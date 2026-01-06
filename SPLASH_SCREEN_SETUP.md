# Splash Screen Setup - Plandit Logo

## ✅ Configuration Complete

The splash screen has been configured to display the Plandit logo on a white background.

## 📸 Required: Add Logo Images

You need to add your Plandit logo image files to complete the setup:

### For iOS:

1. **Add logo images to:** `restaurant_tracker/ios/Runner/Assets.xcassets/LaunchImage.imageset/`

   Replace or add these files:
   - `LaunchImage.png` (1x - 375x375px recommended)
   - `LaunchImage@2x.png` (2x - 750x750px recommended)
   - `LaunchImage@3x.png` (3x - 1125x1125px recommended)

   **OR** use one high-resolution image (1125x1125px or larger) and Xcode will generate the others.

### For Android:

1. **Add logo images to these directories:**

   - `restaurant_tracker/android/app/src/main/res/mipmap-hdpi/launch_image.png` (144x144px)
   - `restaurant_tracker/android/app/src/main/res/mipmap-xhdpi/launch_image.png` (192x192px)
   - `restaurant_tracker/android/app/src/main/res/mipmap-xxhdpi/launch_image.png` (288x288px)
   - `restaurant_tracker/android/app/src/main/res/mipmap-xxxhdpi/launch_image.png` (384x384px)

   **Note:** You can use the same logo image for all sizes - Android will scale it automatically, but providing multiple sizes gives better quality.

## 🎨 Logo Specifications

- **Format:** PNG (with transparency if needed)
- **Background:** The splash screen background is white, so ensure your logo looks good on white
- **Recommended size:** Square format (1:1 aspect ratio) works best
- **Minimum size:** 512x512px for good quality

## ✅ What's Already Configured

- ✅ iOS LaunchScreen.storyboard - White background, centered logo (ready for logo images)
- ✅ Android launch_background.xml - White background (logo reference commented out until images are added)
- ✅ Logo will be displayed at 250x250 points on iOS
- ✅ Logo will be centered on both platforms

## ⚠️ Important: Android Logo Setup

The Android logo reference is currently **commented out** to prevent build errors. After you add the `launch_image.png` files to the mipmap directories:

1. Open `android/app/src/main/res/drawable/launch_background.xml`
2. Open `android/app/src/main/res/drawable-v21/launch_background.xml`
3. Uncomment the logo section (remove the `<!--` and `-->` tags around the `<item>` block)
4. Rebuild the app

## 🧪 Testing

After adding the logo images:

```bash
cd restaurant_tracker
flutter clean
flutter run
```

The splash screen should now show your Plandit logo centered on a white background!

## 📝 Notes

- The logo will automatically scale to fit while maintaining aspect ratio
- If you don't see the logo, make sure the image files are in the correct locations
- For iOS, you may need to open the project in Xcode and verify the images are properly added to the asset catalog

