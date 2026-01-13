import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/design_system.dart';
import '../../models/timeline_models.dart';

class StopDetailSheet extends StatefulWidget {
  final TimelineStop stop;
  final Function(TimelineStop) onSave;

  const StopDetailSheet({
    super.key,
    required this.stop,
    required this.onSave,
  });

  @override
  State<StopDetailSheet> createState() => _StopDetailSheetState();
}

class _StopDetailSheetState extends State<StopDetailSheet> {
  late String _name;
  late StopTimeOfDay _timeOfDay;
  late int _cost;
  late int _aesthetic;
  late StopCrowdLevel _crowd;
  String? _category;
  late TextEditingController _photoOpController;
  late TextEditingController _mustOrderController;
  late TextEditingController _dontOrderController;
  late TextEditingController _reviewController;

  @override
  void initState() {
    super.initState();
    _name = widget.stop.name ?? '';
    _timeOfDay = widget.stop.timeOfDay;
    _cost = widget.stop.costPerPerson;
    _aesthetic = widget.stop.aestheticRating;
    _crowd = widget.stop.crowdLevel;
    _category = widget.stop.category;
    _photoOpController = TextEditingController(text: widget.stop.bestShotLocation);
    _mustOrderController = TextEditingController(text: widget.stop.mustOrder);
    _dontOrderController = TextEditingController(text: widget.stop.overhypedItem);
    _reviewController = TextEditingController(text: widget.stop.tweetReview);
  }

  void _save() {
    final updatedStop = widget.stop.copyWith(
      name: _name,
      timeOfDay: _timeOfDay,
      costPerPerson: _cost,
      aestheticRating: _aesthetic,
      crowdLevel: _crowd,
      category: _category,
      bestShotLocation: _photoOpController.text,
      mustOrder: _mustOrderController.text,
      overhypedItem: _dontOrderController.text,
      tweetReview: _reviewController.text,
    );
    widget.onSave(updatedStop);
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.9,
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
      ),
      child: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.all(24),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Edit Stop',
                  style: GoogleFonts.playfairDisplay(
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                    color: AppColors.textPrimary,
                  ),
                ),
                TextButton(
                  onPressed: _save,
                  child: Text(
                    'Done',
                    style: GoogleFonts.playfairDisplay(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: AppColors.orange,
                    ),
                  ),
                ),
              ],
            ),
          ),
          
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(24, 0, 24, 40),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Location Input
                  _buildSectionTitle('Where were you?'),
                  TextField(
                    onChanged: (val) => _name = val,
                    controller: TextEditingController(text: _name),
                    style: GoogleFonts.inter(fontWeight: FontWeight.w600),
                    decoration: InputDecoration(
                      hintText: 'Search for a place...',
                      prefixIcon: const Icon(Icons.location_on_outlined, color: AppColors.orange),
                      filled: true,
                      fillColor: Colors.grey[50],
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(16),
                        borderSide: BorderSide.none,
                      ),
                    ),
                  ),
                  const SizedBox(height: 32),

                  // Time & Cost Row
                  Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _buildSectionTitle('Time of Day'),
                            _buildDropdown<StopTimeOfDay>(
                              value: _timeOfDay,
                              items: StopTimeOfDay.values,
                              onChanged: (val) => setState(() => _timeOfDay = val!),
                              label: (v) => v.name.toUpperCase(),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _buildSectionTitle('Cost/Person'),
                            _buildCostPicker(),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 32),

                  const Divider(),
                  const SizedBox(height: 32),

                  // Aesthetic Rating
                  _buildSectionTitle('How Instagrammable was it?'),
                  _buildAestheticPicker(),
                  const SizedBox(height: 32),

                  // Crowd Meter
                  _buildSectionTitle('How busy was it?'),
                  _buildCrowdPicker(),
                  const SizedBox(height: 32),

                  // Photo Op
                  _buildSectionTitle('Where is the best photo op?'),
                  _buildTextField(
                    controller: _photoOpController,
                    hint: 'e.g., The neon sign in the back...',
                    icon: Icons.camera_alt_outlined,
                  ),
                  const SizedBox(height: 32),

                  // Category Selector
                  _buildSectionTitle('What kind of place is this?'),
                  _buildCategoryPicker(),
                  const SizedBox(height: 24),

                  // Contextual Questions
                  if (_category != null) ...[
                    _buildContextualQuestions(),
                    const SizedBox(height: 32),
                  ],

                  const Divider(),
                  const SizedBox(height: 32),

                  // Food Data
                  _buildSectionTitle('Must-Order Item'),
                  _buildTextField(
                    controller: _mustOrderController,
                    hint: 'What\'s the one dish to try?',
                    icon: Icons.restaurant_menu,
                  ),
                  const SizedBox(height: 24),
                  _buildSectionTitle('Don\'t Order (Overhyped)'),
                  _buildTextField(
                    controller: _dontOrderController,
                    hint: 'Was anything a letdown?',
                    icon: Icons.thumb_down_off_alt,
                  ),
                  const SizedBox(height: 32),

                  // Tweet Review
                  _buildSectionTitle('Quick Impression (Tweet length)'),
                  TextField(
                    controller: _reviewController,
                    maxLength: 280,
                    maxLines: 3,
                    style: GoogleFonts.inter(),
                    decoration: InputDecoration(
                      hintText: 'Share the vibe in a few words...',
                      filled: true,
                      fillColor: Colors.grey[50],
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(16),
                        borderSide: BorderSide.none,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Text(
        title,
        style: GoogleFonts.playfairDisplay(
          fontSize: 15,
          fontWeight: FontWeight.w700,
          color: AppColors.textPrimary,
        ),
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String hint,
    required IconData icon,
  }) {
    return TextField(
      controller: controller,
      style: GoogleFonts.inter(fontSize: 14),
      decoration: InputDecoration(
        hintText: hint,
        prefixIcon: Icon(icon, color: Colors.grey[400], size: 20),
        filled: true,
        fillColor: Colors.grey[50],
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
      ),
    );
  }

  Widget _buildDropdown<T>({
    required T value,
    required List<T> items,
    required Function(T?) onChanged,
    required String Function(T) label,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        color: Colors.grey[50],
        borderRadius: BorderRadius.circular(12),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<T>(
          value: value,
          isExpanded: true,
          items: items.map((t) => DropdownMenuItem(
            value: t,
            child: Text(label(t), style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w600)),
          )).toList(),
          onChanged: onChanged,
        ),
      ),
    );
  }

  Widget _buildCostPicker() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: List.generate(4, (index) {
        final level = index + 1;
        final isSelected = _cost == level;
        return GestureDetector(
          onTap: () => setState(() => _cost = level),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: isSelected ? AppColors.orange : Colors.grey[100],
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              '\$' * level,
              style: GoogleFonts.inter(
                color: isSelected ? Colors.white : Colors.grey[600],
                fontWeight: FontWeight.w800,
                fontSize: 12,
              ),
            ),
          ),
        );
      }),
    );
  }

  Widget _buildAestheticPicker() {
    return Row(
      children: List.generate(5, (index) {
        final rating = index + 1;
        final isSelected = _aesthetic >= rating;
        return IconButton(
          onPressed: () => setState(() => _aesthetic = rating),
          icon: Icon(
            isSelected ? Icons.auto_awesome : Icons.auto_awesome_outlined,
            color: isSelected ? AppColors.orange : Colors.grey[300],
            size: 32,
          ),
        );
      }),
    );
  }

  Widget _buildCrowdPicker() {
    final options = [
      {'label': 'Empty', 'icon': Icons.person_outline, 'val': StopCrowdLevel.empty},
      {'label': 'Bustling', 'icon': Icons.people_outline, 'val': StopCrowdLevel.bustling},
      {'label': 'Line Out Door', 'icon': Icons.groups_outlined, 'val': StopCrowdLevel.lineOutDoor},
      {'label': 'Sardine Can', 'icon': Icons.sports_kabaddi, 'val': StopCrowdLevel.sardineCan},
    ];

    return Wrap(
      spacing: 8,
      children: options.map((opt) {
        final isSelected = _crowd == opt['val'];
        return ChoiceChip(
          label: Text(opt['label'] as String),
          selected: isSelected,
          onSelected: (selected) {
            if (selected) setState(() => _crowd = opt['val'] as StopCrowdLevel);
          },
          selectedColor: AppColors.orange.withOpacity(0.2),
          labelStyle: GoogleFonts.inter(
            color: isSelected ? AppColors.orange : Colors.grey[600],
            fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
            fontSize: 12,
          ),
        );
      }).toList(),
    );
  }

  Widget _buildCategoryPicker() {
    final categories = ['Coffee Shop', 'Bar', 'Fine Dining', 'Museum', 'Park', 'Other'];
    return Wrap(
      spacing: 8,
      children: categories.map((cat) {
        final isSelected = _category == cat;
        return ChoiceChip(
          label: Text(cat),
          selected: isSelected,
          onSelected: (selected) {
            setState(() => _category = selected ? cat : null);
          },
          selectedColor: AppColors.orange.withOpacity(0.2),
        );
      }).toList(),
    );
  }

  Widget _buildContextualQuestions() {
    if (_category == 'Coffee Shop') {
      return _buildToggleQuestion('Is it laptop friendly?', 'laptop_friendly');
    } else if (_category == 'Bar') {
      return Column(
        children: [
          _buildToggleQuestion('Good for a date?', 'good_for_date'),
          const SizedBox(height: 12),
          _buildToggleQuestion('Good for a group?', 'good_for_group'),
        ],
      );
    } else if (_category == 'Fine Dining') {
      return _buildToggleQuestion('Is there a dress code?', 'dress_code');
    }
    return const SizedBox.shrink();
  }

  Widget _buildToggleQuestion(String question, String key) {
    final isEnabled = widget.stop.contextualAnswers[key] == true;
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(question, style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w500)),
        Switch(
          value: isEnabled,
          onChanged: (val) {
            setState(() {
              widget.stop.contextualAnswers[key] = val;
            });
          },
          activeColor: AppColors.orange,
        ),
      ],
    );
  }
}
