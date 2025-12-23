import puppeteer from 'puppeteer';
import fs from 'fs';
import { fileURLToPath } from 'url';

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function debugPlaceId(placeId) {
    console.log(`\n🔍 DEBUG: Opening place with ID: ${placeId}`);

    const browser = await puppeteer.launch({
        headless: false,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1400, height: 900 });

        const url = `https://www.google.com/maps/search/?api=1&query=Google&query_place_id=${placeId}`;
        console.log(`📍 URL: ${url}\n`);

        await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
        await delay(5000);
        console.log('✅ Page loaded\n');

        // Take screenshot
        await page.screenshot({ path: 'debug_page.png', fullPage: false });
        console.log('📸 Screenshot saved to debug_page.png\n');

        // Find all buttons and log their text
        console.log('🔍 Looking for all buttons...');
        const buttonTexts = await page.evaluate(() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            return buttons.map(btn => btn.textContent.trim()).filter(text => text.length > 0);
        });

        console.log(`   Found ${buttonTexts.length} buttons:`);
        buttonTexts.slice(0, 20).forEach((text, i) => {
            console.log(`   ${i + 1}. "${text}"`);
        });

        // Check for tabs specifically
        console.log('\n🔍 Looking for tabs...');
        const tabs = await page.$$('button[role="tab"]');
        console.log(`   Found ${tabs.length} tabs`);

        for (let i = 0; i < tabs.length; i++) {
            const text = await tabs[i].evaluate(el => el.textContent.trim());
            const ariaLabel = await tabs[i].evaluate(el => el.getAttribute('aria-label'));
            console.log(`   Tab ${i + 1}: "${text}" (aria-label: "${ariaLabel}")`);
        }

        // Wait so you can see the browser
        console.log('\n⏸️  Keeping browser open for 15 seconds...');
        await delay(15000);

        await browser.close();
        console.log('✅ Done!');

    } catch (error) {
        console.error('❌ Error:', error.message);
        await browser.close();
    }
}

// Run
const placeId = process.argv[2] || 'ChIJN1t_tDeuEmsRUsoyG83frY4';

console.log(`\n${'='.repeat(60)}`);
console.log(`  DEBUG: Google Maps Place ID`);
console.log(`${'='.repeat(60)}`);

debugPlaceId(placeId);
