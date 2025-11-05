import os
from urllib.parse import urlparse, urlunparse


def _is_wsl() -> bool:
    """Return True if running under WSL (primarily WSL2)."""
    try:
        with open('/proc/version','r',encoding='utf-8') as f:
            v = f.read().lower()
        return 'microsoft' in v or 'wsl' in v
    except Exception:
        return False


def _get_windows_host_gateway() -> str | None:
    """Best-effort retrieval of the Windows host gateway IP from inside WSL.

    WSL2 typically writes the Windows host resolver to /etc/resolv.conf as the
    first nameserver entry.
    """
    try:
        with open('/etc/resolv.conf','r',encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('nameserver'):
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1]
    except Exception:
        pass
    return None


def resolve_database_url(url: str) -> str:
    """Optionally adjust a database URL for WSL scenarios.

    If AUTO_RESOLVE_WSL_DB=1 and we detect WSL and the DB host is localhost / 127.0.0.1,
    we will attempt to substitute the Windows host gateway IP to allow connecting
    to PostgreSQL running on the Windows side when WSL loopback forwarding fails.

    This is a no-op if conditions are not met.
    """
    if not url or '://' not in url:
        return url

    if os.getenv('AUTO_RESOLVE_WSL_DB','0') != '1':
        return url

    if not _is_wsl():
        return url

    parsed = urlparse(url)
    # Only adjust postgres schemes
    if not parsed.scheme.startswith('postgres'):
        return url

    host = parsed.hostname or ''
    if host not in {'localhost','127.0.0.1'}:
        return url

    gateway = _get_windows_host_gateway()
    if not gateway:
        return url

    # Rebuild netloc with possible username/password and new host/port
    username = parsed.username or ''
    password = parsed.password or ''
    port = f":{parsed.port}" if parsed.port else ''
    auth = ''
    if username:
        auth = username
        if password:
            auth += f":{password}"
        auth += '@'
    new_netloc = f"{auth}{gateway}{port}"
    rebuilt = parsed._replace(netloc=new_netloc)
    return urlunparse(rebuilt)
