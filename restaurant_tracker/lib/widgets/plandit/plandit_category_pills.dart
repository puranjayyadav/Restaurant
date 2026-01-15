import 'package:flutter/material.dart';
import '../../theme/plandit_design_system.dart';

class PlanditCategoryPills extends StatefulWidget {
  final Function(String query)? onCategorySelected;
  const PlanditCategoryPills({super.key, this.onCategorySelected});

  @override
  State<PlanditCategoryPills> createState() => _PlanditCategoryPillsState();
}

class _PlanditCategoryPillsState extends State<PlanditCategoryPills> {
  String _activeId = 'all';

  final List<Map<String, String>> _categories = [
    {'id': 'all', 'label': 'All'},
    {'id': 'brunch', 'label': 'Brunch'},
    {'id': 'date_night', 'label': 'Date Night'},
    {'id': 'coffee', 'label': 'Coffee'},
    {'id': 'rooftop', 'label': 'Rooftop'},
    {'id': 'cocktail_bar', 'label': 'Cocktail Bar'},
    {'id': 'hidden_gem', 'label': 'Hidden Gems'},
    {'id': 'omakase', 'label': 'Omakase'},
  ];

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 40,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: _categories.length,
        separatorBuilder: (context, index) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final cat = _categories[index];
          final isActive = _activeId == cat['id'];
          return GestureDetector(
            onTap: () {
              setState(() => _activeId = cat['id']!);
              if (cat['id'] != 'all' && widget.onCategorySelected != null) {
                widget.onCategorySelected!(cat['label']!);
              }
            },
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: isActive ? PlanditColors.primary : PlanditColors.secondary,
                borderRadius: BorderRadius.circular(100),
                boxShadow: isActive ? PlanditColors.shadowSoft : null,
              ),
              child: Center(
                child: Text(
                  cat['label']!,
                  style: TextStyle(
                    color: isActive
                        ? PlanditColors.primaryForeground
                        : PlanditColors.secondaryForeground,
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
