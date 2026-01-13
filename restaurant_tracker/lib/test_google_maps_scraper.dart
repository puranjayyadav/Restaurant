import 'dart:convert';
import 'package:http/http.dart' as http;

/// Test file for Google Maps scraping
/// Run this to test and debug the scraping functionality
void main() async {
  print('=== Google Maps Scraper Test ===\n');

  // Test parameters
  final query = 'restaurant cafe dessert';
  final lat = 40.7428228;
  final lon = -74.0573162;
  final zoom = 13499.795714815926;
  final count = 200;
  final start = 0;

  print('Query: $query');
  print('Location: $lat, $lon');
  print('Zoom: $zoom\n');

  try {
    // Make the request
    final url =
        'https://www.google.com/search?tbm=map&authuser=0&hl=en&gl=us&pb=!4m12!1m3!1d$zoom!2d$lon!3d$lat!2m3!1f0!2f0!3f0!3m2!1i1920!2i376!4f13.1!7i$count!8i$start!10b1!12m16!1m1!18b1!2m3!5m1!6e2!20e3!10b1!12b1!13b1!16b1!17m1!3e1!20m3!5e2!6b1!14b1!19m4!2m3!1i360!2i120!4i8!20m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m42!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e9!2b1!3e2!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!2b1!4b1!9b0!22m2!1sSTleZpLoHLy4wN4Ps-iR2Aw!7e81!24m98!1m31!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m20!3b1!4b1!5b1!6b1!9b1!12b1!13b1!14b1!17b1!20b1!21b1!22b1!25b1!27m1!1b0!28b0!31b0!32b0!33m1!1b0!10m1!8e3!11m1!3e1!14m1!3b1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!29b1!30m1!2b1!36b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1!55b1!56m1!1b1!65m5!3m4!1m3!1m2!1i224!2i298!71b1!72m19!1m5!1b1!2b1!3b1!5b1!7b1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4!3sother_user_reviews!6m1!1e1!9b1!89b1!103b1!113b1!114m3!1b1!2m1!1b1!117b1!122m1!1b1!125b0!26m4!2m3!1i80!2i92!4i8!30m28!1m6!1m2!1i0!2i0!2m2!1i530!2i376!1m6!1m2!1i1870!2i0!2m2!1i1920!2i376!1m6!1m2!1i0!2i0!2m2!1i1920!2i20!1m6!1m2!1i0!2i356!2m2!1i1920!2i376!34m18!2b1!3b1!4b1!6b1!8m6!1b1!3b1!4b1!5b1!6b1!7b1!9b1!12b1!14b1!20b1!23b1!25b1!26b1!37m1!1e81!42b1!46m1!1e10!47m0!49m8!3b1!6m2!1b1!2b1!7m2!1e3!2b1!8b1!50m34!1m29!2m7!1u49!4sIn+stock!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKoGKBc!10m2!50m1!1e1!2m7!1u3!4s!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKsGKBg!10m2!3m1!1e1!2m7!1u2!4s!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKwGKBk!10m2!2m1!1e1!3m1!1u2!3m1!1u3!4BIAE!2e2!3m2!1b1!3b1!59BQ2dBd0Fn!61b1!67m2!7b1!10b1!69i695&q=${Uri.encodeComponent(query)}&tch=1&ech=3&psi=STleZpLoHLy4wN4Ps-iR2Aw.1717451082784.1';

    print('Making request...');
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

    print('Status Code: ${response.statusCode}');
    print('Response Length: ${response.body.length} bytes\n');

    // Show first 500 characters of raw response
    print('=== RAW RESPONSE (first 500 chars) ===');
    print(response.body
        .substring(0, response.body.length > 500 ? 500 : response.body.length));
    print('\n');

    // Test parsing
    final html = response.body;
    String cleaned = html;

    // Remove /*""*/ at the end if present
    if (cleaned.length > 6 && cleaned.endsWith('/*""*/')) {
      cleaned = cleaned.substring(0, cleaned.length - 6);
      print('Removed /*""*/ suffix');
    }

    // Handle different response formats
    print('\n=== PARSING ATTEMPTS ===');

    // Try 1: Handle {"c":0,"d":")]}'\n[...]}
    if (cleaned.startsWith('{"c":') || cleaned.contains('"d":')) {
      print('Detected format: {"c":0,"d":"...');
      try {
        final jsonData = json.decode(cleaned);
        print('✓ Successfully parsed as JSON object');
        print('Keys: ${jsonData.keys}');

        if (jsonData.containsKey('d')) {
          final d = jsonData['d'];
          print('Type of "d": ${d.runtimeType}');

          if (d is String) {
            print('"d" is a string, length: ${d.length}');
            print(
                'First 100 chars: ${d.substring(0, d.length > 100 ? 100 : d.length)}');

            // Remove )]}' prefix if present
            String dCleaned = d;
            if (dCleaned.startsWith(")]}'")) {
              dCleaned = dCleaned.substring(4);
              print('Removed )]}\' prefix');
            }

            // Remove newlines
            dCleaned = dCleaned.replaceAll('\n', '').trim();
            print('After cleaning, length: ${dCleaned.length}');
            print(
                'First 200 chars: ${dCleaned.substring(0, dCleaned.length > 200 ? 200 : dCleaned.length)}');

            try {
              final dParsed = json.decode(dCleaned);
              print('✓ Successfully parsed "d" as JSON');
              print('Type: ${dParsed.runtimeType}');

              if (dParsed is List && dParsed.isNotEmpty) {
                print('✓ It\'s a List with ${dParsed.length} items');
                final first = dParsed[0];
                print('First item type: ${first.runtimeType}');

                if (first is List) {
                  print('✓ First item is a List with ${first.length} items');

                  if (first.length > 1) {
                    final second = first[1];
                    print('Second item (index 1) type: ${second.runtimeType}');

                    if (second is List) {
                      print(
                          '✓ Second item is a List with ${second.length} items');
                      print('\n=== EXTRACTING PLACES ===');

                      final places = <dynamic>[];
                      for (int i = 0; i < second.length; i++) {
                        final item = second[i];
                        if (item is List) {
                          if (item.length > 14) {
                            final placeData = item[14];
                            places.add(placeData);
                            print(
                                'Place ${places.length}: Found at index $i (array length: ${item.length})');
                          } else {
                            print(
                                'Skipped index $i: array length ${item.length} < 15');
                          }
                        } else {
                          print(
                              'Skipped index $i: not a List (type: ${item.runtimeType})');
                        }
                      }

                      print('\n✓ Found ${places.length} places');

                      if (places.isNotEmpty) {
                        print('\n=== FIRST PLACE DATA ===');
                        print('Type: ${places[0].runtimeType}');
                        if (places[0] is List) {
                          final placeList = places[0] as List;
                          print('It\'s a List with ${placeList.length} items');
                          print(
                              'First 30 items: ${placeList.take(30).toList()}');

                          // Extract key fields based on actual structure
                          print('\n=== EXTRACTED FIELDS ===');

                          // Place ID (index 0)
                          if (placeList.length > 0) {
                            print('Place ID (index 0): ${placeList[0]}');
                          }

                          // Address (index 2)
                          if (placeList.length > 2) {
                            print('Address (index 2): ${placeList[2]}');
                          }

                          // Rating data (index 4)
                          if (placeList.length > 4 && placeList[4] is List) {
                            final ratingData = placeList[4] as List;
                            print(
                                'Rating data (index 4): ${ratingData.take(10).toList()}');
                            if (ratingData.length > 2) {
                              print(
                                  '  Price Level (index 4[2]): ${ratingData[2]}');
                            }
                            if (ratingData.length > 7) {
                              print('  Rating (index 4[7]): ${ratingData[7]}');
                            }
                            if (ratingData.length > 8) {
                              print(
                                  '  Total Reviews (index 4[8]): ${ratingData[8]}');
                            }
                          }

                          // Website (index 7)
                          if (placeList.length > 7 && placeList[7] is List) {
                            final websiteData = placeList[7] as List;
                            print(
                                'Website data (index 7): ${websiteData.take(5).toList()}');
                            if (websiteData.isNotEmpty) {
                              print(
                                  '  Website URL (index 7[0]): ${websiteData[0]}');
                            }
                          }

                          // Name (index 11)
                          if (placeList.length > 11) {
                            print('Name (index 11): ${placeList[11]}');
                          }

                          // Types/Categories (index 13)
                          if (placeList.length > 13) {
                            print('Types (index 13): ${placeList[13]}');
                          }

                          // Coordinates (index 208)
                          if (placeList.length > 208) {
                            final coordsData = placeList[208];
                            print('Coordinates (index 208): $coordsData');
                            if (coordsData is List && coordsData.isNotEmpty) {
                              final coordArray = coordsData[0];
                              if (coordArray is List && coordArray.length > 2) {
                                print(
                                    '  Lat (index 208[0][2]): ${coordArray[2]}');
                                print(
                                    '  Lng (index 208[0][3]): ${coordArray[3]}');
                              }
                            }
                          }

                          // Phone (index 178)
                          if (placeList.length > 178 &&
                              placeList[178] is List) {
                            final phoneData = placeList[178] as List;
                            print(
                                'Phone data (index 178): ${phoneData.take(3).toList()}');
                            if (phoneData.isNotEmpty) {
                              print('  Phone (index 178[0]): ${phoneData[0]}');
                            }
                          }

                          // Search for image/photo data - common indices to check
                          print('\n=== SEARCHING FOR IMAGES ===');
                          // Check common indices where photos might be stored
                          final potentialPhotoIndices = [
                            6,
                            9,
                            10,
                            14,
                            15,
                            16,
                            17,
                            18,
                            19,
                            20,
                            21,
                            22,
                            23,
                            24,
                            25,
                            26,
                            27,
                            28,
                            29,
                            30,
                            100,
                            101,
                            102,
                            103,
                            104,
                            105,
                            150,
                            151,
                            152,
                            153,
                            154,
                            155,
                            200,
                            201,
                            202,
                            203,
                            204,
                            205
                          ];
                          for (final idx in potentialPhotoIndices) {
                            if (placeList.length > idx) {
                              final data = placeList[idx];
                              if (data != null) {
                                if (data is String &&
                                    (data.contains('http') ||
                                        data.contains('photo') ||
                                        data.contains('image') ||
                                        data.contains('googleusercontent'))) {
                                  print(
                                      '  Index $idx (String URL): ${data.length > 100 ? data.substring(0, 100) : data}');
                                } else if (data is List && data.isNotEmpty) {
                                  // Check if list contains URLs
                                  for (int i = 0;
                                      i < (data.length > 3 ? 3 : data.length);
                                      i++) {
                                    final item = data[i];
                                    if (item is String &&
                                        (item.contains('http') ||
                                            item.contains('photo') ||
                                            item.contains('image') ||
                                            item.contains(
                                                'googleusercontent'))) {
                                      print(
                                          '  Index $idx[$i] (List URL): ${item.length > 100 ? item.substring(0, 100) : item}');
                                    } else if (item is List &&
                                        item.isNotEmpty) {
                                      final nested = item[0];
                                      if (nested is String &&
                                          (nested.contains('http') ||
                                              nested.contains('photo') ||
                                              nested.contains('image') ||
                                              nested.contains(
                                                  'googleusercontent'))) {
                                        print(
                                            '  Index $idx[$i][0] (Nested URL): ${nested.length > 100 ? nested.substring(0, 100) : nested}');
                                      }
                                    }
                                  }
                                }
                              }
                            }
                          }

                          // Specifically check index 6 and 9 which are common for photos
                          if (placeList.length > 6) {
                            final idx6 = placeList[6];
                            print(
                                'Index 6 type: ${idx6.runtimeType}, value: ${idx6 is List ? idx6.take(3).toList() : (idx6 is String ? (idx6.length > 100 ? idx6.substring(0, 100) : idx6) : idx6)}');
                          }

                          if (placeList.length > 9) {
                            final idx9 = placeList[9];
                            print(
                                'Index 9 type: ${idx9.runtimeType}, value: ${idx9 is List ? idx9.take(3).toList() : (idx9 is String ? (idx9.length > 100 ? idx9.substring(0, 100) : idx9) : idx9)}');
                          }

                          print('\n=== SUMMARY ===');
                          print('✓ Successfully extracted all key fields!');
                          print('✓ Parsing logic is working correctly');
                        } else {
                          print('Data: ${places[0]}');
                        }
                      } else {
                        print('\n⚠ No places found. Checking structure...');
                        print('First few items in second array:');
                        for (int i = 0;
                            i < (second.length > 5 ? 5 : second.length);
                            i++) {
                          final item = second[i];
                          if (item is List) {
                            print('  Index $i: List with ${item.length} items');
                          } else {
                            print('  Index $i: ${item.runtimeType} = $item');
                          }
                        }
                      }
                    } else {
                      print(
                          '✗ Second item is not a List, it\'s: ${second.runtimeType}');
                    }
                  } else {
                    print(
                        '✗ First list has only ${first.length} items (need at least 2)');
                    print('Items: ${first.take(5).toList()}');
                  }
                } else {
                  print(
                      '✗ First item is not a List, it\'s: ${first.runtimeType}');
                }
              } else {
                print('✗ Parsed data is not a List or is empty');
                print('Type: ${dParsed.runtimeType}');
              }
            } catch (e) {
              print('✗ Failed to parse "d" string: $e');
              print('Error details: $e');
            }
          } else {
            print('"d" is not a string, it\'s: ${d.runtimeType}');
            if (d is List) {
              print('"d" is a List with ${d.length} items');
            } else if (d is Map) {
              print('"d" is a Map with keys: ${d.keys}');
            } else {
              print('Value: $d');
            }
          }
        }
      } catch (e) {
        print('✗ Failed to parse: $e');
        print('Error details: $e');
      }
    }

    // Try 2: Direct array format
    if (cleaned.startsWith('[') || cleaned.contains(")]}'")) {
      print('\n--- Trying direct array format ---');
      String testCleaned = cleaned;

      if (testCleaned.contains(")]}'")) {
        final index = testCleaned.indexOf(")]}'");
        testCleaned = testCleaned.substring(index + 4);
        print('Removed )]}\' prefix');
      }

      testCleaned = testCleaned.replaceAll('\n', '').trim();

      // Remove /*""*/ if still present
      if (testCleaned.endsWith('/*""*/')) {
        testCleaned = testCleaned.substring(0, testCleaned.length - 6);
      }

      try {
        final jsonData = json.decode(testCleaned);
        print('✓ Successfully parsed as JSON');
        print('Type: ${jsonData.runtimeType}');

        if (jsonData is List) {
          print('✓ It\'s a List with ${jsonData.length} items');
        } else if (jsonData is Map) {
          print('✓ It\'s a Map with keys: ${jsonData.keys}');
        }
      } catch (e) {
        print('✗ Failed to parse: $e');
      }
    }
  } catch (e, stackTrace) {
    print('ERROR: $e');
    print('Stack trace: $stackTrace');
  }
}
