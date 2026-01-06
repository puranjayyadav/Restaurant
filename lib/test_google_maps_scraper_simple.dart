import 'dart:convert';
import 'package:http/http.dart' as http;

/// Simplified test to find image indices
void main() async {
  print('=== Searching for Images in Google Maps Response ===\n');

  final query = 'restaurant cafe dessert';
  final lat = 40.7428228;
  final lon = -74.0573162;
  final zoom = 13499.795714815926;
  final count = 200;
  final start = 0;

  final url =
      'https://www.google.com/search?tbm=map&authuser=0&hl=en&gl=us&pb=!4m12!1m3!1d$zoom!2d$lon!3d$lat!2m3!1f0!2f0!3f0!3m2!1i1920!2i376!4f13.1!7i$count!8i$start!10b1!12m16!1m1!18b1!2m3!5m1!6e2!20e3!10b1!12b1!13b1!16b1!17m1!3e1!20m3!5e2!6b1!14b1!19m4!2m3!1i360!2i120!4i8!20m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m42!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e9!2b1!3e2!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!2b1!4b1!9b0!22m2!1sSTleZpLoHLy4wN4Ps-iR2Aw!7e81!24m98!1m31!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m20!3b1!4b1!5b1!6b1!9b1!12b1!13b1!14b1!17b1!20b1!21b1!22b1!25b1!27m1!1b0!28b0!31b0!32b0!33m1!1b0!10m1!8e3!11m1!3e1!14m1!3b1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!29b1!30m1!2b1!36b1!39m3!2m4!1m3!1m2!1i224!2i298!71b1!72m19!1m5!1b1!2b1!3b1!5b1!7b1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4!3sother_user_reviews!6m1!1e1!9b1!89b1!103b1!113b1!114m3!1b1!2m1!1b1!117b1!122m1!1b1!125b0!26m4!2m3!1i80!2i92!4i8!30m28!1m6!1m2!1i0!2i0!2m2!1i530!2i376!1m6!1m2!1i1870!2i0!2m2!1i1920!2i376!1m6!1m2!1i0!2i0!2m2!1i1920!2i20!1m6!1m2!1i0!2i356!2m2!1i1920!2i376!34m18!2b1!3b1!4b1!6b1!8m6!1b1!3b1!4b1!5b1!6b1!7b1!9b1!12b1!14b1!20b1!23b1!25b1!26b1!37m1!1e81!42b1!46m1!1e10!47m0!49m8!3b1!6m2!1b1!2b1!7m2!1e3!2b1!8b1!50m34!1m29!2m7!1u49!4sIn+stock!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKoGKBc!10m2!50m1!1e1!2m7!1u3!4s!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKsGKBg!10m2!3m1!1e1!2m7!1u2!4s!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKwGKBk!10m2!2m1!1e1!3m1!1u2!3m1!1u3!4BIAE!2e2!3m2!1b1!3b1!59BQ2dBd0Fn!61b1!67m2!7b1!10b1!69i695&q=${Uri.encodeComponent(query)}&tch=1&ech=3&psi=STleZpLoHLy4wN4Ps-iR2Aw.1717451082784.1';

  final response = await http.get(
    Uri.parse(url),
    headers: {
      'User-Agent':
          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.114 Safari/537.36',
      'Accept': '*/*',
      'Accept-Language': 'en-US,en;q=0.9',
      'Referer': 'https://www.google.com/',
      'Referrer-Policy': 'origin',
    },
  );

  if (response.statusCode != 200) {
    print('Error: ${response.statusCode}');
    return;
  }

  String cleaned = response.body;
  if (cleaned.endsWith('/*""*/')) {
    cleaned = cleaned.substring(0, cleaned.length - 6);
  }

  final jsonData = json.decode(cleaned);
  if (jsonData is Map && jsonData.containsKey('d')) {
    final d = jsonData['d'] as String;
    String dCleaned = d;
    if (dCleaned.startsWith(")]}'")) {
      dCleaned = dCleaned.substring(4);
    }
    dCleaned = dCleaned.replaceAll('\n', '').trim();

    final dParsed = json.decode(dCleaned);
    if (dParsed is List && dParsed.isNotEmpty) {
      final first = dParsed[0];
      if (first is List && first.length > 1) {
        final second = first[1];
        if (second is List && second.length > 1) {
          final place = second[1][14] as List; // Get first place

          print(
              'Searching for image URLs in place data (${place.length} items)...\n');

          final foundIndices = <int>[];

          for (int i = 0; i < place.length; i++) {
            final item = place[i];
            if (item == null) continue;

            bool found = false;
            String? url;

            if (item is String) {
              if (item.contains('googleusercontent') ||
                  item.contains('lh3.googleusercontent') ||
                  item.contains('maps.googleapis.com') ||
                  item.contains('maps/photo') ||
                  (item.contains('http') &&
                      (item.contains('.jpg') ||
                          item.contains('.png') ||
                          item.contains('photo')))) {
                found = true;
                url = item;
              }
            } else if (item is List) {
              for (final subItem in item) {
                if (subItem is String) {
                  if (subItem.contains('googleusercontent') ||
                      subItem.contains('lh3.googleusercontent') ||
                      subItem.contains('maps.googleapis.com') ||
                      subItem.contains('maps/photo') ||
                      (subItem.contains('http') &&
                          (subItem.contains('.jpg') ||
                              subItem.contains('.png') ||
                              subItem.contains('photo')))) {
                    found = true;
                    url = subItem;
                    break;
                  }
                } else if (subItem is List) {
                  for (final nested in subItem) {
                    if (nested is String &&
                        (nested.contains('googleusercontent') ||
                            nested.contains('maps.googleapis.com'))) {
                      found = true;
                      url = nested;
                      break;
                    }
                  }
                }
              }
            }

            if (found) {
              foundIndices.add(i);
              print(
                  '✓ Index $i: ${url!.length > 120 ? url.substring(0, 120) + "..." : url}');
            }
          }

          if (foundIndices.isEmpty) {
            print('⚠ No image URLs found in the response');
            print(
                'Images may need to be fetched separately using the place_id');
          } else {
            print('\n✓ Found images at indices: $foundIndices');
          }
        }
      }
    }
  }
}
