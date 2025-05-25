import os
import time
from datetime import datetime
from urllib.parse import urljoin
from stagehand import Stagehand
from supabase import create_client

# Load environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Initialize Stagehand
stagehand = Stagehand(
    browserbase_api_key=BROWSERBASE_API_KEY,
    browserbase_project_id=BROWSERBASE_PROJECT_ID,
    model_name="gpt-4o"  # Adjust model if needed
)

BASE_URL = "https://www.health.ny.gov"
DAL_PAGE_URL = f"{BASE_URL}/facilities/adult_care/dear_administrator_letters/"

# Scrape 2025 DAL links
def scrape_2025_dal_links():
    page = stagehand.new_page()
    page.goto(DAL_PAGE_URL)
    page.wait_for_selector("h2.expandable")

    # Make sure the 2025 section is expanded
    header = page.query_selector("h2.expandable.open:has-text('2025')")
    if not header:
        # Try to click it if not already open
        header = page.query_selector("h2.expandable:has-text('2025')")
        if header:
            header.click()
            time.sleep(1)

    # Select all links under the 2025 section
    links = page.query_selector_all("h2:has-text('2025') + div li a")

    results = []
    for link in links:
        title = link.inner_text().strip()
        relative_url = link.get_attribute("href").strip()
        full_url = urljoin(BASE_URL, relative_url)
        results.append({
            "dal_title": title,
            "dal_url": full_url,
            "updated_at": datetime.utcnow().isoformat()
        })

    return results

# Insert new DALs into Supabase
def insert_dals_to_supabase(dals):
    for dal in dals:
        existing = supabase.table("dal_tracker").select("*").eq("dal_url", dal["dal_url"]).execute()
        if not existing.data:
            print(f"📝 Inserting: {dal['dal_title']}")
            supabase.table("dal_tracker").insert(dal).execute()
        else:
            print(f"⚠️ Already exists: {dal['dal_title']}")

# Main
if __name__ == "__main__":
    print("🚀 Scraping 2025 Dear Administrator Letters...")
    dals = scrape_2025_dal_links()
    print(f"✅ Found {len(dals)} links. Inserting into Supabase...")
    insert_dals_to_supabase(dals)
    print("🎉 Done.")
