import json
import time
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.myscheme.gov.in/search"

def extract_section(page, keyword):
    try:
        section = page.locator(f"text={keyword}")
        if section.count() > 0:
            parent = section.first.locator("xpath=..")
            return parent.inner_text()
    except:
        pass
    return None

def scrape():
    data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto(BASE_URL)
        page.wait_for_timeout(3000)

        schemes = []

        # Scroll to load schemes
        while len(schemes) < 200:
            page.mouse.wheel(0, 5000)
            time.sleep(2)
            schemes = page.query_selector_all("a[href*='/scheme/']")

        schemes = schemes[:200]

        links = []
        for s in schemes:
            href = s.get_attribute("href")
            if href:
                links.append("https://www.myscheme.gov.in" + href)

        print(f"Collected {len(links)} schemes")

        for idx, link in enumerate(links):
            print(f"Scraping {idx+1}/200")

            page.goto(link)
            page.wait_for_timeout(3000)

            scheme = {"url": link}

            # 🔹 Basic Info
            try:
                scheme["title"] = page.locator("h1").inner_text()
            except:
                scheme["title"] = None

            scheme["full_text"] = page.inner_text("body")

            # 🔹 Structured Sections
            scheme["application_process"] = extract_section(page, "Application Process")
            scheme["exclusions"] = extract_section(page, "Exclusions")
            scheme["benefits"] = extract_section(page, "Benefits")
            scheme["eligibility"] = extract_section(page, "Eligibility")

            # 🔥 Eligibility Questions
            questions = []
            try:
                btn = page.locator("text=Check Eligibility")
                if btn.count() > 0:
                    btn.click()
                    page.wait_for_timeout(2000)

                    q_elements = page.locator("label")
                    for i in range(q_elements.count()):
                        questions.append(q_elements.nth(i).inner_text())

            except:
                pass

            scheme["questions"] = questions

            data.append(scheme)

        browser.close()

    with open("myscheme_200_full.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    scrape()