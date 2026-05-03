
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // 1. Visit dashboard
    await page.goto('http://localhost:5000/dashboard');
    
    // Wait for recommendations to load
    await page.waitForSelector('.sgc-apply');
    
    // 2. Click Apply on a scheme (Success case first)
    const applyBtns = await page.$$('.sgc-apply');
    if (applyBtns.length > 0) {
        await applyBtns[0].click();
        
        // Check for Benefit Advisor modal
        const advisorModal = await page.waitForSelector('#benefitAdvisorModal', { timeout: 5000 });
        if (advisorModal) {
            console.log("SUCCESS: Benefit Advisor modal appeared.");
            const title = await page.textContent('#adv-scheme-name');
            console.log("Scheme Name in Modal:", title);
        } else {
            console.log("FAILURE: Benefit Advisor modal did not appear.");
        }
    } else {
        console.log("FAILURE: No Apply buttons found.");
    }

  } catch (err) {
    console.error("Verification Error:", err);
  } finally {
    await browser.close();
  }
})();
