import asyncio
import os
import time
from playwright.async_api import async_playwright
from onepassword import Client
from onepassword.types import ItemCreateParams, ItemField, ItemCategory

DOMAIN_URL = os.getenv("DOMAIN_URL", "https://proton07.1password.com")
EMAIL = os.getenv("EMAIL", "Nitesh.Msinha@proton.me")
MASTER_PASSWORD = os.getenv("MASTER_PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY")
SERVICE_ACCOUNT_TOKEN = os.getenv("OP_SERVICE_ACCOUNT_TOKEN")
SHARED_VAULT_ID = os.getenv("SHARED_VAULT_ID")

# --- USE CASE 2: Sign-in Attempts (Playwright Headless Browser) ---
async def generate_signin_events():
    print("[1/2] Triggering Sign-in Attempts...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        page = await browser.new_page()

        # Step A: Failed Sign-in Attempt
        try:
            await page.goto(f"{DOMAIN_URL}/signin", wait_until="networkidle")
            await page.fill('input[type="email"]', EMAIL)
            await page.click('button:has-text("Next"), button[type="submit"]')
            await page.wait_for_selector('input[type="password"]', timeout=10000)

            await page.fill('input[type="password"]', "WrongPassword123!")
            await page.click('button:has-text("Sign in"), button[type="submit"]')
            await page.wait_for_timeout(3000)
            print(" -> Failed sign-in attempt triggered.")
        except Exception as e:
            print(f"Failed attempt step warning: {e}")

        # Step B: Successful Sign-in Attempt
        try:
            await page.goto(f"{DOMAIN_URL}/signin", wait_until="networkidle")
            await page.fill('input[type="email"]', EMAIL)
            await page.click('button:has-text("Next"), button[type="submit"]')
            await page.wait_for_selector('input[type="password"]', timeout=10000)

            secret_key_field = page.locator('input[name="secretKey"]')
            if await secret_key_field.is_visible():
                await secret_key_field.fill(SECRET_KEY)

            await page.fill('input[type="password"]', MASTER_PASSWORD)
            await page.click('button:has-text("Sign in"), button[type="submit"]')
            await page.wait_for_timeout(5000)
            print(" -> Successful sign-in attempt triggered.")
        except Exception as e:
            print(f"Successful attempt step warning: {e}")

        await browser.close()

# --- USE CASE 1 & 3: Item Usages & Audit Events (1Password SDK) ---
async def generate_item_and_audit_events():
    print("[2/2] Triggering Item Usages & Audit Events...")
    if not SERVICE_ACCOUNT_TOKEN or not SHARED_VAULT_ID:
        print("Skipping SDK step: OP_SERVICE_ACCOUNT_TOKEN or SHARED_VAULT_ID missing.")
        return

    client = await Client.authenticate(
        auth=SERVICE_ACCOUNT_TOKEN,
        integration_name="Automated Test Generator",
        integration_version="v1.0.0"
    )

    timestamp = int(time.time())

    new_item_params = ItemCreateParams(
        vault_id=SHARED_VAULT_ID,
        title=f"Auto-Test-Item-{timestamp}",
        category=ItemCategory.LOGIN,
        fields=[
            ItemField(id="username", label="username", value=f"test_user_{timestamp}"),
            ItemField(id="password", label="password", value="SecurePass123!")
        ]
    )

    # Create Item (Audit event)
    item = await client.items.create(new_item_params)
    print(f" -> Created test item: {item.id}")

    # Read Item (Item Usage event)
    _ = await client.items.get(SHARED_VAULT_ID, item.id)
    print(" -> Read test item field.")

    # Delete Item (Audit event)
    await client.items.delete(SHARED_VAULT_ID, item.id)
    print(" -> Deleted test item.")

async def main():
    await generate_signin_events()
    await generate_item_and_audit_events()

if __name__ == "__main__":
    asyncio.run(main())
