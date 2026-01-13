import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import '../theme/design_system.dart';
import '../models/timeline_models.dart';
import 'timeline_editor_screen.dart';

class ItineraryCreationScreen extends StatefulWidget {
  const ItineraryCreationScreen({super.key});

  @override
  State<ItineraryCreationScreen> createState() => _ItineraryCreationScreenState();
}

class _ItineraryCreationScreenState extends State<ItineraryCreationScreen> {
  final _titleController = TextEditingController();
  String? _heroImagePath;
  final List<String> _selectedVibes = [];
  final _picker = ImagePicker();

  final List<String> _vibeOptions = [
    'Date Night',
    'Girl\'s Trip',
    'Solo Adventure',
    'Foodie Tour',
    'Hidden Gems',
    'Aesthetic Spots',
    'Quick Bite',
    'Fine Dining',
  ];

  Future<void> _pickHeroImage() async {
    final XFile? image = await _picker.pickImage(source: ImageSource.gallery);
    if (image != null) {
      setState(() {
        _heroImagePath = image.path;
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.close, color: AppColors.textPrimary),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          'Create New Plan',
          style: GoogleFonts.playfairDisplay(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w700,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () {
              final draft = ItineraryDraft(
                title: _titleController.text,
                heroImagePath: _heroImagePath,
                vibeTags: _selectedVibes,
              );
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => TimelineEditorScreen(draft: draft),
                ),
              );
            },
            child: Text(
              'Next',
              style: GoogleFonts.playfairDisplay(
                color: AppColors.orange,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Cover Photo
            GestureDetector(
              onTap: _pickHeroImage,
              child: Container(
                width: double.infinity,
                height: 200,
                decoration: BoxDecoration(
                  color: Colors.grey[100],
                  borderRadius: BorderRadius.circular(16),
                  image: _heroImagePath != null
                      ? DecorationImage(
                          image: FileImage(File(_heroImagePath!)),
                          fit: BoxFit.cover,
                        )
                      : null,
                ),
                child: _heroImagePath == null
                    ? Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.add_a_photo_outlined,
                              size: 40, color: Colors.grey[400]),
                          const SizedBox(height: 8),
                          Text(
                            'Add Cover Photo',
                            style: GoogleFonts.playfairDisplay(
                              color: Colors.grey[500],
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      )
                    : Align(
                        alignment: Alignment.bottomRight,
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: CircleAvatar(
                            backgroundColor: Colors.black.withOpacity(0.5),
                            radius: 18,
                            child: const Icon(Icons.edit,
                                size: 18, color: Colors.white),
                          ),
                        ),
                      ),
              ),
            ),
            const SizedBox(height: 32),

            // Title
            Text(
              'Itinerary Title',
              style: GoogleFonts.playfairDisplay(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _titleController,
              style: GoogleFonts.inter(fontSize: 16),
              decoration: InputDecoration(
                hintText: 'e.g., Perfect SoHo Saturday',
                hintStyle: const TextStyle(color: Colors.grey),
                enabledBorder: UnderlineInputBorder(
                  borderSide: BorderSide(color: Colors.grey[200]!),
                ),
                focusedBorder: const UnderlineInputBorder(
                  borderSide: BorderSide(color: AppColors.orange),
                ),
              ),
            ),
            const SizedBox(height: 32),

            // Vibe Tags
            Text(
              'What\'s the vibe?',
              style: GoogleFonts.playfairDisplay(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 12,
              children: _vibeOptions.map((vibe) {
                final isSelected = _selectedVibes.contains(vibe);
                return GestureDetector(
                  onTap: () => _toggleVibe(vibe),
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    decoration: BoxDecoration(
                      color: isSelected ? AppColors.orange : Colors.grey[50],
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: isSelected ? AppColors.orange : Colors.grey[200]!,
                      ),
                    ),
                    child: Text(
                      vibe,
                      style: GoogleFonts.inter(
                        color: isSelected ? Colors.white : AppColors.textPrimary,
                        fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                        fontSize: 14,
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }
}
