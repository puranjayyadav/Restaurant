import { scraper } from 'google-maps-review-scraper';
import fs from 'fs';

async function testReviewScraper() {
    try {
        console.log('Testing Google Maps Review Scraper...\n');

        // Test with Lackawanna Coffee (a place we know has reviews)
        const placeUrl = 'https://www.google.com/maps/place/LACKAWANNA+COFFEE/@40.718536,-74.0461748,18z';

        console.log(`Fetching reviews for: ${placeUrl}\n`);

        const reviews = await scraper(placeUrl, {
            sort_type: 'newest',  // Options: 'newest', 'highest_rating', 'lowest_rating', 'relevent'
            pages: 1,             // Number of pages to scrape
            clean: true           // Return clean/parsed reviews
        });

        if (reviews === 0 || reviews === undefined) {
            console.log('No reviews found or error occurred.');
            return;
        }

        console.log(`Found ${reviews.length} reviews:\n`);

        reviews.slice(0, 5).forEach((review, index) => {
            console.log(`--- Review ${index + 1} ---`);
            console.log(`Author: ${review.author || review.name || 'Unknown'}`);
            console.log(`Rating: ${review.rating || review.stars || 'N/A'}/5`);
            console.log(`Date: ${review.date || review.publishedAtDate || 'N/A'}`);
            console.log(`Text: ${review.text || review.snippet || 'No text'}`);
            console.log('');
        });

        // Save to JSON
        fs.writeFileSync('sample_reviews.json', JSON.stringify(reviews, null, 2));
        console.log(`\nSaved ${reviews.length} reviews to sample_reviews.json`);

    } catch (error) {
        console.error('Error:', error.message);
        console.error('Stack:', error.stack);
    }
}

testReviewScraper();
