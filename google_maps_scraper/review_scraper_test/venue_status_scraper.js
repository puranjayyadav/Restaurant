import puppeteer from 'puppeteer-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';

puppeteer.use(StealthPlugin());

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function scrapeVenueStatus(placeId) {
    const browser = await puppeteer.launch({
        headless: false,
        slowMo: 50,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled'
        ]
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1400, height: 900 });

        // Initial load
        const url = `https://www.google.com/maps/search/?api=1&query=Venue&query_place_id=${placeId}`;
        console.error(`📍 URL: ${url}`);
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });

        // Wait 3 seconds then refresh as requested to load review count
        console.error('⏳ Waiting for initial load...');
        await delay(3000);
        console.error('🔄 Refreshing to ensure data load...');
        await page.reload({ waitUntil: 'networkidle2' });
        await delay(5000);

        // PHASE 1: Extract data that might change after clicking hours
        const initialData = await page.evaluate(() => {
            const data = {
                review_count: null,
                business_status: 'OPEN',
                raw_status: null,
                price_range: null,
                debug_label: null
            };

            // 1. Extract Review Count
            const reviewSelectors = [
                'span[role="img"][aria-label*="review"]',
                'button[aria-label*="review"]',
                'div[aria-label*="review"]'
            ];

            let reviewEl = null;
            for (const selector of reviewSelectors) {
                const elements = document.querySelectorAll(selector);
                for (const el of elements) {
                    const label = (el.getAttribute('aria-label') || el.textContent).toLowerCase();
                    if (label.includes('review') && !label.includes('write') && !label.includes('post')) {
                        reviewEl = el;
                        break;
                    }
                }
                if (reviewEl) break;
            }

            if (reviewEl) {
                const label = reviewEl.getAttribute('aria-label') || reviewEl.textContent;
                data.debug_label = label;
                const match = label.replace(/,/g, '').match(/(\d+)\s+review/i);
                if (match) {
                    data.review_count = parseInt(match[1]);
                } else {
                    const fallbackMatch = label.match(/([\d,]+)/);
                    if (fallbackMatch) {
                        data.review_count = parseInt(fallbackMatch[1].replace(/,/g, ''));
                    }
                }
            }

            // 2. Extract Closure Status
            const statusEl = document.querySelector('div.fontBodyMedium span span.fCEvvc');
            if (statusEl) {
                const statusText = statusEl.textContent.trim();
                data.raw_status = statusText;
                if (statusText.toLowerCase().includes('temporarily closed')) {
                    data.business_status = 'TEMPORARILY_CLOSED';
                } else if (statusText.toLowerCase().includes('permanently closed')) {
                    data.business_status = 'CLOSED_PERMANENTLY';
                }
            }

            // 3. Extract Price Range
            const priceSelectors = ['div.fontBodyMedium', 'span.fontBodyMedium'];
            for (const selector of priceSelectors) {
                const elements = document.querySelectorAll(selector);
                for (const el of elements) {
                    const text = el.textContent.trim();
                    if (text.includes('per person') && text.includes('$')) {
                        const match = text.match(/(\$[\d,]+[–-]?[\d,]*\s*per person)/i);
                        if (match) {
                            data.price_range = match[1];
                            break;
                        }
                    }
                }
                if (data.price_range) break;
            }

            return data;
        });

        console.error(`📊 Initial data: reviews=${initialData.review_count}, status=${initialData.business_status}`);

        // Click on "See more hours" to expand the full schedule
        try {
            const clicked = await page.evaluate(() => {
                // Target the "See more hours" link from user's HTML
                const seeMoreHours = document.querySelector('span.HlvSq');
                if (seeMoreHours) {
                    // Click on the parent clickable element
                    const clickableParent = seeMoreHours.closest('div.PbZDve') || seeMoreHours.closest('div');
                    if (clickableParent) {
                        clickableParent.click();
                        return true;
                    }
                }
                return false;
            });

            if (clicked) {
                console.error('📋 Clicked "See more hours"');
                await delay(2000); // Wait for table to expand
            } else {
                console.error('   ⚠️ Could not find "See more hours" link');
            }
        } catch (e) {
            console.error(`   ❌ Error expanding hours: ${e.message}`);
        }

        // PHASE 2: Extract hours after clicking
        const hoursData = await page.evaluate(() => {
            const hours = [];
            const hours_debug = { table_found: false, rows_found: 0 };

            // Target the specific table structure: table.eK4R0e > tbody > tr.y0skZc
            const hoursTable = document.querySelector('table.eK4R0e');
            if (hoursTable) {
                hours_debug.table_found = true;
                const rows = hoursTable.querySelectorAll('tbody tr.y0skZc');
                hours_debug.rows_found = rows.length;

                rows.forEach(row => {
                    const dayCell = row.querySelector('td.ylH6lf');
                    const hoursCell = row.querySelector('td.mxowUb');

                    if (dayCell && hoursCell) {
                        const dayDiv = dayCell.querySelector('div');
                        const day = dayDiv ? dayDiv.textContent.trim() : dayCell.textContent.trim();
                        const hoursText = hoursCell.getAttribute('aria-label') || hoursCell.textContent.trim();

                        hours.push({
                            day: day,
                            hours: hoursText
                        });
                    }
                });
            }

            return { hours, hours_debug };
        });

        // Merge initial data with hours data
        const result = {
            ...initialData,
            hours: hoursData.hours,
            hours_debug: hoursData.hours_debug
        };

        const screenshotName = `debug_venue_${placeId}.png`;
        await page.screenshot({ path: screenshotName });
        await browser.close();
        return result;

    } catch (error) {
        if (browser) await browser.close();
        return { error: error.message };
    }
}

const placeId = process.argv[2];
if (placeId) {
    scrapeVenueStatus(placeId).then(data => {
        console.log(JSON.stringify(data));
    });
}
