import os
from stagehand import Browser
from supabase import create_client
from datetime import datetime
from urllib.parse import urljoin
import time

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Base URL
BASE_URL = "https://www.health.ny.gov"

# Step 1: Use Browserbase to scrape 2025 DAL links
def scrape_2025_dal_links():
    browser = Browser()
    browser.goto("https://www.health.ny.gov/facilities/adult_care/dear_administrator_letters/")
    browser.wait_for_selector("h2.expandable")

    # Expand the 2025 section if collapsed
    browser.click("h2.expandable.open:has-text('2025')")

    # Wait for links to load
    time.sleep(1)

    # Grab all <a> links inside the 2025 section
    links = browser.query_selector_all("h2:has-text('2025') + div li a")

    results = []
    for link in links:
        title = browser.get_text(link)
        relative_url = browser.get_attribute(link, "href")
        full_url = urljoin(BASE_URL, relative_url)
        results.append({
            "dal_title": title.strip(),
            "dal_url": full_url.strip(),
            "updated_at": datetime.utcnow().isoformat()
        })

    browser.close()
    return results

# Step 2: Write to Supabase
def insert_dals_to_supabase(dals):
    for dal in dals:
        # Avoid duplicates (optional: you can add constraints in Supabase too)
        existing = supabase.table("dal_tracker").select("*").eq("dal_url", dal["dal_url"]).execute()
        if not existing.data:
            print(f"📝 Inserting: {dal['dal_title']}")
            supabase.table("dal_tracker").insert(dal).execute()
        else:
            print(f"⚠️ Already exists: {dal['dal_title']}")

# Main flow
if __name__ == "__main__":
    print("🚀 Scraping 2025 Dear Administrator Letters...")
    dals = scrape_2025_dal_links()
    print(f"✅ Found {len(dals)} links. Inserting into Supabase...")
    insert_dals_to_supabase(dals)
    print("🎉 Done.")
