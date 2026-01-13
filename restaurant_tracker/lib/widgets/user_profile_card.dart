import 'package:flutter/material.dart';

class UserProfileCard extends StatelessWidget {
  final String userName;
  final String? userPhotoUrl;
  final int totalPublicItineraries;
  final int totalLikesReceived;

  const UserProfileCard({
    Key? key,
    required this.userName,
    this.userPhotoUrl,
    this.totalPublicItineraries = 0,
    this.totalLikesReceived = 0,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        // Profile Photo
        CircleAvatar(
          radius: 20,
          backgroundImage: userPhotoUrl != null && userPhotoUrl!.isNotEmpty
              ? NetworkImage(userPhotoUrl!)
              : null,
          child: userPhotoUrl == null || userPhotoUrl!.isEmpty
              ? Text(
                  userName.isNotEmpty ? userName[0].toUpperCase() : '?',
                  style: const TextStyle(fontSize: 18),
                )
              : null,
        ),
        const SizedBox(width: 12),
        // User Info
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                userName,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  _StatItem(
                    icon: Icons.list_alt,
                    value: totalPublicItineraries,
                    label: 'itineraries',
                  ),
                  const SizedBox(width: 16),
                  _StatItem(
                    icon: Icons.favorite,
                    value: totalLikesReceived,
                    label: 'likes',
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _StatItem extends StatelessWidget {
  final IconData icon;
  final int value;
  final String label;

  const _StatItem({
    Key? key,
    required this.icon,
    required this.value,
    required this.label,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: Colors.grey[600]),
        const SizedBox(width: 4),
        Text(
          '$value $label',
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
      ],
    );
  }
}
