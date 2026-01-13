import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/plandit_design_system.dart';

class Creator {
  final int id;
  final String name;
  final String avatar;
  final String metric;
  final int rank;

  Creator({
    required this.id,
    required this.name,
    required this.avatar,
    required this.metric,
    required this.rank,
  });
}

class PlanditCreatorLeaderboard extends StatelessWidget {
  PlanditCreatorLeaderboard({super.key});

  final List<Creator> creators = [
    Creator(
      id: 1,
      name: "Chloe K.",
      avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop&crop=face",
      metric: "24.5k Saves",
      rank: 1,
    ),
    Creator(
      id: 2,
      name: "Liam J.",
      avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop&crop=face",
      metric: "18.2k Saves",
      rank: 2,
    ),
    Creator(
      id: 3,
      name: "Maya R.",
      avatar: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200&h=200&fit=crop&crop=face",
      metric: "15.1k Saves",
      rank: 3,
    ),
    Creator(
      id: 4,
      name: "Vinna P.",
      avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&h=200&fit=crop&crop=face",
      metric: "12.8k Saves",
      rank: 4,
    ),
    Creator(
      id: 5,
      name: "Sofia L.",
      avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&h=200&fit=crop&crop=face",
      metric: "11.3k Saves",
      rank: 5,
    ),
    Creator(
      id: 6,
      name: "Marcus T.",
      avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&h=200&fit=crop&crop=face",
      metric: "9.7k Saves",
      rank: 6,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 20),
          child: Text(
            'Top NYC Creators',
            style: GoogleFonts.playfairDisplay(
              fontSize: 20,
              fontWeight: FontWeight.w400,
              color: PlanditColors.foreground,
            ),
          ),
        ),
        SizedBox(
          height: 140,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: creators.length,
            separatorBuilder: (context, index) => const SizedBox(width: 20),
            itemBuilder: (context, index) {
              final creator = creators[index];
              return _CreatorCard(creator: creator);
            },
          ),
        ),
      ],
    );
  }
}

class _CreatorCard extends StatelessWidget {
  final Creator creator;

  const _CreatorCard({required this.creator});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Stack(
          clipBehavior: Clip.none,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: PlanditColors.border.withOpacity(0.5), width: 2),
              ),
              child: Padding(
                padding: const EdgeInsets.all(2.0),
                child: CircleAvatar(
                  backgroundImage: NetworkImage(creator.avatar),
                ),
              ),
            ),
            if (creator.rank <= 3)
              Positioned(
                bottom: -4,
                right: -4,
                child: _RankBadge(rank: creator.rank),
              ),
          ],
        ),
        const SizedBox(height: 10),
        Text(
          creator.name,
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w300,
            color: PlanditColors.foreground,
          ),
        ),
        Text(
          creator.metric,
          style: const TextStyle(
            fontSize: 12,
            color: PlanditColors.mutedForeground,
          ),
        ),
      ],
    );
  }
}

class _RankBadge extends StatelessWidget {
  final int rank;

  const _RankBadge({required this.rank});

  @override
  Widget build(BuildContext context) {
    Color bg;
    List<BoxShadow> shadow;
    if (rank == 1) {
      bg = PlanditColors.rankGold;
      shadow = [
        BoxShadow(
          color: const Color(0xFFE6AC1A).withOpacity(0.4),
          blurRadius: 8,
          offset: const Offset(0, 2),
        )
      ];
    } else if (rank == 2) {
      bg = PlanditColors.rankSilver;
      shadow = [
        BoxShadow(
          color: const Color(0xFFB3B3B3).withOpacity(0.4),
          blurRadius: 8,
          offset: const Offset(0, 2),
        )
      ];
    } else {
      bg = PlanditColors.rankBronze;
      shadow = [
        BoxShadow(
          color: const Color(0xFFBF6F40).withOpacity(0.4),
          blurRadius: 8,
          offset: const Offset(0, 2),
        )
      ];
    }

    return Container(
      width: 28,
      height: 28,
      decoration: BoxDecoration(
        color: bg,
        shape: BoxShape.circle,
        boxShadow: shadow,
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          if (rank == 1)
            const Icon(
              Icons.workspace_premium, // Close enough to Crown
              size: 12,
              color: PlanditColors.primaryForeground,
            ),
          Text(
            rank.toString(),
            style: const TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.bold,
              color: PlanditColors.primaryForeground,
            ),
          ),
        ],
      ),
    );
  }
}
