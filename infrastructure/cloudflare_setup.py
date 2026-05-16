"""
Aethera AI - Cloudflare Setup

Automated Cloudflare Tunnel setup for secure remote access.
"""
import subprocess
import json
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("aethera.cloudflare")


class CloudflareSetup:
    """
    Cloudflare Tunnel configuration.

    Provides secure remote access to Aethera without opening ports.
    """

    def __init__(self, config_dir: str = "./data/cloudflare"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def install_cloudflared(self) -> bool:
        """Install cloudflared daemon."""
        try:
            # Check if already installed
            result = subprocess.run(
                ["cloudflared", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True

            # Install based on platform
            import platform
            system = platform.system()

            if system == "Windows":
                # PowerShell installation
                subprocess.run([
                    "powershell", "-command",
                    "Invoke-WebRequest -Uri https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe -OutFile cloudflared.exe"
                ], cwd=self.config_dir)
            elif system == "Darwin":
                subprocess.run(["brew", "install", "cloudflared"])
            else:
                # Linux
                subprocess.run([
                    "curl", "-L", "-o", str(self.config_dir / "cloudflared"),
                    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
                ])
                subprocess.run(["chmod", "+x", str(self.config_dir / "cloudflared")])

            return True
        except Exception as e:
            print(f"Installation failed: {e}")
            return False

    def create_tunnel(self, tunnel_name: str = "aethera-tunnel") -> Optional[Dict[str, Any]]:
        """Create a new Cloudflare Tunnel."""
        try:
            # Create tunnel
            result = subprocess.run(
                ["cloudflared", "tunnel", "create", "--name", tunnel_name, "--json"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return None

            tunnel_info = json.loads(result.stdout)
            return {
                "id": tunnel_info.get("id"),
                "name": tunnel_info.get("name"),
                "credentials_file": tunnel_info.get("credentialsfile")
            }
        except Exception as e:
            print(f"Tunnel creation failed: {e}")
            return None

    def configure_tunnel(self, tunnel_id: str, local_port: int = 8000) -> bool:
        """Configure tunnel to route to local service."""
        config = {
            "version": "2",
            "tunnel": tunnel_id,
            "credentials-file": str(self.config_dir / f"{tunnel_id}.json"),
            "ingress": [
                {
                    "hostname": f"aethera.{os.getenv('CLOUDFLARE_DOMAIN', 'example.com')}",
                    "service": f"http://localhost:{local_port}"
                },
                {
                    "service": "http_status:404"
                }
            ]
        }

        config_path = self.config_dir / "config.yml"
        try:
            import yaml
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
        except ImportError:
            # Fallback: write YAML manually
            with open(config_path, 'w') as f:
                f.write(f"tunnel: {config['tunnel']}\n")
                f.write(f"credentials-file: {config['credentials-file']}\n")
                f.write("ingress:\n")
                for rule in config['ingress']:
                    if 'hostname' in rule:
                        f.write(f"  - hostname: {rule['hostname']}\n")
                        f.write(f"    service: {rule['service']}\n")
                    else:
                        f.write(f"  - service: {rule['service']}\n")

        return True

    def start_tunnel(self, tunnel_id: str) -> bool:
        """Start the tunnel daemon."""
        try:
            config_path = self.config_dir / "config.yml"

            # Run as background process
            subprocess.Popen(
                ["cloudflared", "tunnel", "run", tunnel_id],
                cwd=str(self.config_dir)
            )

            return True
        except Exception as e:
            print(f"Tunnel start failed: {e}")
            return False

    def get_tunnel_status(self) -> Dict[str, Any]:
        """Get tunnel status."""
        try:
            result = subprocess.run(
                ["cloudflared", "tunnel", "list", "--json"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                tunnels = json.loads(result.stdout)
                return {"tunnels": tunnels, "status": "running"}

            return {"status": "error", "message": "Failed to get status"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def setup_access_policy(self, tunnel_id: str, allowed_emails: list) -> bool:
        """Setup Cloudflare Access policy for the tunnel."""
        api_key = os.getenv("CLOUDFLARE_API_KEY")
        if not api_key:
            logger.warning("CLOUDFLARE_API_KEY not set, skipping access policy setup")
            return False

        account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        if not account_id:
            logger.warning("CLOUDFLARE_ACCOUNT_ID not set, skipping access policy setup")
            return False

        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            # Create an Access application for the tunnel
            app_payload = {
                "name": f"aethera-access-{tunnel_id[:8]}",
                "domain": os.getenv("CLOUDFLARE_DOMAIN", ""),
                "type": "self_hosted",
                "session_duration": "24h",
            }

            with httpx.Client(timeout=30) as client:
                app_resp = client.post(
                    f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps",
                    headers=headers,
                    json=app_payload,
                )

                if app_resp.status_code not in (200, 201):
                    logger.warning(f"Access app creation failed: {app_resp.status_code}")
                    return False

                app_data = app_resp.json().get("result", {})
                app_id = app_data.get("id")

                if not app_id:
                    logger.warning("No app ID returned from Access creation")
                    return False

                # Create email-based access policy
                policy_payload = {
                    "name": f"aethera-policy-{tunnel_id[:8]}",
                    "app_id": app_id,
                    "decision": "allow",
                    "include": [
                        {"email": {"email": email}} for email in (allowed_emails or [])
                    ],
                }

                policy_resp = client.post(
                    f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps/{app_id}/policies",
                    headers=headers,
                    json=policy_payload,
                )

                if policy_resp.status_code not in (200, 201):
                    logger.warning(f"Access policy creation failed: {policy_resp.status_code}")
                    return False

                logger.info(f"Access policy created for tunnel {tunnel_id}")
                return True

        except ImportError:
            logger.error("httpx not installed, cannot create access policy")
            return False
        except Exception as e:
            logger.error(f"Access policy setup failed: {e}")
            return False


# Convenience function
def setup_cloudflare_tunnel(local_port: int = 8000) -> Dict[str, Any]:
    """One-click Cloudflare Tunnel setup."""
    setup = CloudflareSetup()

    # Install
    if not setup.install_cloudflared():
        return {"success": False, "error": "Installation failed"}

    # Create tunnel
    tunnel = setup.create_tunnel()
    if not tunnel:
        return {"success": False, "error": "Tunnel creation failed"}

    # Configure
    setup.configure_tunnel(tunnel["id"], local_port)

    # Start
    if not setup.start_tunnel(tunnel["id"]):
        return {"success": False, "error": "Failed to start tunnel"}

    return {
        "success": True,
        "tunnel_id": tunnel["id"],
        "url": f"https://aethera.{os.getenv('CLOUDFLARE_DOMAIN', 'pending-domain.com')}"
    }
