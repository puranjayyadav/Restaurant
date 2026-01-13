import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'google_signin_screen.dart'; // Change this if you have a dedicated login screen

class LogoutButton extends StatelessWidget {
  const LogoutButton({super.key});

  Future<void> _logout(BuildContext context) async {
    try {
      await FirebaseAuth.instance.signOut();
      // After logging out, navigate to the login screen.
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => GoogleSignInScreen()),
      );
    } catch (e) {
      print('Error during logout: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Logout failed. Please try again.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return IconButton(
      icon: const Icon(Icons.logout),
      tooltip: 'Logout',
      onPressed: () => _logout(context),
    );
  }
}
