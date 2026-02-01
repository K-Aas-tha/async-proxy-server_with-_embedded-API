"""
Test script for the asyncio proxy server.
"""

import asyncio
import aiohttp


async def test_api():
    """Test management API endpoints."""
    async with aiohttp.ClientSession() as session:
        base_url = "http://localhost:9000"
        
        print("Testing Health Endpoint...")
        async with session.get(f"{base_url}/health") as resp:
            print(f"Status: {resp.status}")
            print(f"Response: {await resp.json()}\n")
        
        print("Testing Config Endpoint...")
        async with session.get(f"{base_url}/config") as resp:
            print(f"Status: {resp.status}")
            print(f"Response: {await resp.json()}\n")
        
        print("Testing Stats Endpoint...")
        async with session.get(f"{base_url}/stats") as resp:
            print(f"Status: {resp.status}")
            print(f"Response: {await resp.json()}\n")
        
        print("Testing Config Update...")
        async with session.post(
            f"{base_url}/config",
            json={"max_connections": 150}
        ) as resp:
            print(f"Status: {resp.status}")
            print(f"Response: {await resp.json()}\n")


async def test_proxy():
    """Test proxy forwarding (requires target server on localhost:8000)."""
    async with aiohttp.ClientSession() as session:
        proxy_url = "http://localhost:8080"
        
        print("Testing Proxy Forwarding...")
        try:
            async with session.get(f"{proxy_url}/api/test") as resp:
                print(f"Status: {resp.status}")
                print(f"Response: {await resp.text()}\n")
        except aiohttp.ClientConnectorError:
            print("Target server not available on localhost:8000\n")


async def main():
    """Run all tests."""
    print("=" * 50)
    print("Asyncio Proxy Server Tests")
    print("=" * 50 + "\n")
    
    try:
        await test_api()
    except Exception as e:
        print(f"API test failed: {e}")
    
    try:
        await test_proxy()
    except Exception as e:
        print(f"Proxy test failed: {e}")


if __name__ == '__main__':
    asyncio.run(main())
