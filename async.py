"""
High-performance asyncio proxy server with embedded aiohttp API.
Handles request forwarding with connection pooling and management endpoints.
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime
from aiohttp import web, ClientSession, TCPConnector
import json
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProxyServer:
    """Async proxy server with embedded management API."""
    
    def __init__(self, proxy_host: str = None, proxy_port: int = None,
                 api_host: str = None, api_port: int = None,
                 target_url: str = None,
                 max_connections: int = None):
        self.proxy_host = proxy_host or os.getenv('PROXY_HOST', '0.0.0.0')
        self.proxy_port = int(proxy_port or os.getenv('PROXY_PORT', 8080))
        self.api_host = api_host or os.getenv('API_HOST', '0.0.0.0')
        self.api_port = int(api_port or os.getenv('API_PORT', 9000))
        self.target_url = target_url or os.getenv('TARGET_URL', 'http://localhost:8000')
        self.max_connections = int(max_connections or os.getenv('MAX_CONNECTIONS', 100))
        
        self.proxy_server = None
        self.api_app = web.Application()
        self.client_session: Optional[ClientSession] = None
        
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'start_time': datetime.now().isoformat(),
            'uptime_seconds': 0,
            'active_connections': 0
        }
        
        self.routes = [
            ('GET', '/health', self.health_check),
            ('GET', '/stats', self.get_stats),
            ('POST', '/config', self.update_config),
            ('GET', '/config', self.get_config),
            ('POST', '/reset-stats', self.reset_stats),
        ]
        
        self._setup_api()
    
    def _setup_api(self):
        """Setup API routes."""
        for method, path, handler in self.routes:
            if method == 'GET':
                self.api_app.router.add_get(path, handler)
            elif method == 'POST':
                self.api_app.router.add_post(path, handler)
        
        logger.info(f"API routes configured: {len(self.routes)} endpoints")
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'active_connections': self.stats['active_connections']
        })
    
    async def get_stats(self, request: web.Request) -> web.Response:
        """Get proxy statistics."""
        self.stats['uptime_seconds'] = int((datetime.now() - datetime.fromisoformat(self.stats['start_time'])).total_seconds())
        
        return web.json_response(self.stats)
    
    async def get_config(self, request: web.Request) -> web.Response:
        """Get current proxy configuration."""
        return web.json_response({
            'proxy_host': self.proxy_host,
            'proxy_port': self.proxy_port,
            'api_host': self.api_host,
            'api_port': self.api_port,
            'target_url': self.target_url,
            'max_connections': self.max_connections,
            'connector_type': 'TCPConnector with connection pooling'
        })
    
    async def update_config(self, request: web.Request) -> web.Response:
        """Update proxy configuration."""
        try:
            data = await request.json()
            
            if 'max_connections' in data:
                self.max_connections = int(data['max_connections'])
                logger.info(f"Updated max_connections to {self.max_connections}")
            
            if 'target_url' in data:
                self.target_url = data['target_url']
                logger.info(f"Updated target_url to {self.target_url}")
            
            return web.json_response({
                'message': 'Configuration updated successfully',
                'config': {
                    'max_connections': self.max_connections,
                    'target_url': self.target_url
                }
            })
        except Exception as e:
            logger.error(f"Config update error: {e}")
            return web.json_response(
                {'error': str(e)},
                status=400
            )
    
    async def reset_stats(self, request: web.Request) -> web.Response:
        """Reset statistics."""
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'start_time': datetime.now().isoformat(),
            'uptime_seconds': 0,
            'active_connections': 0
        }
        return web.json_response({'message': 'Statistics reset'})
    
    async def forward_request(self, method: str, url: str, 
                            headers: Dict[str, str], 
                            data: Optional[bytes] = None) -> tuple[int, str]:
        """Forward request to target server with connection pooling."""
        try:
            self.stats['total_requests'] += 1
            self.stats['active_connections'] += 1
            
            async with self.client_session.request(
                method, url, 
                headers=headers, 
                data=data,
                timeout=30
            ) as resp:
                response_text = await resp.text()
                self.stats['successful_requests'] += 1
                return resp.status, response_text
        
        except Exception as e:
            logger.error(f"Request forwarding error: {e}")
            self.stats['failed_requests'] += 1
            return 502, json.dumps({'error': 'Bad Gateway', 'details': str(e)})
        
        finally:
            self.stats['active_connections'] -= 1
    
    async def handle_proxy_request(self, reader: asyncio.StreamReader, 
                                   writer: asyncio.StreamWriter):
        """Handle incoming proxy requests."""
        try:
            # Read HTTP request line
            request_line = await asyncio.wait_for(reader.readline(), timeout=10)
            if not request_line:
                return
            
            request_line = request_line.decode('latin-1').rstrip('\r\n')
            parts = request_line.split(' ', 2)
            
            if len(parts) < 3:
                logger.warning(f"Invalid request line: {request_line}")
                return
            
            method, path, http_version = parts
            
            # Read headers
            headers = {}
            while True:
                header_line = await asyncio.wait_for(reader.readline(), timeout=10)
                if header_line == b'\r\n' or header_line == b'\n':
                    break
                
                header_line = header_line.decode('latin-1').rstrip('\r\n')
                if ':' in header_line:
                    key, value = header_line.split(':', 1)
                    headers[key.strip()] = value.strip()
            
            # Use configured target URL
            target_url = f"{self.target_url}{path}"
            logger.info(f"Proxying {method} {path} to {target_url}")
            
            # Read body if present
            body = None
            if 'Content-Length' in headers:
                content_length = int(headers['Content-Length'])
                body = await asyncio.wait_for(reader.readexactly(content_length), timeout=10)
            
            # Forward request
            status, response = await self.forward_request(method, target_url, headers, body)
            
            # Send response
            response_line = f"{http_version} {status} OK\r\n"
            response_headers = f"Content-Length: {len(response)}\r\nContent-Type: application/json\r\n\r\n"
            
            writer.write(response_line.encode('latin-1'))
            writer.write(response_headers.encode('latin-1'))
            writer.write(response.encode('utf-8') if isinstance(response, str) else response)
            await writer.drain()
        
        except asyncio.TimeoutError:
            logger.error("Request timeout")
        except Exception as e:
            logger.error(f"Proxy request error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
    
    async def start_proxy(self):
        """Start the proxy server."""
        self.proxy_server = await asyncio.start_server(
            self.handle_proxy_request,
            self.proxy_host,
            self.proxy_port
        )
        logger.info(f"Proxy server started on {self.proxy_host}:{self.proxy_port}")
    
    async def start_api(self):
        """Start the management API server."""
        runner = web.AppRunner(self.api_app)
        await runner.setup()
        site = web.TCPSite(runner, self.api_host, self.api_port)
        await site.start()
        logger.info(f"Management API started on {self.api_host}:{self.api_port}")
        return runner
    
    async def setup_client_session(self):
        """Setup HTTP client session with connection pooling."""
        connector = TCPConnector(
            limit=self.max_connections,
            limit_per_host=30,
            ttl_dns_cache=300
        )
        self.client_session = ClientSession(connector=connector)
        logger.info(f"Client session created with max_connections={self.max_connections}")
    
    async def start(self):
        """Start both proxy and API servers."""
        await self.setup_client_session()
        await self.start_proxy()
        api_runner = await self.start_api()
        
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            logger.info("Shutting down...")
            if self.client_session:
                await self.client_session.close()
            await api_runner.cleanup()


async def main():
    """Main entry point."""
    proxy = ProxyServer()
    
    logger.info("Starting asyncio proxy server...")
    await proxy.start()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Proxy server terminated")
    except OSError as e:
        if e.errno == 10048:
            logger.error("\n" + "!"*60)
            logger.error(f"PORT CONFLICT: Port 8080 or 9000 is already in use!")
            logger.error("Please ensure no other instance of are running, or:")
            logger.error("1. Close the application using those ports.")
            logger.error("2. Change the ports in the main() function of async.py.")
            logger.error("!"*60 + "\n")
        else:
            logger.error(f"Unexpected OS error: {e}")
    except Exception as e:
        logger.error(f"Application crash: {e}")