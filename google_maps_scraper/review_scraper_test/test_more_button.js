import { scrapeReviewsBySearch } from './review_scraper.js';

console.log('🧪 Testing review scraper with "More" button expansion...\n');

const testPlace = 'Stumptown Coffee NYC';

scrapeReviewsBySearch(testPlace, 3)
    .then(reviews => {
        if (reviews.length === 0) {
            console.log('❌ No reviews found');
            return;
        }

        console.log(`\n✅ Successfully scraped ${reviews.length} reviews\n`);

        reviews.forEach((review, i) => {
            console.log(`━━━ Review ${i + 1} ━━━`);
            console.log(`⭐ Rating: ${review.rating}/5`);
            console.log(`📝 Text length: ${review.text.length} characters`);
            console.log(`📄 Preview: ${review.text.substring(0, 150)}...`);
            console.log('');
        });

        // Check if reviews are fully expanded
        const avgLength = reviews.reduce((sum, r) => sum + r.text.length, 0) / reviews.length;
        console.log(`📊 Average review length: ${Math.round(avgLength)} characters`);

        if (avgLength > 200) {
            console.log('✅ Reviews appear to be fully expanded!');
        } else {
            console.log('⚠️  Reviews might be truncated (average length is low)');
        }
    })
    .catch(err => {
        console.error('❌ Test failed:', err.message);
        console.error(err.stack);
    });
