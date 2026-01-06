import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../theme/plandit_design_system.dart';
import 'storyboard_models.dart';

class BookingOptionsSheet extends StatelessWidget {
  final VenueVariant venue;

  const BookingOptionsSheet({
    super.key,
    required this.venue,
  });

  @override
  Widget build(BuildContext context) {
    final hasBookingOptions = venue.opentableUrl != null || venue.resyUrl != null;

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: PlanditColors.accent.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(
                  Icons.restaurant_menu,
                  color: PlanditColors.accent,
                  size: 24,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Make a Reservation',
                      style: GoogleFonts.inter(
                        fontSize: 20,
                        fontWeight: FontWeight.w600,
                        color: PlanditColors.primaryText,
                      ),
                    ),
                    Text(
                      venue.name,
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        color: PlanditColors.secondaryText,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 24),
          
          if (!hasBookingOptions)
            _buildNoBookingAvailable(context)
          else ...[
            // OpenTable Option
            if (venue.opentableUrl != null)
              _buildPlatformOption(
                context,
                'OpenTable',
                'assets/opentable_icon.png',
                venue.opentableUrl!,
                const Color(0xFFDA3743),
              ),
            
            // Resy Option
            if (venue.resyUrl != null)
              _buildPlatformOption(
                context,
                'Resy',
                'assets/resy_icon.png',
                venue.resyUrl!,
                const Color(0xFFE94B3C),
              ),
          ],
          
          // Divider
          if (hasBookingOptions && venue.phone != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 16),
              child: Row(
                children: [
                  Expanded(child: Divider(color: Colors.grey.shade300)),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Text(
                      'or',
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: PlanditColors.secondaryText,
                      ),
                    ),
                  ),
                  Expanded(child: Divider(color: Colors.grey.shade300)),
                ],
              ),
            ),
          
          // Call Restaurant Option
          if (venue.phone != null)
            _buildCallOption(context, venue),
          
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _buildNoBookingAvailable(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(
        children: [
          Icon(
            Icons.info_outline,
            color: Colors.grey.shade600,
            size: 32,
          ),
          const SizedBox(height: 12),
          Text(
            'Online booking not available',
            style: GoogleFonts.inter(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: PlanditColors.primaryText,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Please call the restaurant directly to make a reservation',
            style: GoogleFonts.inter(
              fontSize: 14,
              color: PlanditColors.secondaryText,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildPlatformOption(
    BuildContext context,
    String platform,
    String iconAsset,
    String url,
    Color brandColor,
  ) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () async {
            try {
              await launchUrl(
                Uri.parse(url),
                mode: LaunchMode.externalApplication,
              );
              if (context.mounted) Navigator.pop(context);
            } catch (e) {
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('Could not open $platform'),
                    backgroundColor: Colors.red,
                  ),
                );
              }
            }
          },
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              border: Border.all(color: Colors.grey.shade300),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                // Platform Icon
                Container(
                  width: 48,
                  height: 48,
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: brandColor.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Image.asset(
                    iconAsset,
                    errorBuilder: (context, error, stackTrace) {
                      // Fallback to icon if image not found
                      return Icon(
                        Icons.restaurant,
                        color: brandColor,
                        size: 24,
                      );
                    },
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Book on $platform',
                        style: GoogleFonts.inter(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: PlanditColors.primaryText,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Opens in $platform app or website',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          color: PlanditColors.secondaryText,
                        ),
                      ),
                    ],
                  ),
                ),
                Icon(
                  Icons.arrow_forward_ios,
                  size: 16,
                  color: Colors.grey.shade400,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildCallOption(BuildContext context, VenueVariant venue) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () async {
          final phoneUrl = 'tel:${venue.phone}';
          try {
            await launchUrl(Uri.parse(phoneUrl));
            if (context.mounted) Navigator.pop(context);
          } catch (e) {
            if (context.mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Could not make call'),
                  backgroundColor: Colors.red,
                ),
              );
            }
          }
        },
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.grey.shade50,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.grey.shade300),
                ),
                child: Icon(
                  Icons.phone,
                  color: Colors.grey.shade700,
                  size: 20,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Call Restaurant',
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: PlanditColors.primaryText,
                      ),
                    ),
                    Text(
                      venue.phone ?? '',
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: PlanditColors.secondaryText,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.phone_forwarded,
                size: 18,
                color: Colors.grey.shade400,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
