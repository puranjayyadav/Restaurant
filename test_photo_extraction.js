// Test script to manually check if photos are in the Google Maps scraping response
const fetch = require("node-fetch");
const fs = require("fs");

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

// Function to recursively search for photo URLs in the data structure
function findPhotoUrls(data, path = "", depth = 0, maxDepth = 5) {
  const photos = [];
  
  if (depth > maxDepth) return photos;
  
  if (typeof data === 'string') {
    // Check if it's a photo URL
    if (data.includes('googleusercontent') || 
        data.includes('lh3.googleusercontent') ||
        data.includes('maps.googleapis.com') ||
        data.includes('maps/photo') ||
        (data.startsWith('http') && (data.includes('.jpg') || data.includes('.png') || data.includes('photo')))) {
      photos.push({ path, url: data });
    }
  } else if (Array.isArray(data)) {
    data.forEach((item, index) => {
      const newPath = path ? `${path}[${index}]` : `[${index}]`;
      photos.push(...findPhotoUrls(item, newPath, depth + 1, maxDepth));
    });
  } else if (data && typeof data === 'object') {
    Object.keys(data).forEach(key => {
      const newPath = path ? `${path}.${key}` : key;
      photos.push(...findPhotoUrls(data[key], newPath, depth + 1, maxDepth));
    });
  }
  
  return photos;
}

async function testPhotoExtraction() {
  try {
    const q = "restaurant";
    const lat = 40.7128; // New York
    const lon = -74.0060;
    const zoom = 13499.795714815926;
    const count = 20;
    const start = 0;

    const url = `https://www.google.com/search?tbm=map&authuser=0&hl=en&gl=us&pb=!4m12!1m3!1d${zoom}!2d${lon}!3d${lat}!2m3!1f0!2f0!3f0!3m2!1i1920!2i376!4f13.1!7i${count}!8i${start}!10b1!12m16!1m1!18b1!2m3!5m1!6e2!20e3!10b1!12b1!13b1!16b1!17m1!3e1!20m3!5e2!6b1!14b1!19m4!2m3!1i360!2i120!4i8!20m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m42!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e9!2b1!3e2!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!2b1!4b1!9b0!22m2!1sSTleZpLoHLy4wN4Ps-iR2Aw!7e81!24m98!1m31!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m20!3b1!4b1!5b1!6b1!9b1!12b1!13b1!14b1!17b1!20b1!21b1!22b1!25b1!27m1!1b0!28b0!31b0!32b0!33m1!1b0!10m1!8e3!11m1!3e1!14m1!3b1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!29b1!30m1!2b1!36b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1!55b1!56m1!1b1!65m5!3m4!1m3!1m2!1i224!2i298!71b1!72m19!1m5!1b1!2b1!3b1!5b1!7b1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4!3sother_user_reviews!6m1!1e1!9b1!89b1!103b1!113b1!114m3!1b1!2m1!1b1!117b1!122m1!1b1!125b0!26m4!2m3!1i80!2i92!4i8!30m28!1m6!1m2!1i0!2i0!2m2!1i530!2i376!1m6!1m2!1i1870!2i0!2m2!1i1920!2i376!1m6!1m2!1i0!2i0!2m2!1i1920!2i20!1m6!1m2!1i0!2i356!2m2!1i1920!2i376!34m18!2b1!3b1!4b1!6b1!8m6!1b1!3b1!4b1!5b1!6b1!7b1!9b1!12b1!14b1!20b1!23b1!25b1!26b1!37m1!1e81!42b1!46m1!1e10!47m0!49m8!3b1!6m2!1b1!2b1!7m2!1e3!2b1!8b1!50m34!1m29!2m7!1u49!4sIn+stock!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKoGKBc!10m2!50m1!1e1!2m7!1u3!4s!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKsGKBg!10m2!3m1!1e1!2m7!1u2!4s!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKwGKBk!10m2!2m1!1e1!3m1!1u2!3m1!1u3!4BIAE!2e2!3m2!1b1!3b1!59BQ2dBd0Fn!61b1!67m2!7b1!10b1!69i695&q=${encodeURIComponent(q)}&tch=1&ech=3&psi=STleZpLoHLy4wN4Ps-iR2Aw.1717451082784.1`;

    console.log("Fetching Google Maps data...");
    const res = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.114 Safari/537.36",
        accept: "*/*",
        "accept-language": "en-US,en;q=0.9",
      },
    });

    const html = await res.text();
    const data = html.substring(0, html.length - 6);
    const json = JSON.parse(data);
    const preparedData = prepare(json.d);

    console.log(`\nFound ${preparedData.length} places\n`);

    // Analyze first place in detail
    if (preparedData.length > 0) {
      const firstPlace = preparedData[0];
      const lookup = prepareLookup(firstPlace);
      
      console.log("=== First Place Analysis ===");
      console.log("Name:", lookup(11));
      console.log("Place ID:", lookup(78));
      console.log("\n=== Searching for Photos ===");
      
      // Search for photo URLs in the entire data structure
      const photoUrls = findPhotoUrls(firstPlace);
      
      if (photoUrls.length > 0) {
        console.log(`\nFound ${photoUrls.length} potential photo URLs:`);
        photoUrls.forEach((photo, index) => {
          console.log(`\nPhoto ${index + 1}:`);
          console.log(`  Path: ${photo.path}`);
          console.log(`  URL: ${photo.url.substring(0, 100)}...`);
        });
      } else {
        console.log("No photo URLs found in the data structure.");
        console.log("\n=== Checking specific indices that might contain photos ===");
        
        // Check some common indices that might have photos
        const indicesToCheck = [6, 7, 8, 9, 10, 20, 21, 22, 23, 24, 25, 30, 31, 32, 33, 34, 35, 40, 41, 42, 43, 44, 45];
        for (const idx of indicesToCheck) {
          try {
            const value = lookup(idx);
            if (value) {
              console.log(`Index [${idx}]:`, typeof value === 'string' ? value.substring(0, 100) : Array.isArray(value) ? `Array[${value.length}]` : typeof value);
              if (typeof value === 'string' && (value.includes('http') || value.includes('photo') || value.includes('image'))) {
                console.log(`  ^^^ Potential photo-related data!`);
              }
            }
          } catch (e) {
            // Ignore
          }
        }
      }
      
      // Save full structure for analysis
      fs.writeFileSync('./test_place_structure.json', JSON.stringify(firstPlace, null, 2));
      console.log("\n=== Full place structure saved to test_place_structure.json ===");
    }
  } catch (error) {
    console.error("Error:", error.message);
    console.error(error.stack);
  }
}

testPhotoExtraction();

