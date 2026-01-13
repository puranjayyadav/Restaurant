import { scrapeReviewsByPlaceId } from './final_scraper.js';

console.log('🧪 Testing place_id-based scraping\n');

// Test with a known place_id (Google Sydney office)
const testPlaceId = 'ChIJN1t_tDeuEmsRUsoyG83frY4';

console.log(`Testing with place_id: ${testPlaceId}\n`);

scrapeReviewsByPlaceId(testPlaceId, 3)
    .then(reviews => {
        if (reviews.length === 0) {
            console.log('\n❌ No reviews found');
            console.log('This might mean:');
            console.log('  1. The place has no reviews');
            console.log('  2. Google Maps layout changed');
            console.log('  3. The place_id is invalid\n');
            return;
        }

        console.log(`\n✅ SUCCESS! Scraped ${reviews.length} reviews using place_id\n`);

        const avgLength = reviews.reduce((sum, r) => sum + r.length, 0) / reviews.length;
        console.log(`📊 Average review length: ${Math.round(avgLength)} characters`);

        if (avgLength > 150) {
            console.log('✅ Reviews are fully expanded!\n');
        }
    })
    .catch(err => {
        console.error('\n❌ Test failed:', err.message);
    });
