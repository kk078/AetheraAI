"""
Cloudflare Plugin for Aethera
Manages Cloudflare DNS, Tunnels, Access, Workers, and R2.
"""
import asyncio
import os
from typing import Any, Dict, List, Optional
import aiohttp
from ..plugin_base import AetheraPlugin, PluginConfig, PluginParameter, PluginResult


class CloudflarePlugin(AetheraPlugin):
    """Cloudflare integration plugin."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key', '')
        self.account_id = config.get('account_id', '')
        self.zone_id = config.get('zone_id', '')
        self._session: Optional[aiohttp.ClientSession] = None

    def get_config(self) -> PluginConfig:
        return PluginConfig(
            name='cloudflare',
            version='1.0.0',
            description='Cloudflare DNS, Tunnels, Access, Workers, and R2 management',
            author='Aethera AI',
            parameters=[
                PluginParameter(
                    name='action',
                    type='action',
                    description='Action to perform',
                    required=True,
                    choices=[
                        'get_dns_records', 'add_dns_record', 'update_dns_record', 'delete_dns_record',
                        'get_tunnel_status', 'create_tunnel', 'delete_tunnel',
                        'get_access_policy', 'create_access_policy',
                        'list_workers', 'deploy_worker',
                        'list_r2_buckets', 'create_r2_bucket', 'delete_r2_bucket',
                        'purge_cache',
                    ]
                ),
                PluginParameter(name='name', type='str', description='Record/resource name', required=False),
                PluginParameter(name='type', type='str', description='DNS record type (A, CNAME, MX, etc.)', required=False),
                PluginParameter(name='content', type='str', description='Record content/value', required=False),
                PluginParameter(name='ttl', type='int', description='DNS TTL in seconds', required=False, default=3600),
                PluginParameter(name='proxied', type='bool', description='Proxy through Cloudflare', required=False, default=True),
                PluginParameter(name='priority', type='int', description='MX record priority', required=False),
                PluginParameter(name='script', type='str', description='Worker script content', required=False),
                PluginParameter(name='binding_name', type='str', description='R2 bucket binding name', required=False),
                PluginParameter(name='policy_name', type='str', description='Access policy name', required=False),
                PluginParameter(name='email', type='str', description='Email for Access policy', required=False),
            ],
            permissions=['dns:write', 'tunnel:manage', 'access:manage', 'workers:deploy', 'r2:manage'],
            dependencies=['aiohttp'],
        )

    async def _do_initialize(self) -> None:
        """Initialize HTTP session."""
        if not self.api_key:
            raise ValueError("Cloudflare API key is required")
        if not self.account_id:
            raise ValueError("Cloudflare Account ID is required")

        self._session = aiohttp.ClientSession(
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
        )

    async def cleanup(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        await super().cleanup()

    async def execute(self, action: str, parameters: Dict[str, Any]) -> PluginResult:
        """Execute Cloudflare action."""
        action_map = {
            'get_dns_records': self._get_dns_records,
            'add_dns_record': self._add_dns_record,
            'update_dns_record': self._update_dns_record,
            'delete_dns_record': self._delete_dns_record,
            'get_tunnel_status': self._get_tunnel_status,
            'create_tunnel': self._create_tunnel,
            'delete_tunnel': self._delete_tunnel,
            'get_access_policy': self._get_access_policy,
            'create_access_policy': self._create_access_policy,
            'list_workers': self._list_workers,
            'deploy_worker': self._deploy_worker,
            'list_r2_buckets': self._list_r2_buckets,
            'create_r2_bucket': self._create_r2_bucket,
            'delete_r2_bucket': self._delete_r2_bucket,
            'purge_cache': self._purge_cache,
        }

        if action not in action_map:
            return PluginResult(success=False, error=f"Unknown action: {action}")

        try:
            result = await action_map[action](parameters)
            return PluginResult(success=True, data=result)
        except Exception as e:
            return PluginResult(success=False, error=str(e))

    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make Cloudflare API request."""
        url = f"https://api.cloudflare.com/client/v4/{endpoint}"
        async with self._session.request(method, url, json=data) as resp:
            result = await resp.json()
            if not result.get('success', False):
                errors = result.get('errors', [{'message': 'Unknown error'}])
                raise Exception(f"Cloudflare API error: {errors[0]['message']}")
            return result.get('result', {})

    async def _get_dns_records(self, params: Dict) -> List[Dict]:
        """Get DNS records for zone."""
        result = await self._request('GET', f'zones/{self.zone_id}/dns_records')
        return [
            {
                'id': r['id'],
                'name': r['name'],
                'type': r['type'],
                'content': r['content'],
                'proxied': r.get('proxied', False),
                'ttl': r.get('ttl', 3600),
            }
            for r in result
        ]

    async def _add_dns_record(self, params: Dict) -> Dict:
        """Add DNS record."""
        data = {
            'type': params.get('type', 'A'),
            'name': params['name'],
            'content': params['content'],
            'ttl': params.get('ttl', 3600),
            'proxied': params.get('proxied', True),
        }
        if params.get('priority'):
            data['priority'] = params['priority']

        result = await self._request('POST', f'zones/{self.zone_id}/dns_records', data)
        return {'id': result['id'], 'name': result['name'], 'type': result['type']}

    async def _update_dns_record(self, params: Dict) -> Dict:
        """Update DNS record."""
        record_id = params.get('id')
        if not record_id:
            raise ValueError("Record ID required for update")

        data = {
            'type': params.get('type'),
            'name': params.get('name'),
            'content': params.get('content'),
            'ttl': params.get('ttl'),
            'proxied': params.get('proxied'),
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        result = await self._request('PUT', f'zones/{self.zone_id}/dns_records/{record_id}', data)
        return {'id': result['id'], 'name': result['name']}

    async def _delete_dns_record(self, params: Dict) -> bool:
        """Delete DNS record."""
        record_id = params.get('id')
        if not record_id:
            raise ValueError("Record ID required for deletion")

        await self._request('DELETE', f'zones/{self.zone_id}/dns_records/{record_id}')
        return True

    async def _get_tunnel_status(self, params: Dict) -> Dict:
        """Get Cloudflare Tunnel status."""
        tunnel_id = params.get('tunnel_id')

        if tunnel_id:
            tunnel = await self._request('GET', f'accounts/{self.account_id}/tunnels/{tunnel_id}')
            return {
                'id': tunnel['id'],
                'name': tunnel['name'],
                'status': 'active' if tunnel.get('connections', []) else 'inactive',
                'connections': len(tunnel.get('connections', [])),
            }
        else:
            tunnels = await self._request('GET', f'accounts/{self.account_id}/tunnels')
            return [
                {
                    'id': t['id'],
                    'name': t['name'],
                    'status': 'active' if t.get('connections', []) else 'inactive',
                }
                for t in tunnels
            ]

    async def _create_tunnel(self, params: Dict) -> Dict:
        """Create Cloudflare Tunnel."""
        name = params.get('name', 'aethera-tunnel')

        # Create tunnel
        tunnel = await self._request('POST', f'accounts/{self.account_id}/tunnels', {
            'name': name,
            'config_src': 'cloudflare'
        })

        # Generate token
        tunnel_id = tunnel['id']
        token = await self._request('POST', f'accounts/{self.account_id}/tunnels/{tunnel_id}/tokens')

        return {
            'id': tunnel['id'],
            'name': tunnel['name'],
            'token': token.get('token', ''),
            'install_command': f"cloudflared service install {token.get('token', '')}",
        }

    async def _delete_tunnel(self, params: Dict) -> bool:
        """Delete Cloudflare Tunnel."""
        tunnel_id = params.get('id')
        if not tunnel_id:
            raise ValueError("Tunnel ID required")

        await self._request('DELETE', f'accounts/{self.account_id}/tunnels/{tunnel_id}')
        return True

    async def _get_access_policy(self, params: Dict) -> List[Dict]:
        """Get Access policies."""
        result = await self._request('GET', f'accounts/{self.account_id}/access/policies')
        return [
            {'id': p['id'], 'name': p['name'], 'enabled': p.get('enabled', True)}
            for p in result
        ]

    async def _create_access_policy(self, params: Dict) -> Dict:
        """Create Access policy."""
        name = params.get('policy_name', 'aethera-access')
        email = params.get('email')

        if not email:
            raise ValueError("Email required for Access policy")

        policy = await self._request('POST', f'accounts/{self.account_id}/access/policies', {
            'name': name,
            'enabled': True,
            'aud': 'aethera',
            'include': [{'email': {'email': email}}],
        })

        return {'id': policy['id'], 'name': policy['name']}

    async def _list_workers(self, params: Dict) -> List[Dict]:
        """List Cloudflare Workers."""
        result = await self._request('GET', f'accounts/{self.account_id}/workers/scripts')
        return [{'name': w['id'], 'created': w.get('created_on', '')} for w in result.get('workers', [])]

    async def _deploy_worker(self, params: Dict) -> Dict:
        """Deploy Cloudflare Worker."""
        name = params.get('name', 'aethera-worker')
        script = params.get('script')

        if not script:
            raise ValueError("Worker script content required")

        # Deploy worker
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/workers/scripts/{name}"
        async with self._session.put(
            url,
            data=script,
            headers={'Content-Type': 'application/javascript'}
        ) as resp:
            result = await resp.json()
            if not result.get('success'):
                errors = result.get('errors', [{'message': 'Unknown error'}])
                raise Exception(f"Worker deploy failed: {errors[0]['message']}")

        return {'name': name, 'status': 'deployed'}

    async def _list_r2_buckets(self, params: Dict) -> List[Dict]:
        """List R2 buckets."""
        result = await self._request('GET', f'accounts/{self.account_id}/r2/buckets')
        return [{'name': b['name'], 'created': b.get('creation_date', '')} for b in result.get('buckets', [])]

    async def _create_r2_bucket(self, params: Dict) -> Dict:
        """Create R2 bucket."""
        name = params.get('name')
        if not name:
            raise ValueError("Bucket name required")

        bucket = await self._request('POST', f'accounts/{self.account_id}/r2/buckets', {'name': name})
        return {'name': bucket['name']}

    async def _delete_r2_bucket(self, params: Dict) -> bool:
        """Delete R2 bucket."""
        name = params.get('name')
        if not name:
            raise ValueError("Bucket name required")

        await self._request('DELETE', f'accounts/{self.account_id}/r2/buckets/{name}')
        return True

    async def _purge_cache(self, params: Dict) -> Dict:
        """Purge Cloudflare cache."""
        tags = params.get('tags', [])
        hosts = params.get('hosts', [])

        data = {}
        if tags:
            data['tags'] = tags
        if hosts:
            data['hosts'] = hosts

        result = await self._request('POST', f'zones/{self.zone_id}/purge_cache', data)
        return {'status': 'purged', 'tags': tags, 'hosts': hosts}


def register_plugin():
    """Register the Cloudflare plugin."""
    return CloudflarePlugin, {
        'api_key': os.getenv('CLOUDFLARE_API_KEY', ''),
        'account_id': os.getenv('CLOUDFLARE_ACCOUNT_ID', ''),
        'zone_id': os.getenv('CLOUDFLARE_ZONE_ID', ''),
        'enabled': True,
    }
