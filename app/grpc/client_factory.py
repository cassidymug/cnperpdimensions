"""
gRPC Configuration and Client Factory for CNPERP
Provides centralized gRPC client management and configuration.
"""

import os
import asyncio
import logging
from typing import Dict, Optional, Any
from contextlib import asynccontextmanager
import grpc
from grpc import aio as grpc_aio
from app.core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class GrpcClientFactory:
    """Factory for creating and managing gRPC clients."""
    
    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config or ConfigManager()
        self._clients: Dict[str, Any] = {}
        self._channels: Dict[str, grpc_aio.Channel] = {}
        
    async def get_inventory_client(self):
        """Get or create inventory service client."""
        if 'inventory' not in self._clients:
            channel = await self._get_channel('inventory')
            # Import here to avoid circular imports
            from app.grpc.generated import inventory_pb2_grpc
            self._clients['inventory'] = inventory_pb2_grpc.InventoryServiceStub(channel)
        return self._clients['inventory']
    
    async def get_accounting_client(self):
        """Get or create accounting service client."""
        if 'accounting' not in self._clients:
            channel = await self._get_channel('accounting')
            from app.grpc.generated import accounting_pb2_grpc
            self._clients['accounting'] = accounting_pb2_grpc.AccountingServiceStub(channel)
        return self._clients['accounting']
    
    async def get_realtime_client(self):
        """Get or create realtime service client.""" 
        if 'realtime' not in self._clients:
            channel = await self._get_channel('realtime')
            from app.grpc.generated import realtime_pb2_grpc
            self._clients['realtime'] = realtime_pb2_grpc.RealtimeServiceStub(channel)
        return self._clients['realtime']
    
    async def _get_channel(self, service_name: str) -> grpc_aio.Channel:
        """Get or create gRPC channel for a service."""
        if service_name not in self._channels:
            # Get service configuration
            host = os.getenv(f'GRPC_{service_name.upper()}_HOST', 'localhost')
            port = int(os.getenv(f'GRPC_{service_name.upper()}_PORT', self._get_default_port(service_name)))
            
            # Channel options for performance
            options = [
                ('grpc.keepalive_time_ms', 10000),
                ('grpc.keepalive_timeout_ms', 5000),
                ('grpc.keepalive_permit_without_calls', True),
                ('grpc.http2.max_pings_without_data', 0),
                ('grpc.http2.min_time_between_pings_ms', 10000),
                ('grpc.http2.min_ping_interval_without_data_ms', 300000),
                ('grpc.max_receive_message_length', 4 * 1024 * 1024),  # 4MB
                ('grpc.max_send_message_length', 4 * 1024 * 1024),     # 4MB
            ]
            
            target = f'{host}:{port}'
            logger.info(f"Creating gRPC channel to {service_name} at {target}")
            
            # For development, use insecure channel
            # In production, use secure channel with TLS
            if os.getenv('GRPC_SECURE', 'false').lower() == 'true':
                credentials = grpc.ssl_channel_credentials()
                self._channels[service_name] = grpc_aio.secure_channel(target, credentials, options=options)
            else:
                self._channels[service_name] = grpc_aio.insecure_channel(target, options=options)
        
        return self._channels[service_name]
    
    def _get_default_port(self, service_name: str) -> int:
        """Get default port for a service."""
        default_ports = {
            'inventory': 50051,
            'accounting': 50052,
            'realtime': 50053,
        }
        return default_ports.get(service_name, 50051)
    
    async def close_all(self):
        """Close all gRPC channels and clients."""
        logger.info("Closing all gRPC channels...")
        
        for service_name, channel in self._channels.items():
            try:
                await channel.close()
                logger.info(f"Closed {service_name} channel")
            except Exception as e:
                logger.error(f"Error closing {service_name} channel: {e}")
        
        self._channels.clear()
        self._clients.clear()
        logger.info("All gRPC channels closed")

class GrpcServerConfig:
    """Configuration for gRPC servers."""
    
    def __init__(self):
        self.max_workers = int(os.getenv('GRPC_MAX_WORKERS', '10'))
        self.port = int(os.getenv('GRPC_SERVER_PORT', '50051'))
        self.host = os.getenv('GRPC_SERVER_HOST', '0.0.0.0')
        
        # Server options for performance
        self.options = [
            ('grpc.keepalive_time_ms', 10000),
            ('grpc.keepalive_timeout_ms', 5000),
            ('grpc.http2.max_pings_without_data', 0),
            ('grpc.http2.min_time_between_pings_ms', 10000),
            ('grpc.max_receive_message_length', 4 * 1024 * 1024),
            ('grpc.max_send_message_length', 4 * 1024 * 1024),
            ('grpc.max_concurrent_streams', 100),
        ]

# Global client factory instance
_client_factory: Optional[GrpcClientFactory] = None

def get_grpc_client_factory() -> GrpcClientFactory:
    """Get the global gRPC client factory instance."""
    global _client_factory
    if _client_factory is None:
        _client_factory = GrpcClientFactory()
    return _client_factory

@asynccontextmanager
async def grpc_client_context():
    """Context manager for gRPC client lifecycle."""
    factory = get_grpc_client_factory()
    try:
        yield factory
    finally:
        await factory.close_all()

# Convenience functions for getting clients
async def get_inventory_client():
    """Get inventory service client."""
    factory = get_grpc_client_factory()
    return await factory.get_inventory_client()

async def get_accounting_client():
    """Get accounting service client."""
    factory = get_grpc_client_factory()
    return await factory.get_accounting_client()

async def get_realtime_client():
    """Get realtime service client."""
    factory = get_grpc_client_factory()
    return await factory.get_realtime_client()