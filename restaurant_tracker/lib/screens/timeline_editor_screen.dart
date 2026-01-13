import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import '../theme/design_system.dart';
import '../models/timeline_models.dart';
import '../widgets/timeline/stop_detail_sheet.dart';
import 'package:exif/exif.dart';
import 'package:geocoding/geocoding.dart';
import 'package:intl/intl.dart';

class TimelineEditorScreen extends StatefulWidget {
  final ItineraryDraft draft;

  const TimelineEditorScreen({super.key, required this.draft});

  @override
  State<TimelineEditorScreen> createState() => _TimelineEditorScreenState();
}

class _TimelineEditorScreenState extends State<TimelineEditorScreen> {
  late List<TimelineStop> _stops;
  final _picker = ImagePicker();
  bool _isProcessing = false;

  @override
  void initState() {
    super.initState();
    _stops = List.from(widget.draft.stops);
    if (_stops.isEmpty) {
      _pickInitialMedia();
    }
  }

  Future<void> _pickInitialMedia() async {
    final List<XFile> images = await _picker.pickMultiImage();
    if (images.isNotEmpty) {
      _processImages(images);
    }
  }

  Future<void> _processImages(List<XFile> images) async {
    setState(() => _isProcessing = true);
    
    List<Map<String, dynamic>> photoData = [];

    for (var image in images) {
      final bytes = await File(image.path).readAsBytes();
      final data = await readExifFromBytes(bytes);
      
      DateTime? timestamp;
      if (data.containsKey('Image DateTime')) {
        try {
          timestamp = DateFormat("yyyy:MM:dd HH:mm:ss").parse(data['Image DateTime']!.toString());
        } catch (_) {}
      }
      
      photoData.add({
        'path': image.path,
        'timestamp': timestamp ?? DateTime.now(),
      });
    }

    // Sort by time
    photoData.sort((a, b) => (a['timestamp'] as DateTime).compareTo(b['timestamp'] as DateTime));

    // Clustering: 60 min gap starts a new stop
    List<TimelineStop> newStops = [];
    if (photoData.isNotEmpty) {
      List<String> currentGroupPaths = [photoData[0]['path']];
      DateTime groupStart = photoData[0]['timestamp'];

      for (int i = 1; i < photoData.length; i++) {
        DateTime currentPhotoTime = photoData[i]['timestamp'];
        if (currentPhotoTime.difference(groupStart).inMinutes.abs() < 60) {
          currentGroupPaths.add(photoData[i]['path']);
        } else {
          // Finish previous group
          newStops.add(TimelineStop(
            id: DateTime.now().millisecondsSinceEpoch.toString() + i.toString(),
            name: 'Suggested Stop ${newStops.length + 1}',
            photoPaths: List.from(currentGroupPaths),
            timestamp: groupStart,
          ));
          // Start new group
          currentGroupPaths = [photoData[i]['path']];
          groupStart = currentPhotoTime;
        }
      }
      // Add last group
      newStops.add(TimelineStop(
        id: DateTime.now().millisecondsSinceEpoch.toString() + 'final',
        name: 'Suggested Stop ${newStops.length + 1}',
        photoPaths: List.from(currentGroupPaths),
        timestamp: groupStart,
      ));
    }

    setState(() {
      _stops.addAll(newStops);
      _isProcessing = false;
    });
  }

  void _addStop() {
    setState(() {
      _stops.add(TimelineStop(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        name: 'New Stop',
        timestamp: _stops.isEmpty 
            ? DateTime.now() 
            : _stops.last.timestamp?.add(const Duration(hours: 2)),
      ));
    });
  }

  void _editStop(int index) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => StopDetailSheet(
        stop: _stops[index],
        onSave: (updatedStop) {
          setState(() {
            _stops[index] = updatedStop;
          });
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: AppColors.textPrimary),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          'Day Timeline',
          style: GoogleFonts.playfairDisplay(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w700,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () {
              // TODO: Complete and save itinerary
            },
            child: Text(
              'Save',
              style: GoogleFonts.playfairDisplay(
                color: AppColors.orange,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
      body: _isProcessing 
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(color: AppColors.orange),
                  SizedBox(height: 16),
                  Text('Analyzing your photos...', style: TextStyle(fontWeight: FontWeight.w600)),
                  Text('Generating your timeline suggestions...', style: TextStyle(color: Colors.grey, fontSize: 12)),
                ],
              ),
            )
          : _stops.isEmpty
              ? _buildEmptyState()
              : ReorderableListView.builder(
              padding: const EdgeInsets.fromLTRB(24, 0, 24, 100),
              itemCount: _stops.length,
              onReorder: (oldIndex, newIndex) {
                setState(() {
                  if (newIndex > oldIndex) newIndex -= 1;
                  final item = _stops.removeAt(oldIndex);
                  _stops.insert(newIndex, item);
                });
              },
              itemBuilder: (context, index) {
                return _buildTimelineItem(index);
              },
            ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _addStop,
        backgroundColor: AppColors.orange,
        icon: const Icon(Icons.add, color: Colors.white),
        label: Text(
          'Add Stop',
          style: GoogleFonts.playfairDisplay(color: Colors.white, fontWeight: FontWeight.w600),
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.photo_library_outlined, size: 64, color: Colors.grey[300]),
          const SizedBox(height: 16),
          Text(
            'Start by adding photos',
            style: GoogleFonts.playfairDisplay(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: Colors.grey[400],
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _pickInitialMedia,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.orange,
              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 12),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: Text(
              'Select Media',
              style: GoogleFonts.playfairDisplay(color: Colors.white, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimelineItem(int index) {
    final stop = _stops[index];
    final isLast = index == _stops.length - 1;

    return KeyedSubtree(
      key: ValueKey(stop.id),
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Timeline Line
            Column(
              children: [
                Container(
                  width: 12,
                  height: 12,
                  decoration: const BoxDecoration(
                    color: AppColors.orange,
                    shape: BoxShape.circle,
                  ),
                ),
                if (!isLast)
                  Expanded(
                    child: Container(
                      width: 2,
                      color: AppColors.orange.withOpacity(0.3),
                    ),
                  ),
              ],
            ),
            const SizedBox(width: 24),

            // Card
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(bottom: 32),
                child: GestureDetector(
                  onTap: () => _editStop(index),
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.grey[50],
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: Colors.grey[200]!),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              stop.timestamp != null 
                                  ? '${stop.timestamp!.hour}:${stop.timestamp!.minute.toString().padLeft(2, '0')}' 
                                  : '--:--',
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                color: AppColors.orange,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const Icon(Icons.drag_handle, size: 20, color: Colors.grey),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          stop.name ?? 'New Stop',
                          style: GoogleFonts.playfairDisplay(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        if (stop.photoPaths.isNotEmpty) ...[
                          const SizedBox(height: 12),
                          SizedBox(
                            height: 60,
                            child: ListView.builder(
                              scrollDirection: Axis.horizontal,
                              itemCount: stop.photoPaths.length,
                              itemBuilder: (context, pIndex) {
                                return Container(
                                  width: 60,
                                  margin: const EdgeInsets.only(right: 8),
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(8),
                                    image: DecorationImage(
                                      image: FileImage(File(stop.photoPaths[pIndex])),
                                      fit: BoxFit.cover,
                                    ),
                                  ),
                                );
                              },
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
