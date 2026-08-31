#!/usr/bin/env python3
"""
Trackr UK Finance internship monitor.
Scrapes the listing table, diffs against yesterday's snapshot,
and emails a summary if anything changed.
"""

import asyncio
import json
import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

URL = "https://app.the-trackr.com/uk-finance/summer-internships"
SNAPSHOT_FILE = Path("snapshot.json")
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT = os.environ.get("RECIPIENT_EMAIL", GMAIL_USER)


# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------

async def scrape() -> list[dict]:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle", timeout=60_000)

        # Dismiss sign-up modal if it appears (try Escape, then click the × button)
        try:
            await page.wait_for_selector("text=Create Your Account", timeout=5_000)
            await page.keyboard.press("Escape")
        except PlaywrightTimeoutError:
            pass  # No modal — fine
        except Exception:
            pass

        # Make sure the table is present
        await page.wait_for_selector("table tbody tr", timeout=20_000)

        listings = await page.evaluate("""() => {
            const rows = document.querySelectorAll('table tbody tr');
            const results = [];
            let currentCategory = '';

            for (const row of rows) {
                const cells = row.querySelectorAll('td');

                // Section header row (colspan 100)
                if (cells.length === 1) {
                    currentCategory = cells[0].textContent.trim().replace(/\\s+/g, ' ');
                    continue;
                }

                if (cells.length < 5) continue;

                const companyCell = cells[1];
                const programmeCell = cells[2];

                const companyName = companyCell.textContent.trim();
                const programmeName = programmeCell.textContent.trim();
                if (!companyName && !programmeName) continue;

                // Application link lives on the programme name anchor
                const programmeLink = programmeCell.querySelector('a');
                const applicationLink = programmeLink ? programmeLink.href : '';

                const companyLink = companyCell.querySelector('a');
                const companyUrl = companyLink ? companyLink.href : '';

                results.push({
                    category: currentCategory,
                    company: companyName,
                    programme: programmeName,
                    opening_date: cells[3] ? cells[3].textContent.trim() : '',
                    closing_date: cells[4] ? cells[4].textContent.trim() : '',
                    latest_stage: cells[5] ? cells[5].textContent.trim() : '',
                    sponsors_visa: cells[11] ? cells[11].textContent.trim() : '',
                    application_link: applicationLink,
                    company_url: companyUrl,
                });
            }
            return results;
        }""")

        await browser.close()
        return listings


# ---------------------------------------------------------------------------
# Diff logic
# ---------------------------------------------------------------------------

def make_key(listing: dict) -> str:
    return f"{listing['company']}|{listing['programme']}"


def diff(previous: list[dict], current: list[dict]) -> tuple[list[dict], list[dict]]:
    prev_map = {make_key(l): l for l in previous}
    curr_map = {make_key(l): l for l in current}

    new_listings = [l for k, l in curr_map.items() if k not in prev_map]

    newly_opened = [
        l for k, l in curr_map.items()
        if k in prev_map
        and not prev_map[k].get("opening_date")
        and l.get("opening_date")
    ]

    return new_listings, newly_opened


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def build_email(new_listings: list[dict], newly_opened: list[dict]) -> str:
    lines = [f"Trackr UK Finance update — {date.today()}\n"]

    if new_listings:
        lines.append("=== NEW LISTINGS ===\n")
        for l in new_listings:
            lines.append(f"  [{l['category']}] {l['company']} — {l['programme']}")
            lines.append(f"  Opens: {l['opening_date'] or 'TBC'}  |  Closes: {l['closing_date'] or 'TBC'}")
            if l["application_link"]:
                lines.append(f"  Apply: {l['application_link']}")
            lines.append("")

    if newly_opened:
        lines.append("=== NOW OPEN (previously closed/TBC) ===\n")
        for l in newly_opened:
            lines.append(f"  [{l['category']}] {l['company']} — {l['programme']}")
            lines.append(f"  Opened: {l['opening_date']}  |  Closes: {l['closing_date'] or 'TBC'}")
            if l["application_link"]:
                lines.append(f"  Apply: {l['application_link']}")
            lines.append("")

    return "\n".join(lines)


def send_email(body: str, new_count: int, opened_count: int) -> None:
    subject = f"[Trackr] {new_count} new listing(s), {opened_count} newly open — {date.today()}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, RECIPIENT, msg.as_string())

    print(f"Email sent: {subject}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    print(f"Scraping {URL} …")
    current = await scrape()
    print(f"  Found {len(current)} listings")

    previous = []
    if SNAPSHOT_FILE.exists():
        with SNAPSHOT_FILE.open() as f:
            previous = json.load(f)
        print(f"  Loaded {len(previous)} listings from previous snapshot")
    else:
        print("  No previous snapshot — saving baseline, no email sent")

    # Always save the updated snapshot
    with SNAPSHOT_FILE.open("w") as f:
        json.dump(current, f, indent=2)
    print(f"  Snapshot saved to {SNAPSHOT_FILE}")

    if not previous:
        return  # First run — nothing to diff against

    new_listings, newly_opened = diff(previous, current)
    print(f"  New listings: {len(new_listings)}, Newly opened: {len(newly_opened)}")

    if not new_listings and not newly_opened:
        print("  No changes detected — skipping email")
        return

    body = build_email(new_listings, newly_opened)
    send_email(body, len(new_listings), len(newly_opened))


if __name__ == "__main__":
    asyncio.run(main())
