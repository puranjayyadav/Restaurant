import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/plandit_design_system.dart';
import '../widgets/plandit/plandit_dashboard_header.dart';

class PlanditDashboardScreen extends StatelessWidget {
  const PlanditDashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.only(bottom: 120),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const PlanditDashboardHeader(),
          
          // Placeholder for other Dashboard components (AskAI, etc.)
          _buildPlaceholderSection(context, "Ask AI", "Your personal travel assistant"),
          _buildPlaceholderSection(context, "Neighborhoods", "Curated guides by area"),
          _buildPlaceholderSection(context, "Weekend Edit", "The best of the city this weekend"),
          _buildPlaceholderSection(context, "Upcoming Trip", "Ready for your next adventure?"),
        ],
      ),
    );
  }

  Widget _buildPlaceholderSection(BuildContext context, String title, String subtitle) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: GoogleFonts.playfairDisplay(
              fontSize: 24,
              fontWeight: FontWeight.w300,
              color: PlanditColors.foreground,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: const TextStyle(
              fontSize: 12,
              color: PlanditColors.mutedForeground,
            ),
          ),
          const SizedBox(height: 20),
          Container(
            height: 150,
            width: double.infinity,
            decoration: BoxDecoration(
              color: PlanditColors.secondary,
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Center(
              child: Icon(Icons.auto_awesome, color: PlanditColors.mutedForeground),
            ),
          ),
        ],
      ),
    );
  }
}
