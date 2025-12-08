// Test script to run Google Maps scraper and check for photos
import fetch from "node-fetch";
import fs from "graceful-fs";
import { getSmartProxyAgent } from "./proxies.js";

function prepare(input) {
  const preparedForParsing = input.substring(5).replace(/\n/g, "");
  const json = JSON.parse(preparedForParsing);
  const results = json[0][1].map((array) => array[14]);
  return results;
}

function prepareLookup(data) {
  return function lookup(...indexes) {
    const indexesWithBrackets = indexes.reduce(
      (acc, cur) => `${acc}[${cur}]`,
      ""
    );
    const cmd = `data${indexesWithBrackets}`;
    try {
      const result = eval(cmd);
      return result;
    } catch (e) {
      return null;
    }
  };
}

function getLatLong(lookup) {
  let lat = lookup(208, 0, 2);
  if (!lat) {
    lat = lookup(37, 0, 0, 8, 0, 2);
  }
  let long = lookup(208, 0, 3);
  if (!long) {
    long = lookup(37, 0, 0, 8, 0, 1);
  }
  return {
    lat,
    long,
  };
}

// Helper function to recursively search for photo URLs
function findPhotoUrls(data, depth = 0, maxDepth = 5) {
  const photos = [];
  if (depth > maxDepth) return photos;

  if (typeof data === 'string') {
    // Check if it's a photo URL
    if ((data.includes('googleusercontent') ||
         data.includes('lh3.googleusercontent') ||
         data.includes('maps.googleapis.com') ||
         data.includes('maps/photo') ||
         data.includes('streetview') ||
         (data.startsWith('http') &&
          (data.includes('.jpg') ||
           data.includes('.jpeg') ||
           data.includes('.png') ||
           data.includes('photo') ||
           data.includes('image')))) &&
        !data.includes('logo') &&
        !data.includes('icon')) {
      photos.push(data.trim());
    }
  } else if (Array.isArray(data)) {
    for (const item of data) {
      if (photos.length >= 4) break;
      photos.push(...findPhotoUrls(item, depth + 1, maxDepth));
    }
  } else if (data && typeof data === 'object') {
    for (const value of Object.values(data)) {
      if (photos.length >= 4) break;
      photos.push(...findPhotoUrls(value, depth + 1, maxDepth));
    }
  }

  return photos;
}

function buildResults(preparedData) {
  const results = [];
  for (const place of preparedData) {
    if (!place || !Array.isArray(place)) {
      continue; // Skip invalid places
    }
    
    const lookup = prepareLookup(place);
    const website = lookup(7, 0)?.replace("/url", "");
    const websiteWithoutQueryString = website?.split("?")?.[0];

    const name = lookup(11);
    if (!name) {
      continue; // Skip places without names
    }
    
    const { lat, long } = getLatLong(lookup);

    // Extract photos - check known indices and do comprehensive search
    let photos = [];
    
    // Check known indices where photos might be stored
    const knownPhotoIndices = [6, 7, 8, 9, 10, 20, 21, 22, 23, 24, 25, 30, 31, 32, 33, 34, 35];
    for (const idx of knownPhotoIndices) {
      try {
        const data = lookup(idx);
        if (data) {
          const foundPhotos = findPhotoUrls(data, 0, 5);
          photos.push(...foundPhotos);
          if (photos.length >= 4) break;
        }
      } catch (e) {
        // Ignore errors
      }
    }

    // If no photos found, do comprehensive search through first 200 indices
    if (photos.length === 0 && place && Array.isArray(place)) {
      for (let idx = 0; idx < Math.min(place.length, 200); idx++) {
        try {
          const data = lookup(idx);
          if (data) {
            const foundPhotos = findPhotoUrls(data, 0, 5);
            photos.push(...foundPhotos);
            if (photos.length >= 4) break;
          }
        } catch (e) {
          // Ignore errors
        }
      }
    }

    // Remove duplicates and limit to 4
    const uniquePhotos = [...new Set(photos)].slice(0, 4).map(url => ({
      url: url,
      photo_url: url
    }));

    const result = {
      name,
      place_id: lookup(78),
      lat,
      long,
      photos: uniquePhotos,
      photos_count: uniquePhotos.length,
    };
    results.push(result);
  }

  return results;
}

async function testScraper() {
  try {
    // Test with New York coordinates
    const q = "restaurant";
    const lat = 40.7128;
    const lon = -74.0060;
    const zoom = 13499.795714815926;
    const count = 20;
    const start = 0;

    const url = `https://www.google.com/search?tbm=map&authuser=0&hl=en&gl=us&pb=!4m12!1m3!1d${zoom}!2d${lon}!3d${lat}!2m3!1f0!2f0!3f0!3m2!1i1920!2i376!4f13.1!7i${count}!8i${start}!10b1!12m16!1m1!18b1!2m3!5m1!6e2!20e3!10b1!12b1!13b1!16b1!17m1!3e1!20m3!5e2!6b1!14b1!19m4!2m3!1i360!2i120!4i8!20m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m42!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e9!2b1!3e2!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!2b1!4b1!9b0!22m2!1sSTleZpLoHLy4wN4Ps-iR2Aw!7e81!24m98!1m31!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m20!3b1!4b1!5b1!6b1!9b1!12b1!13b1!14b1!17b1!20b1!21b1!22b1!25b1!27m1!1b0!28b0!31b0!32b0!33m1!1b0!10m1!8e3!11m1!3e1!14m1!3b1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!29b1!30m1!2b1!36b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1!55b1!56m1!1b1!65m5!3m4!1m3!1m2!1i224!2i298!71b1!72m19!1m5!1b1!2b1!3b1!5b1!7b1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4!3sother_user_reviews!6m1!1e1!9b1!89b1!103b1!113b1!114m3!1b1!2m1!1b1!117b1!122m1!1b1!125b0!26m4!2m3!1i80!2i92!4i8!30m28!1m6!1m2!1i0!2i0!2m2!1i530!2i376!1m6!1m2!1i1870!2i0!2m2!1i1920!2i376!1m6!1m2!1i0!2i0!2m2!1i1920!2i20!1m6!1m2!1i0!2i356!2m2!1i1920!2i376!34m18!2b1!3b1!4b1!6b1!8m6!1b1!3b1!4b1!5b1!6b1!7b1!9b1!12b1!14b1!20b1!23b1!25b1!26b1!37m1!1e81!42b1!46m1!1e10!47m0!49m8!3b1!6m2!1b1!2b1!7m2!1e3!2b1!8b1!50m34!1m29!2m7!1u49!4sIn+stock!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKoGKBc!10m2!50m1!1e1!2m7!1u3!4s!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKsGKBg!10m2!3m1!1e1!2m7!1u2!4s!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKwGKBk!10m2!2m1!1e1!3m1!1u2!3m1!1u3!4BIAE!2e2!3m2!1b1!3b1!59BQ2dBd0Fn!61b1!67m2!7b1!10b1!69i695&q=${encodeURIComponent(q)}&tch=1&ech=3&psi=STleZpLoHLy4wN4Ps-iR2Aw.1717451082784.1`;

    console.log("Fetching Google Maps data...");
    console.log(`Query: ${q}, Location: ${lat}, ${lon}`);
    
    const res = await fetch(url, {
      agent: getSmartProxyAgent(),
      headers: {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.114 Safari/537.36",
        accept: "*/*",
        "accept-language": "en-US,en;q=0.9",
      },
    });

    const html = await res.text();
    console.log(`Response length: ${html.length}`);
    
    const data = html.substring(0, html.length - 6);
    const json = JSON.parse(data);
    
    if (!json.d) {
      console.error("No data in response. Response structure:", Object.keys(json));
      return;
    }
    
    const preparedData = prepare(json.d);
    console.log(`Prepared data length: ${preparedData ? preparedData.length : 0}`);
    
    if (!preparedData || preparedData.length === 0) {
      console.error("No places found in prepared data");
      return;
    }
    
    const listResults = buildResults(preparedData);

    console.log(`\n=== RESULTS ===`);
    console.log(`Total places found: ${listResults.length}\n`);

    // Analyze photo extraction
    const placesWithPhotos = listResults.filter(r => r.photos_count > 0);
    console.log(`Places with photos: ${placesWithPhotos.length}/${listResults.length}`);

    // Show first 5 places and their photo status
    console.log("\n=== First 5 Places ===");
    listResults.slice(0, 5).forEach((place, index) => {
      console.log(`\n${index + 1}. ${place.name}`);
      console.log(`   Place ID: ${place.place_id}`);
      console.log(`   Photos: ${place.photos_count}`);
      if (place.photos_count > 0) {
        place.photos.forEach((photo, pIndex) => {
          console.log(`   Photo ${pIndex + 1}: ${photo.url.substring(0, 80)}...`);
        });
      }
    });

    // Save results
    fs.writeFileSync(`./test_scraper_results.json`, JSON.stringify(listResults, null, 2));
    console.log(`\n=== Results saved to test_scraper_results.json ===`);

  } catch (error) {
    console.error("Error:", error.message);
    console.error(error.stack);
  }
}

testScraper();

