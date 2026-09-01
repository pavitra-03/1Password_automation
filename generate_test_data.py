import asyncio
import os
import time
from playwright.async_api import async_playwright
from onepassword import Client

DOMAIN_URL = os.getenv("DOMAIN_URL", "https://proton12.1password.com")
EMAIL = os.getenv("EMAIL", "admin@proton12.com")
MASTER_PASSWORD = os.getenv("MASTER_PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY")
SERVICE_ACCOUNT_TOKEN = os.getenv("OP_SERVICE_ACCOUNT_TOKEN")
VAULT_ID = os.getenv("VAULT_ID")

# --- USE CASE 2: Sign-in Attempts (Playwright Headless Browser) ---
async def generate_signin_events():
    print("[1/2] Triggering Sign-in Attempts...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Failed Sign-in Attempt
        try:
            await page.goto(f"{DOMAIN_URL}/signin")
            await page.fill('input[type="email"]', EMAIL)
            await page.fill('input[type="password"]', "WrongPassword123!")
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Failed attempt warning: {e}")

        # Successful Sign-in Attempt
        try:
            await page.goto(f"{DOMAIN_URL}/signin")
            await page.fill('input[type="email"]', EMAIL)
            if await page.locator('input[name="secretKey"]').is_visible():
                await page.fill('input[name="secretKey"]', SECRET_KEY)
            await page.fill('input[type="password"]', MASTER_PASSWORD)
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"Successful attempt warning: {e}")

        await browser.close()
    print(" -> Sign-in attempt actions completed.")

# --- USE CASE 1 & 3: Item Usages & Audit Events (1Password SDK) ---
async def generate_item_and_audit_events():
    print("[2/2] Triggering Item Usages & Audit Events...")
    if not SERVICE_ACCOUNT_TOKEN:
        print("Skipping SDK step: OP_SERVICE_ACCOUNT_TOKEN missing.")
        return

    client = await Client.authenticate(
        auth=SERVICE_ACCOUNT_TOKEN,
        integration_name="Automated Test Generator",
        integration_version="v1.0.0"
    )

    timestamp = int(time.time())
    
    # Use existing vault if provided, otherwise create a temporary test vault
    target_vault_id = VAULT_ID
    created_vault = None
    
    if not target_vault_id or target_vault_id == "dummy":
        created_vault = await client.vaults.create(title=f"Auto-Vault-{timestamp}")
        target_vault_id = created_vault.id

    # Create Item (Generates Audit & Item Usage Events)
    item = await client.items.create(
        vault_id=target_vault_id,
        title=f"Auto-Test-Item-{timestamp}",
        category="LOGIN",
        fields=[
            {"id": "username", "type": "STRING", "value": f"test_user_{timestamp}"},
            {"id": "password", "type": "CONCEALED", "value": "SecurePass123!"}
        ]
    )

    # Read Item (Generates Item Usage Event)
    _ = await client.items.get(target_vault_id, item.id)

    # Clean Up
    await client.items.delete(target_vault_id, item.id)
    if created_vault:
        await client.vaults.delete(created_vault.id)
        
    print(" -> Item Usages & Audit events completed.")

async def main():
    await generate_signin_events()
    await generate_item_and_audit_events()

if __name__ == "__main__":
    asyncio.run(main())
