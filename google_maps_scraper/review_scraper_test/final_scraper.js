import puppeteer from 'puppeteer-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';
import fs from 'fs';
import { fileURLToPath } from 'url';

// Use stealth plugin to avoid detection
puppeteer.use(StealthPlugin());

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Scrape reviews using Google Maps place_id with stealth mode
 */
async function scrapeReviewsByPlaceId(placeId, maxReviews = 5) {
    console.log(`\n🔍 Opening place with ID: ${placeId}`);

    const browser = await puppeteer.launch({
        headless: false,  // Now works with stealth!
        slowMo: 50,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled'
        ]
    });

    try {
        const page = await browser.newPage();

        // Set realistic viewport
        await page.setViewport({ width: 1920, height: 1080 });

        // Set language and timezone
        await page.setExtraHTTPHeaders({
            'Accept-Language': 'en-US,en;q=0.9'
        });

        const url = `https://www.google.com/maps/search/?api=1&query=Google&query_place_id=${placeId}`;
        console.log(`📍 URL: ${url}\n`);

        await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
        await delay(3000);
        console.log('✅ Page loaded\n');

        // REFRESH TO LOAD REVIEWS
        console.log('🔄 Refreshing page to load reviews...');
        await delay(5000);
        console.log('✅ Page refreshed\n');

        // Scrape total review count from header (before clicking Reviews tab)
        let totalReviewCount = null;
        try {
            totalReviewCount = await page.evaluate(() => {
                const el = document.querySelector('span[role="img"][aria-label*="reviews"]');
                if (el) {
                    const label = el.getAttribute('aria-label');
                    const match = label.match(/([\d,]+)/);
                    return match ? parseInt(match[1].replace(/,/g, '')) : null;
                }
                return null;
            });
            console.log(`📊 Total reviews: ${totalReviewCount || 'Unknown'}\n`);
        } catch (e) {
            // Skip
        }

        // Click Reviews tab
        console.log('📋 Looking for Reviews tab...');
        const buttons = await page.$$('button');
        let foundReviews = false;

        for (const btn of buttons) {
            const text = await btn.evaluate(el => el.textContent);
            if (text && text.includes('Reviews')) {
                console.log('   ✅ Found Reviews tab, clicking...');
                await btn.click();
                await delay(3000);
                foundReviews = true;
                break;
            }
        }

        if (!foundReviews) {
            console.log('   ❌ Reviews tab not found');
            await browser.close();
            return [];
        }

        // Scroll
        console.log('📜 Scrolling...');
        for (let i = 0; i < 3; i++) {
            await page.evaluate(() => {
                const scrollable = document.querySelector('div[role="main"]');
                if (scrollable) scrollable.scrollBy(0, 500);
            });
            await delay(1000);
        }

        // Click "More" buttons
        console.log('🔽 Expanding reviews...');
        const moreButtons = await page.$$('button.w8nwRe.kyuRq[aria-label="See more"]');
        console.log(`   Found ${moreButtons.length} More buttons`);

        for (let i = 0; i < Math.min(moreButtons.length, 10); i++) {
            try {
                await moreButtons[i].click();
                await delay(200);
            } catch (e) {
                // Continue
            }
        }

        await delay(2000);

        // Extract reviews
        console.log('📝 Extracting reviews...\n');
        const reviews = await page.evaluate(() => {
            const results = [];
            const containers = document.querySelectorAll('div[data-review-id]');

            containers.forEach(container => {
                try {
                    const ratingEl = container.querySelector('span[aria-label*="star"]');
                    const ratingText = ratingEl ? ratingEl.getAttribute('aria-label') : null;
                    const ratingMatch = ratingText ? ratingText.match(/(\d+)/) : null;
                    const rating = ratingMatch ? parseInt(ratingMatch[1]) : null;

                    const textEl = container.querySelector('span.wiI7pd');
                    const text = textEl ? textEl.textContent.trim() : '';

                    const authorBtn = container.querySelector('button[aria-label]');
                    const author = authorBtn ? authorBtn.getAttribute('aria-label').replace('Photo of ', '') : 'Unknown';

                    if (text && text.length > 20) {
                        results.push({ author, rating, text, length: text.length });
                    }
                } catch (e) {
                    // Skip
                }
            });

            return results;
        });

        // Deduplicate
        const seen = new Set();
        const uniqueReviews = reviews.filter(review => {
            const key = `${review.author}:${review.text}`;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });

        console.log(`✅ Extracted ${reviews.length} reviews (${uniqueReviews.length} unique)\n`);

        // Display
        uniqueReviews.slice(0, maxReviews).forEach((review, i) => {
            console.log(`${'━'.repeat(60)}`);
            console.log(`Review ${i + 1}`);
            console.log(`${'━'.repeat(60)}`);
            console.log(`👤 ${review.author}`);
            console.log(`⭐ ${review.rating}/5`);
            console.log(`📏 ${review.length} chars`);
            console.log(`\n${review.text}\n`);
        });

        // Save
        const output = uniqueReviews.slice(0, maxReviews);
        fs.writeFileSync('final_reviews.json', JSON.stringify(output, null, 2));
        console.log(`💾 Saved ${output.length} reviews to final_reviews.json\n`);

        await delay(2000);
        await browser.close();
        return output;

    } catch (error) {
        console.error('❌ Error:', error.message);
        await browser.close();
        return [];
    }
}

// Run if called directly
import path from 'path';
const isMainModule = process.argv[1] && (
    path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))
);

if (isMainModule) {
    const placeId = process.argv[2];
    const maxReviews = parseInt(process.argv[3]) || 5;

    console.log(`\n${'='.repeat(60)}`);
    console.log(`  Google Maps Review Scraper - STEALTH MODE`);
    console.log(`${'='.repeat(60)}`);

    if (!placeId) {
        console.log('\n❌ Error: Please provide a place_id');
        console.log('\nUsage: node final_scraper_stealth.js <place_id> [max_reviews]');
        console.log('Example: node final_scraper_stealth.js "ChIJo4cQG05awokRvly8DkNX8ZU" 5\n');
        process.exit(1);
    }

    scrapeReviewsByPlaceId(placeId, maxReviews)
        .then(() => console.log('✅ Complete!'))
        .catch(err => console.error('❌ Failed:', err.message));
}

export { scrapeReviewsByPlaceId };
