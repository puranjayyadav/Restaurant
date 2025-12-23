import puppeteer from 'puppeteer';
import fs from 'fs';

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function scrapeReviewsFromSearch(searchQuery, maxReviews = 5) {
    const browser = await puppeteer.launch({
        headless: false,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1400, height: 900 });

        console.log(`🔍 Searching for: ${searchQuery}`);

        // Go to Google Maps
        await page.goto('https://www.google.com/maps', { waitUntil: 'networkidle2' });
        await delay(2000);

        // Type in search box
        await page.waitForSelector('#searchboxinput');
        await page.type('#searchboxinput', searchQuery);
        await delay(1000);

        // Press Enter
        await page.keyboard.press('Enter');
        await delay(5000);

        // Take screenshot
        await page.screenshot({ path: 'search_results.png' });
        console.log('📸 Screenshot saved');

        // Click on the first result
        try {
            await page.waitForSelector('a[href*="/maps/place/"]', { timeout: 10000 });
            const firstResult = await page.$('a[href*="/maps/place/"]');

            if (firstResult) {
                console.log('📍 Clicking first place...');
                await firstResult.click();
                await delay(5000);

                // Take another screenshot
                await page.screenshot({ path: 'place_details.png' });
                console.log('📸 Place details screenshot saved');

                // Try to find Reviews button/tab
                const buttons = await page.$$('button');
                for (const btn of buttons) {
                    const text = await btn.evaluate(el => el.textContent);
                    if (text && (text.includes('Reviews') || text.includes('review'))) {
                        console.log(`🔘 Found button: ${text}`);
                        await btn.click();
                        await delay(3000);
                        break;
                    }
                }

                // Now try to extract reviews
                console.log('📝 Looking for reviews...');

                // Get page content and look for review-like structures
                const reviewData = await page.evaluate(() => {
                    const reviews = [];

                    // Look for elements that might contain reviews
                    const possibleReviewContainers = document.querySelectorAll('div[data-review-id], div.jftiEf, div[jsaction*="review"]');

                    console.log('Found containers:', possibleReviewContainers.length);

                    possibleReviewContainers.forEach((container, index) => {
                        try {
                            // Get all text
                            const text = container.textContent;

                            // Look for rating
                            const ratingEl = container.querySelector('[aria-label*="star"]');
                            const rating = ratingEl ? ratingEl.getAttribute('aria-label') : null;

                            // Look for spans with substantial text
                            const spans = Array.from(container.querySelectorAll('span'));
                            const reviewText = spans
                                .map(s => s.textContent.trim())
                                .filter(t => t.length > 50)
                                .join(' ');

                            if (reviewText || rating) {
                                reviews.push({
                                    rating,
                                    text: reviewText || text.substring(0, 200),
                                    index
                                });
                            }
                        } catch (e) {
                            console.error('Error extracting review:', e);
                        }
                    });

                    return reviews;
                });

                console.log(`✅ Found ${reviewData.length} potential reviews`);

                const result = {
                    searchQuery,
                    reviewsFound: reviewData.length,
                    reviews: reviewData.slice(0, maxReviews)
                };

                fs.writeFileSync('search_reviews.json', JSON.stringify(result, null, 2));
                console.log('💾 Saved to search_reviews.json');

                // Display first few reviews
                result.reviews.forEach((review, i) => {
                    console.log(`\n--- Review ${i + 1} ---`);
                    console.log(`Rating: ${review.rating || 'N/A'}`);
                    console.log(`Text: ${review.text.substring(0, 100)}...`);
                });

                await delay(3000);
                return result;
            }
        } catch (e) {
            console.error('❌ Error finding/clicking place:', e.message);
        }

    } catch (error) {
        console.error('❌ Error:', error.message);
    } finally {
        await browser.close();
    }
}

// Test with a coffee shop search
scrapeReviewsFromSearch('coffee shop Jersey City NJ', 5);
