// lib/main.dart

import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_auth/firebase_auth.dart' as firebase_auth;
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'config/supabase_config.dart';

import 'google_signin_screen.dart';
import 'screens/preference_selection_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/saved_itineraries_screen.dart';
import 'screens/public_itineraries_screen.dart';
import 'screens/discovery_home_screen.dart';
import 'screens/plandit_explore_screen.dart';
import 'theme/design_system.dart';

// Global navigator key for showing notifications from anywhere
final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();
const String _appFontFamily = 'SF Pro Display';

TextTheme _buildAppTextTheme() {
  TextStyle style(double size, FontWeight weight, Color color) => TextStyle(
        fontFamily: _appFontFamily,
        fontSize: size,
        fontWeight: weight,
        color: color,
      );

  return TextTheme(
    displayLarge: style(
        AppTypography.displayLarge, FontWeight.w700, AppColors.textPrimary),
    displayMedium: style(
        AppTypography.displayMedium, FontWeight.w700, AppColors.textPrimary),
    headlineLarge: style(
        AppTypography.headlineLarge, FontWeight.w700, AppColors.textPrimary),
    headlineMedium: style(
        AppTypography.headlineMedium, FontWeight.w600, AppColors.textPrimary),
    headlineSmall: style(
        AppTypography.headlineSmall, FontWeight.w600, AppColors.textPrimary),
    titleLarge:
        style(AppTypography.titleLarge, FontWeight.w600, AppColors.textPrimary),
    titleMedium: style(
        AppTypography.titleMedium, FontWeight.w500, AppColors.textPrimary),
    titleSmall:
        style(AppTypography.titleSmall, FontWeight.w500, AppColors.textPrimary),
    bodyLarge:
        style(AppTypography.bodyLarge, FontWeight.w400, AppColors.textPrimary),
    bodyMedium:
        style(AppTypography.bodyMedium, FontWeight.w400, AppColors.textPrimary),
    bodySmall: style(
        AppTypography.bodySmall, FontWeight.w400, AppColors.textSecondary),
    labelLarge:
        style(AppTypography.labelLarge, FontWeight.w600, AppColors.textPrimary),
    labelMedium: style(
        AppTypography.labelMedium, FontWeight.w500, AppColors.textSecondary),
    labelSmall: style(
        AppTypography.labelSmall, FontWeight.w500, AppColors.textSecondary),
  );
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize Supabase with error handling
  try {
    await Supabase.initialize(
      url: SupabaseConfig.supabaseUrl,
      anonKey: SupabaseConfig.supabaseAnonKey,
    );
    debugPrint('✅ Supabase initialized successfully');
  } catch (e) {
    debugPrint('⚠️ Supabase initialization failed: $e');
    debugPrint('App will continue without Supabase functionality');
  }
  
  await Firebase.initializeApp();
  firebase_auth.User? user = firebase_auth.FirebaseAuth.instance.currentUser;

  Widget initialScreen;
  if (user == null) {
    // 1) Not signed in yet
    initialScreen = GoogleSignInScreen();
  } else {
    // 2) Signed in — check if they already have saved preferences
    final doc = await FirebaseFirestore.instance
        .collection('user_preferences')
        .doc(user.uid)
        .get();
    if (doc.exists) {
      // preferences already set → go to MainScreen
      initialScreen = const PlanditExploreScreen();
    } else {
      // no preferences yet → show the selection flow
      initialScreen = PreferenceSelectionScreen();
    }
  }

  runApp(FoodExplorerApp(initialScreen: initialScreen));
}

class FoodExplorerApp extends StatelessWidget {
  final Widget initialScreen;
  const FoodExplorerApp({super.key, required this.initialScreen});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: navigatorKey,
      title: 'Food Explorer',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        textTheme: GoogleFonts.mulishTextTheme(
          ThemeData.light().textTheme,
        ),
        colorScheme: ColorScheme.light(
          primary: AppColors.primary,
          secondary: AppColors.secondary,
          surface: AppColors.surface,
          background: AppColors.background,
          error: AppColors.error,
          onPrimary: Colors.white,
          onSecondary: Colors.white,
          onSurface: AppColors.textPrimary,
          onBackground: AppColors.textPrimary,
          onError: Colors.white,
        ),
        scaffoldBackgroundColor: AppColors.background,
      ),
      builder: (context, child) {
        // Provide a ShadTheme ancestor for all Shadcn UI widgets
        return ShadTheme(
          data: ShadThemeData(
            brightness: Brightness.light,
            colorScheme: ShadNeutralColorScheme.light(
              background: AppColors.background,
              foreground: AppColors.textPrimary,
              primary: AppColors.primary,
              primaryForeground: Colors.white,
              border: AppColors.border,
            ),
            radius: BorderRadius.circular(AppBorderRadius.medium),
          ),
          child: ShadToaster(
            child: child ?? const SizedBox.shrink(),
          ),
        );
      },
      routes: {
        '/main': (_) => const MainScreen(),
      },
      home: initialScreen,
    );
  }
}

// Modified BottomNavigationBar builder with minimal design
Widget buildBottomNavBar(BuildContext context,
    {required int currentIndex, required Function(int) onTap}) {
  return Container(
    decoration: BoxDecoration(
      color: AppColors.surfaceElevated,
      border: Border(
        top: BorderSide(color: AppColors.border, width: 1),
      ),
    ),
    child: BottomNavigationBar(
      type: BottomNavigationBarType.fixed,
      backgroundColor: Colors.transparent,
      selectedItemColor: AppColors.orange,
      unselectedItemColor: AppColors.textSecondary,
      selectedFontSize: 12,
      unselectedFontSize: 12,
      elevation: 0,
      currentIndex: currentIndex,
      onTap: onTap,
      items: [
        BottomNavigationBarItem(
          icon: Icon(
            Icons.explore_outlined,
            size: 24,
          ),
          activeIcon: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.explore, size: 24),
              SizedBox(height: 2),
              Container(
                width: 4,
                height: 4,
                decoration: BoxDecoration(
                  color: AppColors.orange,
                  shape: BoxShape.circle,
                ),
              ),
            ],
          ),
          label: 'Discover',
        ),
        BottomNavigationBarItem(
          icon: Icon(Icons.calendar_today_outlined, size: 24),
          activeIcon: Icon(Icons.calendar_today, size: 24),
          label: 'My Plans',
        ),
        BottomNavigationBarItem(
          icon: Icon(Icons.bookmark_outline, size: 24),
          activeIcon: Icon(Icons.bookmark, size: 24),
          label: 'Saved',
        ),
        BottomNavigationBarItem(
          icon: Icon(Icons.person_outline, size: 24),
          activeIcon: Icon(Icons.person, size: 24),
          label: 'Profile',
        ),
      ],
    ),
  );
}

// MainScreen widget that controls navigation between pages.
class MainScreen extends StatefulWidget {
  final int initialTabIndex;

  const MainScreen({super.key, this.initialTabIndex = 0});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  late int _currentIndex;

  @override
  void initState() {
    super.initState();
    _currentIndex = widget.initialTabIndex;
  }

  // List of pages corresponding to each bottom nav item.
  final List<Widget> _pages = [
    const PlanditExploreScreen(), // Discover - Discovery hub with pre-created itineraries
    SavedItinerariesScreen(), // My Plans - Saved Itineraries
    PublicItinerariesScreen(), // Saved - Public Itineraries Feed
    SettingsScreen(), // Profile - Settings
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // IndexedStack preserves the state of each page.
      body: IndexedStack(
        index: _currentIndex,
        children: _pages,
      ),
    );
  }
}
