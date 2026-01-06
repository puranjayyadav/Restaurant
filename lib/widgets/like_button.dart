import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../api_service.dart';

class LikeButton extends StatefulWidget {
  final String itineraryId;
  final int initialLikesCount;
  final bool initialLikedState;

  const LikeButton({
    Key? key,
    required this.itineraryId,
    required this.initialLikesCount,
    this.initialLikedState = false,
  }) : super(key: key);

  @override
  State<LikeButton> createState() => _LikeButtonState();
}

class _LikeButtonState extends State<LikeButton> {
  late bool _isLiked;
  late int _likesCount;
  bool _isLoading = false;
  final ApiService _apiService = ApiService();

  @override
  void initState() {
    super.initState();
    _isLiked = widget.initialLikedState;
    _likesCount = widget.initialLikesCount;
    _checkLikeStatus();
  }

  Future<void> _checkLikeStatus() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    try {
      final hasLiked = await _apiService.hasLikedItinerary(
        itineraryId: widget.itineraryId,
        userId: user.uid,
      );
      if (mounted) {
        setState(() {
          _isLiked = hasLiked;
        });
      }
    } catch (e) {
      print('ERROR: Failed to check like status: $e');
    }
  }

  Future<void> _toggleLike() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please sign in to like itineraries')),
      );
      return;
    }

    if (_isLoading) return;

    setState(() {
      _isLoading = true;
    });

    try {
      final result = await _apiService.likePublicItinerary(
        itineraryId: widget.itineraryId,
        userId: user.uid,
      );

      if (result != null && mounted) {
        setState(() {
          _isLiked = result['liked'] ?? false;
          _likesCount = result['likes_count'] ?? _likesCount;
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to toggle like: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: _isLoading ? null : _toggleLike,
      borderRadius: BorderRadius.circular(20),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _isLoading
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Icon(
                    _isLiked ? Icons.favorite : Icons.favorite_border,
                    color: _isLiked ? Colors.red : Colors.grey,
                    size: 20,
                  ),
            const SizedBox(width: 4),
            Text(
              _likesCount.toString(),
              style: TextStyle(
                fontSize: 14,
                color: _isLiked ? Colors.red : Colors.grey[700],
                fontWeight: _isLiked ? FontWeight.bold : FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
