import puppeteer from 'puppeteer';

console.log('🚀 Starting simple test...');

const placeId = process.argv[2] || 'ChIJpZd5uFtbwokROm9FtRhLhyQ';
const url = `https://www.google.com/maps/search/?api=1&query=Google&query_place_id=${placeId}`;

console.log(`📍 Place ID: ${placeId}`);
console.log(`🔗 URL: ${url}`);

const browser = await puppeteer.launch({
    headless: false,
    args: ['--no-sandbox']
});

const page = await browser.newPage();
console.log('✅ Browser opened');

await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
console.log('✅ Page loaded');

await new Promise(resolve => setTimeout(resolve, 10000));
console.log('⏸️  Waiting 10 seconds for you to see the page...');

await browser.close();
console.log('✅ Done!');
