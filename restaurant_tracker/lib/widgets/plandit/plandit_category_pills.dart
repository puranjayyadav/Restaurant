import 'package:flutter/material.dart';
import '../../theme/plandit_design_system.dart';

class PlanditCategoryPills extends StatefulWidget {
  final Function(String query)? onCategorySelected;
  const PlanditCategoryPills({super.key, this.onCategorySelected});

  @override
  State<PlanditCategoryPills> createState() => _PlanditCategoryPillsState();
}

class _PlanditCategoryPillsState extends State<PlanditCategoryPills> {
  String _activeId = 'brunch';

  final List<Map<String, String>> _categories = [
    {'id': 'brunch', 'label': 'Brunch', 'emoji': '🍳'},
    {'id': 'date_night', 'label': 'Date Night', 'emoji': '🍷'},
    {'id': 'coffee', 'label': 'Coffee', 'emoji': '☕️'},
    {'id': 'rooftop', 'label': 'Rooftop', 'emoji': '🌇'},
    {'id': 'cocktail_bar', 'label': 'Cocktail Bar', 'emoji': '🍸'},
    {'id': 'mexican', 'label': 'Mexican', 'emoji': '🌮'},
    {'id': 'italian', 'label': 'Italian', 'emoji': '🍝'},
    {'id': 'sushi', 'label': 'Sushi', 'emoji': '🍣'},
    {'id': 'omakase', 'label': 'Omakase', 'emoji': '🍱'},
    {'id': 'dessert', 'label': 'Dessert', 'emoji': '🍦'},
    {'id': 'late_night', 'label': 'Late Night', 'emoji': '🌙'},
  ];

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 48, // Slightly taller for better touch targets and emojis
      child: ListView.separated(
        padding: const EdgeInsets.symmetric(vertical: 4),
        scrollDirection: Axis.horizontal,
        itemCount: _categories.length,
        separatorBuilder: (context, index) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final cat = _categories[index];
          final isActive = _activeId == cat['id'];
          return GestureDetector(
            onTap: () {
              final id = cat['id'];
              final label = cat['label'];
              if (id != null) {
                setState(() => _activeId = id);
                if (label != null && widget.onCategorySelected != null) {
                  widget.onCategorySelected!(label);
                }
              }
            },
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: isActive 
                  ? PlanditColors.primary 
                  : PlanditColors.secondary.withOpacity(0.8),
                borderRadius: BorderRadius.circular(100),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(isActive ? 0.15 : 0.08),
                    blurRadius: isActive ? 8 : 4,
                    offset: Offset(0, isActive ? 4 : 2),
                  ),
                ],
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    cat['emoji'] ?? '',
                    style: const TextStyle(fontSize: 14),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    cat['label'] ?? '',
                    style: TextStyle(
                      color: isActive
                          ? PlanditColors.primaryForeground
                          : PlanditColors.mutedForeground,
                      fontSize: 12,
                      fontWeight: isActive ? FontWeight.w700 : FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
