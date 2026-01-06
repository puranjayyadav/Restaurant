import 'package:flutter/material.dart';
import 'dart:async';
import '../api_service.dart';

class LocationAutocompleteTextField extends StatefulWidget {
  final TextEditingController controller;
  final String hintText;
  final Function(Map<String, dynamic>) onPlaceSelected;
  final double? lat;
  final double? lon;
  final InputDecoration? inputDecoration;
  final TextStyle? textStyle;

  const LocationAutocompleteTextField({
    Key? key,
    required this.controller,
    required this.onPlaceSelected,
    this.hintText = 'Search location...',
    this.lat,
    this.lon,
    this.inputDecoration,
    this.textStyle,
  }) : super(key: key);

  @override
  _LocationAutocompleteTextFieldState createState() =>
      _LocationAutocompleteTextFieldState();
}

class _LocationAutocompleteTextFieldState
    extends State<LocationAutocompleteTextField> {
  final ApiService _apiService = ApiService();
  List<Map<String, dynamic>> _suggestions = [];
  bool _showSuggestions = false;
  Timer? _debounceTimer;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    widget.controller.removeListener(_onTextChanged);
    super.dispose();
  }

  void _onTextChanged() {
    _debounceTimer?.cancel();
    _debounceTimer = Timer(Duration(milliseconds: 500), () {
      _searchPlaces(widget.controller.text);
    });
  }

  Future<void> _searchPlaces(String query) async {
    if (query.isEmpty) {
      setState(() {
        _suggestions = [];
        _showSuggestions = false;
      });
      return;
    }

    try {
      // Use Nominatim for autocomplete (geocoding only)
      final results = await _apiService.geocodeNominatim(query);

      if (mounted) {
        setState(() {
          _suggestions = results;
          _showSuggestions = true;
        });
      }
    } catch (e) {
      print('Error searching places: $e');
      if (mounted) {
        setState(() {
          _suggestions = [];
          _showSuggestions = false;
        });
      }
    }
  }

  void _selectPlace(Map<String, dynamic> place) {
    final description = place['formatted_address'] as String? ?? '';
    widget.controller.text = description;
    setState(() {
      _showSuggestions = false;
    });
    widget.onPlaceSelected(place);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          controller: widget.controller,
          style: widget.textStyle,
          decoration: widget.inputDecoration ??
              InputDecoration(
                hintText: widget.hintText,
                prefixIcon: Icon(Icons.search),
              ),
        ),
        if (_showSuggestions && _suggestions.isNotEmpty)
          Container(
            constraints: BoxConstraints(maxHeight: 200),
            decoration: BoxDecoration(
              color: Theme.of(context).cardColor,
              boxShadow: [
                BoxShadow(
                  color: Colors.black26,
                  blurRadius: 4,
                  offset: Offset(0, 2),
                ),
              ],
              borderRadius: BorderRadius.circular(8),
            ),
            child: ListView.builder(
              shrinkWrap: true,
              itemCount: _suggestions.length,
              itemBuilder: (context, index) {
                final place = _suggestions[index];
                final formattedAddress =
                    place['formatted_address'] as String? ?? '';
                final parts = formattedAddress.split(',');
                final mainText = parts.isNotEmpty ? parts[0].trim() : '';
                final secondaryText =
                    parts.length > 1 ? parts.sublist(1).join(',').trim() : '';

                return ListTile(
                  dense: true,
                  title: Text(
                    mainText,
                    style: TextStyle(fontWeight: FontWeight.w500),
                  ),
                  subtitle: Text(
                    secondaryText,
                    style: TextStyle(fontSize: 12),
                  ),
                  onTap: () => _selectPlace(place),
                );
              },
            ),
          ),
      ],
    );
  }
}
