import asyncio
import os
import time
from playwright.async_api import async_playwright
from onepassword import Client
from onepassword.types import ItemCreateParams, ItemField, ItemCategory, ItemFieldType, VaultCreateParams

DOMAIN_URL = os.getenv("DOMAIN_URL", "https://proton07.1password.com")
EMAIL = os.getenv("EMAIL", "Nitesh.Msinha@proton.me")
MASTER_PASSWORD = os.getenv("MASTER_PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY")
SERVICE_ACCOUNT_TOKEN = os.getenv("OP_SERVICE_ACCOUNT_TOKEN")

# --- USE CASE 2: Sign-in Attempts (Playwright Headless Browser) ---
async def generate_signin_events():
    print("[1/2] Triggering Sign-in Attempts...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        page = await browser.new_page()

        # Step A: Intentional Failed Sign-in Attempt
        try:
            await page.goto(f"{DOMAIN_URL}/signin", wait_until="networkidle")
            await page.wait_for_selector('input[type="email"]', timeout=10000)
            await page.fill('input[type="email"]', EMAIL)
            
            secret_key_field = page.locator('input[name="secretKey"], input[id="secret-key"]')
            if await secret_key_field.is_visible():
                await secret_key_field.fill(SECRET_KEY or "A3-XXXXXX-XXXXXX-XXXXX-XXXXX-XXXXX-XXXXX")

            password_field = page.locator('input[type="password"]')
            if await password_field.is_visible():
                await password_field.fill("WrongPassword123!")
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(3000)
                print(" -> Failed sign-in attempt triggered.")
        except Exception as e:
            print(f"Failed attempt step warning: {e}")

        # Step B: Successful Sign-in Attempt
        try:
            await page.goto(f"{DOMAIN_URL}/signin", wait_until="networkidle")
            await page.wait_for_selector('input[type="email"]', timeout=10000)
            await page.fill('input[type="email"]', EMAIL)

            secret_key_field = page.locator('input[name="secretKey"], input[id="secret-key"]')
            if await secret_key_field.is_visible() and SECRET_KEY:
                await secret_key_field.fill(SECRET_KEY)

            password_field = page.locator('input[type="password"]')
            if await password_field.is_visible() and MASTER_PASSWORD:
                await password_field.fill(MASTER_PASSWORD)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(5000)
                print(" -> Successful sign-in attempt triggered.")
        except Exception as e:
            print(f"Successful attempt step warning: {e}")

        await browser.close()

# --- USE CASE 1 & 3: Item Usages & Audit Events (1Password SDK) ---
async def generate_item_and_audit_events():
    print("[2/2] Triggering Item Usages & Audit Events...")
    if not SERVICE_ACCOUNT_TOKEN:
        print("Skipping SDK step: OP_SERVICE_ACCOUNT_TOKEN missing.")
        return

    try:
        client = await Client.authenticate(
            auth=SERVICE_ACCOUNT_TOKEN,
            integration_name="Automated Test Generator",
            integration_version="v1.0.0"
        )

        timestamp = int(time.time())

        # Create a temporary vault for testing
        test_vault = await client.vaults.create(
            VaultCreateParams(
                title=f"Test-Vault-{timestamp}",
                description="Automated Test Vault"
            )
        )
        print(f" -> Created test vault: {test_vault.id}")

        new_item_params = ItemCreateParams(
            vault_id=test_vault.id,
            title=f"Auto-Test-Item-{timestamp}",
            category=ItemCategory.LOGIN,
            fields=[
                ItemField(
                    id="username",
                    title="username",
                    field_type=ItemFieldType.TEXT,
                    value=f"test_user_{timestamp}"
                ),
                ItemField(
                    id="password",
                    title="password",
                    field_type=ItemFieldType.CONCEALED,
                    value="SecurePass123!"
                )
            ]
        )

        # 1. Create item (Audit event)
        item = await client.items.create(new_item_params)
        print(f" -> Created test item: {item.id}")

        # 2. Read item field (Item Usage event)
        _ = await client.items.get(test_vault.id, item.id)
        print(" -> Read test item field.")

        # 3. Delete item (Audit event)
        await client.items.delete(test_vault.id, item.id)
        print(" -> Deleted test item.")

        # 4. Delete test vault
        await client.vaults.delete(test_vault.id)
        print(" -> Cleaned up test vault.")

    except Exception as e:
        print(f"SDK Vault Action Warning: {e}")

async def main():
    await generate_signin_events()
    await generate_item_and_audit_events()

if __name__ == "__main__":
    asyncio.run(main())
