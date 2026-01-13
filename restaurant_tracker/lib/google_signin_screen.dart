import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:http/http.dart' as http;
import 'package:shadcn_ui/shadcn_ui.dart';
import 'mode_selection_screen.dart';
import 'theme/design_system.dart';
import 'api_service.dart';

class GoogleSignInScreen extends StatefulWidget {
  const GoogleSignInScreen({super.key});

  @override
  _GoogleSignInScreenState createState() => _GoogleSignInScreenState();
}

class _GoogleSignInScreenState extends State<GoogleSignInScreen> {
  final FirebaseAuth _auth = FirebaseAuth.instance;

  Future<void> _signInWithGoogle() async {
    try {
      final GoogleSignInAccount? googleUser = await GoogleSignIn().signIn();
      if (googleUser == null) return; // user canceled sign-in

      final GoogleSignInAuthentication googleAuth =
          await googleUser.authentication;
      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );

      final UserCredential userCredential =
          await _auth.signInWithCredential(credential);

      // Log the user's unique ID (UID)
      print("User UID: ${userCredential.user!.uid}");

      final idToken = await userCredential.user?.getIdToken();
      if (idToken == null) {
        print('Could not obtain ID token');
        return;
      }

      print("Firebase ID Token: $idToken");

      final response = await http.post(
        Uri.parse('${ApiService.baseUrl}/api/verify-token/'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $idToken',
        },
      );

      if (response.statusCode == 200) {
        final body = jsonDecode(response.body);
        print('Django verification success: $body');
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => ModeSelectionScreen()),
        );
      } else {
        print('Django verification failed: ${response.body}');
      }
    } catch (e) {
      print('Error during Google Sign-In: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: EdgeInsets.all(AppSpacing.xl),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // App Logo/Branding
                Container(
                  padding: EdgeInsets.all(AppSpacing.lg),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    Icons.restaurant_menu_outlined,
                    size: 48,
                    color: AppColors.primary,
                  ),
                ),
                SizedBox(height: AppSpacing.xl),

                // App Title
                Text(
                  'Food Explorer',
                  style: Theme.of(context).textTheme.displayMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                        letterSpacing: -0.5,
                      ),
                ),
                SizedBox(height: AppSpacing.md),

                // Subtitle
                Text(
                  'Plan your perfect day,\none place at a time',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        color: AppColors.textSecondary,
                        height: 1.5,
                      ),
                ),
                SizedBox(height: AppSpacing.xxl),

                // Sign In Card
                ShadCard(
                  backgroundColor: AppColors.surfaceElevated,
                  padding: EdgeInsets.all(AppSpacing.xl),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'Get Started',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                      ),
                      SizedBox(height: AppSpacing.lg),
                      SizedBox(
                        width: double.infinity,
                        child: ShadButton(
                          size: ShadButtonSize.lg,
                          onPressed: _signInWithGoogle,
                          backgroundColor: AppColors.primary,
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.login, size: 20, color: Colors.white),
                              SizedBox(width: AppSpacing.sm),
                              const Text(
                                'Continue with Google',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                SizedBox(height: AppSpacing.xxl),

                // Footer text
                Text(
                  'Discover curated experiences\ntailored just for you',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.textSecondary,
                        height: 1.6,
                      ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
