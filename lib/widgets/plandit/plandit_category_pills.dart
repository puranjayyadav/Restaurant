import 'package:flutter/material.dart';
import '../../theme/plandit_design_system.dart';

class PlanditCategoryPills extends StatefulWidget {
  const PlanditCategoryPills({super.key});

  @override
  State<PlanditCategoryPills> createState() => _PlanditCategoryPillsState();
}

class _PlanditCategoryPillsState extends State<PlanditCategoryPills> {
  String _activeId = 'all';

  final List<Map<String, String>> _categories = [
    {'id': 'all', 'label': 'All'},
    {'id': 'asia', 'label': 'Asia'},
    {'id': 'europe', 'label': 'Europe'},
    {'id': 'africa', 'label': 'Africa'},
    {'id': 'americas', 'label': 'Americas'},
    {'id': 'oceania', 'label': 'Oceania'},
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
            onTap: () => setState(() => _activeId = cat['id']!),
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
