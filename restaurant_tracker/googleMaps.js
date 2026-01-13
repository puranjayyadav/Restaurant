import fetch from "node-fetch";
import { getSmartProxyAgent } from "./proxies.js";
import axios from "axios";
import fs from "graceful-fs";
import dotenv from "dotenv";
dotenv.config();

function prepare(input) {
  // There are 5 random characters before the JSON object we need to remove
  // Also I found that the newlines were messing up the JSON parsing,
  // so I removed those and it worked.
  const preparedForParsing = input.substring(5).replace(/\n/g, "");
  const json = JSON.parse(preparedForParsing);
  const results = json[0][1].map((array) => array[14]);
  return results;
}

function prepareLookup(data) {
  // this function takes a list of indexes as arguments
  // constructs them into a line of code and then
  // execs the retrieval in a try/catch to handle data not being present
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

function getHours(lookup) {
  const hoursArray = lookup(203, 0);
  if (!hoursArray) {
    return [];
  }

  return hoursArray.map((d) => {
    const day = d?.[0];
    const hours = d?.[3]?.[0]?.[0];
    const open24Hour = d?.[3]?.[0]?.[1]?.[0]?.[0];
    const close24Hour = d?.[3]?.[0]?.[1]?.[1]?.[0];
    return {
      day,
      hours,
      open24Hour: open24Hour || null,
      close24Hour: close24Hour || null,
    };
  });
}

// Helper function to recursively search for photo URLs
function findPhotoUrls(data, depth = 0, maxDepth = 5, maxPhotos = 10) {
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
        !data.includes('icon') &&
        !data.includes('default_user.png') &&
        !data.includes('avatar')) {
      photos.push(data.trim());
    }
  } else if (Array.isArray(data)) {
    for (const item of data) {
      if (photos.length >= maxPhotos) break;
      photos.push(...findPhotoUrls(item, depth + 1, maxDepth, maxPhotos));
    }
  } else if (data && typeof data === 'object') {
    for (const value of Object.values(data)) {
      if (photos.length >= maxPhotos) break;
      photos.push(...findPhotoUrls(value, depth + 1, maxDepth, maxPhotos));
    }
  }

  return photos;
}

function buildResults(preparedData) {
  const results = [];
  for (const place of preparedData) {
    const lookup = prepareLookup(place);
    const website = lookup(7, 0)?.replace("/url", "");
    const websiteWithoutQueryString = website?.split("?")?.[0];

    const name = lookup(11);
    const hours = getHours(lookup);

    const { lat, long } = getLatLong(lookup);

    // Extract photos - check known indices and do comprehensive search
    let photos = [];
    const maxPhotos = 10; // Increased from 4 to find more unique photos
    
    // Check known indices where photos might be stored
    const knownPhotoIndices = [6, 7, 8, 9, 10, 20, 21, 22, 23, 24, 25, 30, 31, 32, 33, 34, 35];
    for (const idx of knownPhotoIndices) {
      try {
        const data = lookup(idx);
        if (data) {
          const foundPhotos = findPhotoUrls(data, 0, 5, maxPhotos);
          photos.push(...foundPhotos);
          if (photos.length >= maxPhotos) break;
        }
      } catch (e) {
        // Ignore errors
      }
    }

    // If no photos found, do comprehensive search through first 200 indices
    if (photos.length === 0) {
      for (let idx = 0; idx < Math.min(place.length, 200); idx++) {
        try {
          const data = lookup(idx);
          if (data) {
            const foundPhotos = findPhotoUrls(data, 0, 5, maxPhotos);
            photos.push(...foundPhotos);
            if (photos.length >= maxPhotos) break;
          }
        } catch (e) {
          // Ignore errors
        }
      }
    }

    // Remove duplicates and filter out default profile photos
    const filteredPhotos = photos.filter(url => 
      !url.includes('default_user.png') &&
      !url.includes('logo') &&
      !url.includes('icon') &&
      !url.includes('avatar')
    );
    
    // Remove duplicates (exact matches)
    const uniquePhotos = [...new Set(filteredPhotos)].slice(0, 8).map(url => ({
      url: url,
      photo_url: url
    }));

    // Use the indexes below to extract certain pieces of data
    // or as a starting point of exploring the data response.
    const result = {
      street_address: lookup(183, 1, 2),
      city: lookup(183, 1, 3),
      zip: lookup(183, 1, 4),
      state: lookup(183, 1, 5),
      country_code: lookup(183, 1, 6),
      full_address: `${lookup(183, 1, 2)} ${lookup(183, 1, 3)} ${lookup(
        183,
        1,
        5
      )} ${lookup(183, 1, 4)} ${lookup(183, 1, 6)}`,
      website: websiteWithoutQueryString || "",
      avg_rating: lookup(4, 7),
      total_reviews: lookup(4, 8),
      name,
      tags: lookup(13),
      notes: lookup(25, 15, 0, 2),
      place_id: lookup(78),
      phone: lookup(178, 0, 0),
      lat,
      long,
      hours,
      photos: uniquePhotos, // Add photos array
    };
    results.push(result);
  }

  return results;
}

// enormous shout out to Joel for this code
// https://stackoverflow.com/questions/50964713/obtain-list-of-my-places-from-google-maps
// https://medium.com/serpapi/how-we-reverse-engineered-google-maps-pagination-18a6fe04f130

async function getGoogleMapsData(
  q,
  lat,
  long,
  zoom,
  count,
  start,
  retries = 0
) {
  try {
    const res = await fetch(
      `https://www.google.com/search?tbm=map&authuser=0&hl=en&gl=us&pb=!4m12!1m3!1d${zoom}!2d${long}!3d${lat}!2m3!1f0!2f0!3f0!3m2!1i1920!2i376!4f13.1!7i${count}!8i${start}!10b1!12m16!1m1!18b1!2m3!5m1!6e2!20e3!10b1!12b1!13b1!16b1!17m1!3e1!20m3!5e2!6b1!14b1!19m4!2m3!1i360!2i120!4i8!20m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m42!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e9!2b1!3e2!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!2b1!4b1!9b0!22m2!1sSTleZpLoHLy4wN4Ps-iR2Aw!7e81!24m98!1m31!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m20!3b1!4b1!5b1!6b1!9b1!12b1!13b1!14b1!17b1!20b1!21b1!22b1!25b1!27m1!1b0!28b0!31b0!32b0!33m1!1b0!10m1!8e3!11m1!3e1!14m1!3b1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!29b1!30m1!2b1!36b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1!55b1!56m1!1b1!65m5!3m4!1m3!1m2!1i224!2i298!71b1!72m19!1m5!1b1!2b1!3b1!5b1!7b1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4!3sother_user_reviews!6m1!1e1!9b1!89b1!103b1!113b1!114m3!1b1!2m1!1b1!117b1!122m1!1b1!125b0!26m4!2m3!1i80!2i92!4i8!30m28!1m6!1m2!1i0!2i0!2m2!1i530!2i376!1m6!1m2!1i1870!2i0!2m2!1i1920!2i376!1m6!1m2!1i0!2i0!2m2!1i1920!2i20!1m6!1m2!1i0!2i356!2m2!1i1920!2i376!34m18!2b1!3b1!4b1!6b1!8m6!1b1!3b1!4b1!5b1!6b1!7b1!9b1!12b1!14b1!20b1!23b1!25b1!26b1!37m1!1e81!42b1!46m1!1e10!47m0!49m8!3b1!6m2!1b1!2b1!7m2!1e3!2b1!8b1!50m34!1m29!2m7!1u49!4sIn+stock!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKoGKBc!10m2!50m1!1e1!2m7!1u3!4s!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKsGKBg!10m2!3m1!1e1!2m7!1u2!4s!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKwGKBk!10m2!2m1!1e1!3m1!1u2!3m1!1u3!4BIAE!2e2!3m2!1b1!3b1!59BQ2dBd0Fn!61b1!67m2!7b1!10b1!69i695&q=${encodeURIComponent(
        q
      )}&tch=1&ech=3&psi=STleZpLoHLy4wN4Ps-iR2Aw.1717451082784.1`,
      {
        agent: getSmartProxyAgent(),
        headers: {
          "User-Agent":
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.114 Safari/537.36",
          accept: "*/*",
          "accept-language": "en-US,en;q=0.9",
          priority: "u=1, i",
          "sec-ch-ua":
            '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
          "sec-ch-ua-arch": '"arm"',
          "sec-ch-ua-bitness": '"64"',
          "sec-ch-ua-full-version": '"125.0.6422.114"',
          "sec-ch-ua-full-version-list":
            '"Google Chrome";v="125.0.6422.114", "Chromium";v="125.0.6422.114", "Not.A/Brand";v="24.0.0.0"',
          "sec-ch-ua-mobile": "?0",
          "sec-ch-ua-model": '""',
          "sec-ch-ua-platform": '"macOS"',
          "sec-ch-ua-platform-version": '"13.0.1"',
          "sec-ch-ua-wow64": "?0",
          "sec-fetch-dest": "empty",
          "sec-fetch-mode": "cors",
          "sec-fetch-site": "same-origin",
          "x-client-data":
            "CJC2yQEIorbJAQipncoBCPP3ygEIk6HLAQiGoM0BCLvIzQEI6JPOAQiMlM4BCJiWzgEI1JjOARj2yc0BGKeIzgEY642lFw==",
          "x-goog-ext-353267353-jspb": "[null,null,null,147535]",
          "x-maps-diversion-context-bin": "CAE=",
          Referer: "https://www.google.com/",
          "Referrer-Policy": "origin",
        },
        body: null,
        method: "GET",
      }
    );
    const html = await res.text();
    // get rid of the /*""*/ at the end of the string
    const data = html.substring(0, html.length - 6);
    const json = JSON.parse(data);
    const preparedData = prepare(json.d);
    const listResults = buildResults(preparedData);
    return listResults;
  } catch (error) {
    if (retries < 3) {
      return getGoogleMapsData(q, lat, long, zoom, count, start, retries + 1);
    }
    console.log("error at getGoogleMapsData", error.message);
    return [];
  }
}

export async function googleMapsTextSearch(query) {
  try {
    const res = await axios({
      method: "get",
      url: `https://maps.googleapis.com/maps/api/place/textsearch/json?query=${encodeURIComponent(
        query
      )}&key=${process.env.GOOGLE_MAPS_API_KEY}`,
    });
    return res?.data?.results?.[0];
  } catch (error) {
    console.log("error at googleMapsTextSearch", error.message);
  }
}

export function getLongLatList(place, desiredGridLength = 5) {
  const northeastLat = place?.geometry.viewport.northeast.lat;
  const northeastLng = place?.geometry.viewport.northeast.lng;
  const southwestLat = place?.geometry.viewport.southwest.lat;
  const southwestLng = place?.geometry.viewport.southwest.lng;

  let output = [];
  let epsilon = 0.0000001; // because JavaScript and math don't get along
  // let epsilon = 0.1; // because JavaScript and math don't get along
  let intermediate_grid_length = desiredGridLength - 1;

  let lat_step_size = (northeastLat - southwestLat) / intermediate_grid_length;
  let lng_step_size = (northeastLng - southwestLng) / intermediate_grid_length;

  for (
    let lat = southwestLat;
    lat <= northeastLat + epsilon;
    lat += lat_step_size
  ) {
    for (
      let lng = southwestLng;
      lng <= northeastLng + epsilon;
      lng += lng_step_size
    ) {
      output.push([lat, lng]);
    }
  }
  return output;
}

(async () => {
  const location = "new york city";
  const place = await googleMapsTextSearch(location);
  const grid = getLongLatList(place, 15);
  console.log("grid.length", grid.length);

  const zoomLevels = [70000, 35000, 10000, 4000, 2000];
  const q = "coffee shop new york";
  let count = 200;
  let start = 0;
  let zoom = 13499.795714815926;

  const promises = [];

  for (let i = 0; i < grid.length; i++) {
    const [lat, long] = grid[i];
    // pushing into promises array to speed up
    promises.push(getGoogleMapsData(q, lat, long, zoom, count, start));
  }

  const allResults = await Promise.all(promises);

  // filtering out dupes
  const unique = new Set();

  const finalResults = allResults.reduce((acc, cur) => {
    cur.forEach((result) => {
      if (!unique.has(result.place_id)) {
        unique.add(result.place_id);
        acc.push(result);
      }
    });
    return acc;
  }, []);

  console.log("finalResults.length", finalResults.length);

  fs.writeFileSync(`./test.json`, JSON.stringify(finalResults, null, 2));
})();
