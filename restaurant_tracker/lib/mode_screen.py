import 'package:flutter/material.dart';
import 'api_service.dart';

class RendezvousScreen extends StatefulWidget {
  @override
  _RendezvousScreenState createState() => _RendezvousScreenState();
}

class _RendezvousScreenState extends State<RendezvousScreen> {
  final TextEditingController _destinationController = TextEditingController();
  final ApiService apiService = ApiService();
  bool isLoading = false;
  List<dynamic> suggestions = [];

  void _fetchSuggestions() async {
    final destination = _destinationController.text.trim();
    if (destination.isEmpty) return;
    
    setState(() {
      isLoading = true;
    });

    try {
      final data = await apiService.fetchRendezvousSuggestions(destination);
      setState(() {
        suggestions = data;
      });
    } catch (e) {
      // Handle error, e.g., show a snackbar.
      print("Error fetching suggestions: $e");
    } finally {
      setState(() {
        isLoading = false;
      });
    }
  }

  @override
  void dispose() {
    _destinationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Rendezvous Mode')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            TextField(
              controller: _destinationController,
              decoration: InputDecoration(
                labelText: 'Enter your final destination',
              ),
            ),
            SizedBox(height: 20),
            ElevatedButton(
              onPressed: _fetchSuggestions,
              child: Text('Plan My Day'),
            ),
            SizedBox(height: 20),
            isLoading
                ? CircularProgressIndicator()
                : Expanded(
                    child: ListView.builder(
                      itemCount: suggestions.length,
                      itemBuilder: (context, index) {
                        final suggestion = suggestions[index];
                        return ListTile(
                          title: Text(suggestion['name'] ?? 'Unnamed'),
                          subtitle: Text(suggestion['address'] ?? 'No address'),
                        );
                      },
                    ),
                  ),
          ],
        ),
      ),
    );
  }
}
