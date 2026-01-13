import puppeteer from 'puppeteer';
import fs from 'fs';

// Helper function to replace waitForTimeout
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function scrapeGoogleMapsReviews(placeUrl, maxReviews = 10) {
    const browser = await puppeteer.launch({
        headless: false, // Keep visible for debugging
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--start-maximized']
    });

    try {
        const page = await browser.newPage();

        // Set viewport and user agent
        await page.setViewport({ width: 1920, height: 1080 });
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

        console.log(`Navigating to: ${placeUrl}`);
        await page.goto(placeUrl, { waitUntil: 'networkidle2', timeout: 60000 });

        // Wait for the page to load
        await delay(5000);

        // Take a screenshot for debugging
        await page.screenshot({ path: 'debug_page.png', fullPage: false });
        console.log('Screenshot saved to debug_page.png');

        // Save HTML for debugging
        const html = await page.content();
        fs.writeFileSync('debug_page.html', html);
        console.log('HTML saved to debug_page.html');

        // Try to find and click Reviews tab
        try {
            // Wait for tabs to load
            await page.waitForSelector('button[role="tab"]', { timeout: 10000 });

            // Find all tabs
            const tabs = await page.$$('button[role="tab"]');
            console.log(`Found ${tabs.length} tabs`);

            for (const tab of tabs) {
                const text = await tab.evaluate(el => el.textContent);
                console.log(`Tab: ${text}`);
                if (text.includes('Reviews') || text.includes('review')) {
                    console.log('Clicking Reviews tab...');
                    await tab.click();
                    await delay(3000);
                    break;
                }
            }
        } catch (e) {
            console.log('Could not find/click Reviews tab:', e.message);
        }

        // Get average rating and review count
        let averageRating = null;
        let reviewCount = null;

        try {
            // Try multiple selectors for rating
            const ratingSelectors = [
                'div.fontDisplayLarge',
                'span.ceNzKf',
                'div[aria-label*="stars"]'
            ];

            for (const selector of ratingSelectors) {
                try {
                    averageRating = await page.$eval(selector, el => el.textContent.trim());
                    if (averageRating) {
                        console.log(`Average Rating: ${averageRating} (found with ${selector})`);
                        break;
                    }
                } catch (e) {
                    // Try next selector
                }
            }
        } catch (e) {
            console.log('Could not find average rating');
        }

        try {
            // Look for review count
            const allText = await page.evaluate(() => {
                const elements = Array.from(document.querySelectorAll('*'));
                return elements
                    .map(el => el.textContent)
                    .filter(text => text && text.includes('review'))
                    .slice(0, 10);
            });

            console.log('Elements containing "review":', allText);

            // Find the one that looks like a count
            for (const text of allText) {
                if (text.match(/\d+.*review/i)) {
                    reviewCount = text.trim();
                    console.log(`Review Count: ${reviewCount}`);
                    break;
                }
            }
        } catch (e) {
            console.log('Could not find review count');
        }

        // Scroll to load reviews
        console.log('Looking for review elements...');

        // Try multiple selectors for review containers
        const reviewSelectors = [
            '[data-review-id]',
            'div.jftiEf',
            'div.MyV7u',
            'div[jsaction*="review"]'
        ];

        let reviewElements = [];
        for (const selector of reviewSelectors) {
            reviewElements = await page.$$(selector);
            if (reviewElements.length > 0) {
                console.log(`Found ${reviewElements.length} review elements with selector: ${selector}`);
                break;
            }
        }

        if (reviewElements.length === 0) {
            console.log('No review elements found. Trying to scroll and wait...');

            // Try scrolling the main content area
            await page.evaluate(() => {
                const scrollable = document.querySelector('div[role="main"]');
                if (scrollable) {
                    scrollable.scrollBy(0, 500);
                }
            });

            await delay(2000);

            // Try again
            for (const selector of reviewSelectors) {
                reviewElements = await page.$$(selector);
                if (reviewElements.length > 0) {
                    console.log(`Found ${reviewElements.length} review elements after scroll with: ${selector}`);
                    break;
                }
            }
        }

        const reviews = [];

        for (let i = 0; i < Math.min(reviewElements.length, maxReviews); i++) {
            const reviewEl = reviewElements[i];

            try {
                // Try to expand review if there's a "More" button
                try {
                    const moreButton = await reviewEl.$('button[aria-label*="more" i]');
                    if (moreButton) {
                        await moreButton.click();
                        await delay(300);
                    }
                } catch (e) {
                    // No more button
                }

                // Extract all text from the review element
                const reviewData = await reviewEl.evaluate(el => {
                    // Get all text content
                    const allText = el.textContent;

                    // Try to find rating
                    const ratingEl = el.querySelector('span[aria-label*="star" i]');
                    const rating = ratingEl ? ratingEl.getAttribute('aria-label') : null;

                    // Try to find author
                    const authorEl = el.querySelector('button[aria-label]');
                    const author = authorEl ? authorEl.getAttribute('aria-label') : null;

                    // Get all spans (review text is usually in a span)
                    const spans = Array.from(el.querySelectorAll('span'));
                    const longTexts = spans
                        .map(s => s.textContent.trim())
                        .filter(t => t.length > 30);

                    return {
                        rating,
                        author,
                        allText: allText.substring(0, 500),
                        longTexts
                    };
                });

                // Pick the longest text as the review
                const text = reviewData.longTexts.length > 0
                    ? reviewData.longTexts.reduce((a, b) => a.length > b.length ? a : b)
                    : reviewData.allText;

                if (text && text.length > 20) {
                    reviews.push({
                        rating: reviewData.rating,
                        author: reviewData.author || 'Unknown',
                        text: text
                    });

                    console.log(`Scraped review ${reviews.length}: ${text.substring(0, 60)}...`);
                }
            } catch (e) {
                console.log(`Error scraping review ${i + 1}:`, e.message);
            }
        }

        const result = {
            placeUrl,
            averageRating,
            reviewCount,
            totalReviewsScraped: reviews.length,
            reviews
        };

        // Save to file
        fs.writeFileSync('puppeteer_reviews.json', JSON.stringify(result, null, 2));
        console.log(`\n✅ Scraped ${reviews.length} reviews successfully!`);
        console.log('📁 Saved to puppeteer_reviews.json');

        // Keep browser open for 5 seconds so you can see the result
        await delay(5000);

        return result;

    } catch (error) {
        console.error('❌ Error:', error.message);
        console.error('Stack:', error.stack);
        throw error;
    } finally {
        await browser.close();
    }
}

// Test with a coffee place in Jersey City
const testUrl = 'https://www.google.com/maps/place/Unnamed+Caf%C3%A9+-+coffee+shop+near+me+(St+Paul%27s+Ave)/@40.7376776,-74.0647566,17z';

console.log('🚀 Starting Google Maps Review Scraper...\n');
scrapeGoogleMapsReviews(testUrl, 10)
    .then(() => console.log('\n✅ Done!'))
    .catch(err => console.error('\n❌ Failed:', err.message));
