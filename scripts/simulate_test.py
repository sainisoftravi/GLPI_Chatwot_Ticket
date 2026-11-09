import asyncio
import json
import httpx
import sys

BRIDGE_URL = "http://localhost:5050"

async def test_health():
    print("==================================================")
    print("1. Testing Bridge Healthcheck...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{BRIDGE_URL}/health")
            if resp.status_code == 200:
                print(f"✅ Bridge is online and healthy: {resp.json()}")
                return True
            else:
                print(f"❌ Bridge returned error: {resp.status_code} - {resp.text}")
                return False
    except Exception as e:
        print(f"❌ Could not connect to Bridge at {BRIDGE_URL}: {e}")
        return False

async def test_chatwoot_webhook_simulation():
    print("\n==================================================")
    print("2. Simulating Chatwoot WhatsApp #ticket escalation...")
    
    # Mock Chatwoot Webhook Payload for an employee needing IT support
    mock_payload = {
        "event": "message_created",
        "id": 9901,
        "content": "#ticket Our team cannot connect to the corporate VPN network. Error code 403.",
        "message_type": "incoming",
        "created_at": "2026-11-09T12:00:00Z",
        "conversation": {
            "id": 105,
            "account_id": 1,
            "status": "open",
            "labels": []
        },
        "meta": {
            "sender": {
                "id": 42,
                "name": "Sarah Connor",
                "phone_number": "+14155552671",
                "email": "sarah.connor@example.com"
            }
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{BRIDGE_URL}/webhook/chatwoot",
                json=mock_payload,
                headers={"Content-Type": "application/json"}
            )
            print(f"Response status: {resp.status_code}")
            print(f"Response body: {resp.json()}")
            if resp.status_code == 200:
                print("✅ Bridge accepted webhook and queued GLPI ticket creation.")
            else:
                print("❌ Bridge rejected the payload.")
    except Exception as e:
        print(f"❌ Request failed: {e}")

async def test_glpi_resolution_simulation():
    print("\n==================================================")
    print("3. Simulating GLPI Ticket Resolution Notification to WhatsApp...")

    mock_glpi_payload = {
        "ticket_id": 101,
        "status": "Solved",
        "solution": "Firewall IP rule updated. VPN connection restored for all users.",
        "chatwoot_conversation_id": 105
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{BRIDGE_URL}/webhook/glpi",
                json=mock_glpi_payload,
                headers={"Content-Type": "application/json"}
            )
            print(f"Response status: {resp.status_code}")
            print(f"Response body: {resp.json()}")
            if resp.status_code == 200:
                print("✅ Bridge processed GLPI ticket resolution update.")
    except Exception as e:
        print(f"❌ Request failed: {e}")

async def main():
    healthy = await test_health()
    if healthy:
        await test_chatwoot_webhook_simulation()
        await asyncio.sleep(1)
        await test_glpi_resolution_simulation()
    else:
        print("\nEnsure the bridge container is running via:")
        print("  docker compose up -d bridge")

if __name__ == "__main__":
    asyncio.run(main())
