import { scrapeReviewsBySearch } from './review_scraper.js';

console.log('🧪 Testing Google Maps Review Scraper\n');
console.log('This will scrape reviews with:');
console.log('  - Exact button selector: button.w8nwRe.kyuRq');
console.log('  - Exact text selector: span.wiI7pd\n');

const testPlace = 'Stumptown Coffee NYC';

scrapeReviewsBySearch(testPlace, 3)
    .then(reviews => {
        if (reviews.length === 0) {
            console.log('\n❌ No reviews extracted');
            console.log('This might mean:');
            console.log('  1. The selectors need adjustment');
            console.log('  2. The page structure changed');
            console.log('  3. Google detected automation\n');
            return;
        }

        console.log(`\n✅ SUCCESS! Scraped ${reviews.length} reviews\n`);

        reviews.forEach((review, i) => {
            console.log(`${'─'.repeat(60)}`);
            console.log(`Review ${i + 1}`);
            console.log(`${'─'.repeat(60)}`);
            console.log(`👤 ${review.author}`);
            console.log(`⭐ ${review.rating}/5 stars`);
            console.log(`📅 ${review.date || 'No date'}`);
            console.log(`📏 ${review.textLength} characters`);
            console.log(`\n"${review.text}"\n`);
        });

        // Check if reviews are fully expanded
        const avgLength = reviews.reduce((sum, r) => sum + r.textLength, 0) / reviews.length;
        console.log(`\n📊 Average review length: ${Math.round(avgLength)} characters`);

        if (avgLength > 150) {
            console.log('✅ Reviews appear to be fully expanded!');
        } else {
            console.log('⚠️  Reviews might still be truncated');
        }
    })
    .catch(err => {
        console.error('\n❌ Test failed:', err.message);
    });
