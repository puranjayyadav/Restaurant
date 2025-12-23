import puppeteer from 'puppeteer';
import fs from 'fs';

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Scrape reviews by searching for a place name
 * @param {string} placeName - Name of the place to search
 * @param {number} maxReviews - Maximum number of reviews to scrape
 * @returns {Promise<Array>} - Reviews data
 */
export async function scrapeReviewsBySearch(placeName, maxReviews = 5) {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1400, height: 900 });

        console.log(`🔍 Searching for: ${placeName}`);

        // Go to Google Maps
        await page.goto('https://www.google.com/maps', { waitUntil: 'networkidle2' });
        await delay(2000);

        // Search
        await page.waitForSelector('#searchboxinput');
        await page.type('#searchboxinput', placeName);
        await page.keyboard.press('Enter');
        await delay(4000);

        // Click first result
        const firstResult = await page.$('a[href*="/maps/place/"]');
        if (!firstResult) {
            console.log('❌ No results found');
            await browser.close();
            return [];
        }

        console.log('📍 Opening place details...');
        await firstResult.click();
        await delay(4000);

        // Click Reviews tab
        const buttons = await page.$$('button');
        for (const btn of buttons) {
            const text = await btn.evaluate(el => el.textContent);
            if (text && text.includes('Reviews')) {
                console.log('📋 Opening Reviews tab...');
                await btn.click();
                await delay(3000);
                break;
            }
        }

        // Scroll to load more reviews
        console.log('📜 Scrolling to load reviews...');
        const scrollableDiv = await page.evaluateHandle(() => {
            const divs = Array.from(document.querySelectorAll('div[role="main"] div'));
            return divs.find(div => div.scrollHeight > div.clientHeight);
        });

        if (scrollableDiv) {
            for (let i = 0; i < 3; i++) {
                await page.evaluate((div) => {
                    if (div) div.scrollBy(0, 500);
                }, scrollableDiv);
                await delay(1000);
            }
        }

        // Click "More" buttons to expand truncated reviews
        console.log('🔽 Expanding truncated reviews...');

        const moreButtons = await page.$$('button.w8nwRe.kyuRq[aria-label="See more"]');
        console.log(`   Found ${moreButtons.length} "More" buttons`);

        for (let i = 0; i < Math.min(moreButtons.length, maxReviews * 2); i++) {
            try {
                const btn = moreButtons[i];
                const isVisible = await btn.evaluate(el => {
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                });

                if (isVisible) {
                    await btn.click();
                    await delay(300);
                }
            } catch (e) {
                // Continue if button can't be clicked
            }
        }

        console.log('   Waiting for expanded content...');
        await delay(1500);

        // Extract reviews using the exact selectors
        console.log('📝 Extracting review data...');
        const reviewData = await page.evaluate(() => {
            const reviews = [];

            // Find all review containers
            const containers = document.querySelectorAll('div[data-review-id]');

            containers.forEach(container => {
                try {
                    // Get rating using the exact selector
                    const ratingEl = container.querySelector('span[aria-label*="star"]');
                    const ratingText = ratingEl ? ratingEl.getAttribute('aria-label') : null;

                    // Extract numeric rating
                    const ratingMatch = ratingText ? ratingText.match(/(\d+)/) : null;
                    const numericRating = ratingMatch ? parseInt(ratingMatch[1]) : null;

                    // Get review text using the exact class: span.wiI7pd
                    const reviewTextEl = container.querySelector('span.wiI7pd');
                    const reviewText = reviewTextEl ? reviewTextEl.textContent.trim() : '';

                    // Get author name
                    let author = 'Unknown';
                    try {
                        const authorButton = container.querySelector('button[aria-label]');
                        if (authorButton) {
                            const authorLabel = authorButton.getAttribute('aria-label');
                            // Extract name from "Photo of [Name]" format
                            author = authorLabel.replace('Photo of ', '').trim();
                        }
                    } catch (e) {
                        // Keep default
                    }

                    // Get date
                    let date = null;
                    try {
                        const dateEl = container.querySelector('span.rsqaWe');
                        date = dateEl ? dateEl.textContent.trim() : null;
                    } catch (e) {
                        // No date
                    }

                    // Only add if we have meaningful content
                    if (reviewText && reviewText.length > 20) {
                        reviews.push({
                            rating: numericRating,
                            ratingText: ratingText,
                            author: author,
                            date: date,
                            text: reviewText,
                            textLength: reviewText.length
                        });
                    }
                } catch (e) {
                    console.error('Error parsing review:', e);
                }
            });

            return reviews;
        });

        console.log(`✅ Extracted ${reviewData.length} reviews`);

        await browser.close();
        return reviewData.slice(0, maxReviews);

    } catch (error) {
        await browser.close();
        console.error('❌ Error scraping reviews:', error.message);
        return [];
    }
}

// CLI usage
if (import.meta.url === `file://${process.argv[1]}`) {
    const placeName = process.argv[2] || 'coffee shop Jersey City NJ';
    const maxReviews = parseInt(process.argv[3]) || 5;

    console.log(`\n${'='.repeat(60)}`);
    console.log(`  Google Maps Review Scraper`);
    console.log(`${'='.repeat(60)}\n`);

    scrapeReviewsBySearch(placeName, maxReviews)
        .then(reviews => {
            console.log(`\n${'='.repeat(60)}`);
            console.log(`  RESULTS`);
            console.log(`${'='.repeat(60)}\n`);

            if (reviews.length === 0) {
                console.log('❌ No reviews found\n');
                return;
            }

            reviews.forEach((review, i) => {
                console.log(`━━━ Review ${i + 1} of ${reviews.length} ━━━`);
                console.log(`👤 Author: ${review.author}`);
                console.log(`⭐ Rating: ${review.rating}/5`);
                console.log(`📅 Date: ${review.date || 'N/A'}`);
                console.log(`📏 Length: ${review.textLength} characters`);
                console.log(`📄 Text:\n${review.text}\n`);
            });

            fs.writeFileSync('reviews_output.json', JSON.stringify(reviews, null, 2));
            console.log(`💾 Saved ${reviews.length} reviews to reviews_output.json\n`);
        })
        .catch(err => {
            console.error('\n❌ Error:', err.message);
            console.error(err.stack);
        });
}
