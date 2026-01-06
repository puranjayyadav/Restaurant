import 'package:flutter/material.dart';

import 'package:intl/intl.dart';

import 'package:shadcn_ui/shadcn_ui.dart';

import '../theme/design_system.dart';

import '../api_service.dart'; // Assuming ApiService is available for API calls.

class NewTripModal extends StatefulWidget {
  const NewTripModal({super.key});

  @override
  State<NewTripModal> createState() => _NewTripModalState();
}

class _NewTripModalState extends State<NewTripModal> {
  String _destination = '';

  DateTime? _startDate;

  DateTime? _endDate;

  String _groupSize = 'Solo';

  List<String> _selectedVibes = [];

  bool _isLoading = false;

  String? _errorMessage;

  final TextEditingController _destinationController = TextEditingController();

  // Dummy list of vibe tags for demonstration

  final List<String> _vibeTags = [
    'Hidden Gems',
    'Foodie',
    'Architecture',
    'Adventure',
    'Relaxation',
    'Nightlife',
    'Family-friendly',
    'Budget-friendly',
    'Luxury',
    'Art & Culture',
    'Nature',
    'Shopping',
    'Historical',
    'Romantic',
    'Beaches',
    'Mountains'
  ];

  @override
  void dispose() {
    _destinationController.dispose();

    super.dispose();
  }

  Future<void> _selectDateRange(BuildContext context) async {
    final initialDateRange = _startDate != null && _endDate != null
        ? DateTimeRange(start: _startDate!, end: _endDate!)
        : null;

    final DateTimeRange? picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime.now(),
      lastDate: DateTime(2101),
      initialDateRange: initialDateRange,
    );

    if (picked != null && picked != initialDateRange) {
      setState(() {
        _startDate = picked.start;

        _endDate = picked.end;
      });
    }
  }

  void _toggleVibe(String vibe) {
    setState(() {
      if (_selectedVibes.contains(vibe)) {
        _selectedVibes.remove(vibe);
      } else {
        _selectedVibes.add(vibe);
      }
    });
  }

  Future<void> _createTrip() async {
    setState(() {
      _isLoading = true;

      _errorMessage = null;
    });

    if (_destination.isEmpty ||
        _startDate == null ||
        _endDate == null ||
        _selectedVibes.isEmpty) {
      setState(() {
        _errorMessage = 'Please fill all required fields.';

        _isLoading = false;
      });

      return;
    }

    try {
      final apiService = ApiService();

      final newTripData = await apiService.createItinerarySkeleton(
        destination: _destination,
        startDate: _startDate!,
        endDate: _endDate!,
        groupSize: _groupSize,
        vibes: _selectedVibes,
      );

      print('New Trip Created with ID: ${newTripData['itinerary_id']}');

      if (!mounted) return;

      Navigator.of(context).pop(); // Close the modal
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to create trip: $e';

        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppColors.background,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppBorderRadius.large),
      ),
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.lg),
        constraints: const BoxConstraints(maxWidth: 500),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Plan a New Trip',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: AppColors.textPrimary,
                    ),
              ),

              const SizedBox(height: AppSpacing.lg),

              // Step 1: Destination

              Text(
                'Where to?',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
              ),

              const SizedBox(height: AppSpacing.md),

              ShadInput(
                controller: _destinationController,
                placeholder: const Text('e.g., Chicago, Paris, Tokyo'),
                onChanged: (value) {
                  setState(() {
                    _destination = value;
                  });
                },
              ),

              const SizedBox(height: AppSpacing.lg),

              // Step 2: When & Who

              Text(
                'When?',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
              ),

              const SizedBox(height: AppSpacing.md),

              ShadButton(
                width: double.infinity,
                onPressed: () => _selectDateRange(context),
                padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
                backgroundColor: AppColors.secondary,
                textStyle: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: AppColors.textPrimary,
                    ),
                child: Text(
                  _startDate == null || _endDate == null
                      ? 'Select Dates'
                      : '${DateFormat.yMMMd().format(_startDate!)} - ${DateFormat.yMMMd().format(_endDate!)}',
                ),
              ),

              const SizedBox(height: AppSpacing.lg),

              Text(
                'Who?',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
              ),

              const SizedBox(height: AppSpacing.md),

              // Custom Toggle Group for Group Size

              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: ['Solo', 'Couple', 'Group'].map((size) {
                  final isSelected = _groupSize == size;

                  return GestureDetector(
                    onTap: () {
                      setState(() {
                        _groupSize = size;
                      });
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.md, vertical: AppSpacing.sm),
                      decoration: BoxDecoration(
                        color: isSelected ? AppColors.teal : AppColors.surface,
                        borderRadius:
                            BorderRadius.circular(AppBorderRadius.large),
                        border: Border.all(
                          color: isSelected ? AppColors.teal : AppColors.border,
                        ),
                      ),
                      child: Text(
                        size,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: isSelected
                                  ? AppColors.textLight
                                  : AppColors.textPrimary,
                              fontWeight: FontWeight.w500,
                            ),
                      ),
                    ),
                  );
                }).toList(),
              ),

              const SizedBox(height: AppSpacing.lg),

              // Step 3: Vibe

              Text(
                "What's the Vibe?",
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
              ),

              const SizedBox(height: AppSpacing.md),

              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: _vibeTags.map((vibe) {
                  final isSelected = _selectedVibes.contains(vibe);

                  return GestureDetector(
                    onTap: () => _toggleVibe(vibe),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.md, vertical: AppSpacing.sm),
                      decoration: BoxDecoration(
                        color: isSelected ? AppColors.teal : AppColors.surface,
                        borderRadius:
                            BorderRadius.circular(AppBorderRadius.large),
                        border: Border.all(
                          color: isSelected ? AppColors.teal : AppColors.border,
                        ),
                      ),
                      child: Text(
                        vibe,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: isSelected
                                  ? AppColors.textLight
                                  : AppColors.textPrimary,
                              fontWeight: FontWeight.w500,
                            ),
                      ),
                    ),
                  );
                }).toList(),
              ),

              const SizedBox(height: AppSpacing.lg),

              if (_errorMessage != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.md),
                  child: Text(
                    _errorMessage!,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: AppColors.error,
                        ),
                  ),
                ),

              ShadButton(
                width: double.infinity,

                onPressed: _isLoading ? null : _createTrip,

                gradient: AppColors.buttonGradient,

                // Removed shadow parameter

                child: _isLoading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          color: AppColors.textLight,
                          strokeWidth: 2,
                        ),
                      )
                    : Text(
                        'Go!',
                        style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                              color: AppColors.textLight,
                              fontWeight: FontWeight.w700,
                            ),
                      ),
              ),

              const SizedBox(height: AppSpacing.sm),

              ShadButton.ghost(
                width: double.infinity,
                onPressed: () => Navigator.of(context).pop(),
                textStyle: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                child: const Text('Cancel'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
