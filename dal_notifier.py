import os
import requests
import openai
import supabase
from bs4 import BeautifulSoup
from supabase import create_client
from stagehand import Stagehand

# Load environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
EMAIL_TO = "design-partners@joinvara.com"

# Initialize clients
openai.api_key = OPENAI_API_KEY
supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Constants
DAL_LIST_URL = "https://www.health.ny.gov/facilities/adult_care/dear_administrator_letters/"
DAL_LINK_SELECTOR = "a:has-text('Dear Administrator Letter')"  # Adjust if necessary

def get_last_seen_url():
    result = supabase_client.table("dal_tracker").select("last_url").limit(1).execute()
    if result.data:
        return result.data[0]["last_url"]
    return None

def update_last_seen_url(new_url):
    supabase_client.table("dal_tracker").update({"last_url": new_url}).eq("id", 1).execute()

def get_latest_dal_url():
    stagehand = Stagehand()
    page = stagehand.page
    page.goto(DAL_LIST_URL)
    link = stagehand.get_attribute("a[href*='dear_administrator_letters']", "href", index=0)
    full_url = f"https://www.health.ny.gov{link}" if link.startswith("/") else link
    stagehand.close()
    return full_url

def extract_text_from_dal(url):
    stagehand = Stagehand()
    stagehand.goto(url)
    text = Stagehand.get_text("body")  # You can refine this selector
    stagehand.close()
    return text.strip()

def summarize_text(text):
    prompt = (
        "You are summarizing a government compliance letter for assisted living staff.\n\n"
        "Please provide a 3-5 bullet point TLDR summary of the following letter:\n\n"
        f"{text[:4000]}"  # Limit input size
    )

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return response['choices'][0]['message']['content']

def send_summary_email(summary, url):
    email_html = f"""
    <h2>New Dear Administrator Letter Posted</h2>
    <p><strong>Summary:</strong></p>
    <pre>{summary}</pre>
    <p><a href="{url}">Read the full letter here</a></p>
    """

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "from": "alerts@joinvara.com",
            "to": [EMAIL_TO],
            "subject": "New Dear Administrator Letter Available",
            "html": email_html
        }
    )

    if response.status_code != 200:
        print("Failed to send email:", response.text)
    else:
        print("✅ Email sent successfully")

# Main flow
def main():
    print("🔍 Checking for new DAL letter...")
    latest_url = get_latest_dal_url()
    last_seen_url = get_last_seen_url()

    if latest_url != last_seen_url:
        print(f"🆕 New letter found: {latest_url}")
        text = extract_text_from_dal(latest_url)
        summary = summarize_text(text)
        send_summary_email(summary, latest_url)
        update_last_seen_url(latest_url)
    else:
        print("✅ No new letters. All caught up.")

if __name__ == "__main__":
    main()
