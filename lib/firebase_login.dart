import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  runApp(FirebaseAuthDemo());
}

class FirebaseAuthDemo extends StatelessWidget {
  const FirebaseAuthDemo({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Firebase Auth Demo',
      theme: ThemeData(primarySwatch: Colors.deepOrange),
      home: SignInScreen(),
    );
  }
}

class SignInScreen extends StatefulWidget {
  const SignInScreen({super.key});

  @override
  _SignInScreenState createState() => _SignInScreenState();
}

class _SignInScreenState extends State<SignInScreen> {
  bool _isSigningIn = false;
  User? _user;

  Future<void> _signInWithGoogle() async {
    setState(() {
      _isSigningIn = true;
    });
    try {
      // Trigger the authentication flow.
      final GoogleSignInAccount? googleUser = await GoogleSignIn().signIn();
      if (googleUser == null) {
        // User aborted the sign-in process.
        setState(() {
          _isSigningIn = false;
        });
        return;
      }

      // Obtain the auth details from the request.
      final GoogleSignInAuthentication googleAuth =
          await googleUser.authentication;

      // Create a new credential for Firebase.
      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );

      // Sign in to Firebase with the credential.
      final UserCredential userCredential =
          await FirebaseAuth.instance.signInWithCredential(credential);
      setState(() {
        _user = userCredential.user;
        _isSigningIn = false;
      });

      // Print the user's UID to the console.
      print("User UID: ${_user!.uid}");
    } catch (e) {
      print('Error during Google Sign-In: $e');
      setState(() {
        _isSigningIn = false;
      });
    }
  }

  Future<void> _signOut() async {
    await FirebaseAuth.instance.signOut();
    await GoogleSignIn().signOut();
    setState(() {
      _user = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Firebase Auth Demo'),
      ),
      body: Center(
        child: _isSigningIn
            ? CircularProgressIndicator()
            : _user == null
                ? ElevatedButton(
                    onPressed: _signInWithGoogle,
                    child: Text('Sign in with Google'),
                  )
                : Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        'Welcome, ${_user!.displayName}!',
                        style: TextStyle(fontSize: 20),
                      ),
                      SizedBox(height: 8),
                      Text('Your UID is: ${_user!.uid}'),
                      SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _signOut,
                        child: Text('Sign Out'),
                      ),
                    ],
                  ),
      ),
    );
  }
}
