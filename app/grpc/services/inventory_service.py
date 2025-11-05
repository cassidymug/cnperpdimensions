"""
Inventory gRPC Service Implementation
High-frequency operations for inventory management with real-time streaming.
"""

import logging
from datetime import datetime
from typing import AsyncIterator, List
import asyncio
from decimal import Decimal

import grpc
from grpc import aio as grpc_aio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.core.database import get_async_db
from app.models.inventory import Product, StockMovement
from app.core.response_wrapper import UnifiedResponse

# Import generated protobuf classes (these will be generated after compilation)
try:
    from app.grpc.generated import inventory_pb2, inventory_pb2_grpc, common_pb2
except ImportError:
    # Placeholder for development - will be available after proto compilation
    inventory_pb2 = None
    inventory_pb2_grpc = None
    common_pb2 = None

logger = logging.getLogger(__name__)

class InventoryServiceImpl(inventory_pb2_grpc.InventoryServiceServicer):
    """High-performance inventory service implementation."""
    
    def __init__(self):
        self.subscribers = {}  # Track real-time subscribers
        self.stock_updates_queue = asyncio.Queue()
        
    async def GetProduct(self, request, context) -> inventory_pb2.ProductResponse:
        """Get a single product by ID."""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(Product).where(Product.id == request.id)
                )
                product = result.scalar_one_or_none()
                
                if not product:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Product with ID {request.id} not found")
                    return inventory_pb2.ProductResponse()
                
                # Convert to protobuf
                product_proto = await self._product_to_proto(product)
                
                response = common_pb2.UnifiedGrpcResponse(
                    success=True,
                    message=f"Retrieved product {product.name}",
                    timestamp=datetime.utcnow().isoformat()
                )
                
                return inventory_pb2.ProductResponse(
                    response=response,
                    product=product_proto
                )
                
        except Exception as e:
            logger.error(f"Error getting product {request.id}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return inventory_pb2.ProductResponse()
    
    async def GetProducts(self, request, context) -> inventory_pb2.ProductsResponse:
        """Get products with pagination and filtering."""
        try:
            async with get_async_db() as db:
                query = select(Product)
                
                # Apply filters
                if request.search:
                    query = query.where(Product.name.ilike(f"%{request.search}%"))
                if request.category:
                    query = query.where(Product.category == request.category)
                if request.inventory_only:
                    query = query.where(Product.is_inventory == True)
                
                # Get total count
                count_result = await db.execute(query.with_only_columns(func.count()))
                total = count_result.scalar()
                
                # Apply pagination
                if request.pagination:
                    query = query.offset(request.pagination.skip).limit(request.pagination.limit)
                
                result = await db.execute(query)
                products = result.scalars().all()
                
                # Convert to protobuf
                products_proto = []
                for product in products:
                    product_proto = await self._product_to_proto(product)
                    products_proto.append(product_proto)
                
                pagination_meta = common_pb2.PaginationMeta(
                    total=total,
                    skip=request.pagination.skip if request.pagination else 0,
                    limit=request.pagination.limit if request.pagination else len(products),
                    pages=(total + (request.pagination.limit - 1)) // request.pagination.limit if request.pagination and request.pagination.limit > 0 else 1
                )
                
                response = common_pb2.UnifiedGrpcResponse(
                    success=True,
                    message=f"Retrieved {len(products)} products",
                    timestamp=datetime.utcnow().isoformat()
                )
                
                return inventory_pb2.ProductsResponse(
                    response=response,
                    products=products_proto,
                    pagination=pagination_meta
                )
                
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return inventory_pb2.ProductsResponse()
    
    async def UpdateStock(self, request, context) -> inventory_pb2.StockResponse:
        """High-frequency stock update operation."""
        try:
            async with get_async_db() as db:
                async with db.begin():
                    # Get current product
                    result = await db.execute(
                        select(Product).where(Product.id == request.product_id)
                    )
                    product = result.scalar_one_or_none()
                    
                    if not product:
                        context.set_code(grpc.StatusCode.NOT_FOUND)
                        context.set_details(f"Product {request.product_id} not found")
                        return inventory_pb2.StockResponse()
                    
                    old_stock = product.current_stock or 0
                    
                    # Update stock based on movement type
                    if request.movement_type == "IN":
                        new_stock = old_stock + request.quantity
                    elif request.movement_type == "OUT":
                        new_stock = old_stock - request.quantity
                        if new_stock < 0:
                            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                            context.set_details("Insufficient stock")
                            return inventory_pb2.StockResponse()
                    elif request.movement_type == "ADJUSTMENT":
                        new_stock = request.quantity
                    else:
                        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                        context.set_details(f"Invalid movement type: {request.movement_type}")
                        return inventory_pb2.StockResponse()
                    
                    # Update product stock
                    await db.execute(
                        update(Product)
                        .where(Product.id == request.product_id)
                        .values(current_stock=new_stock)
                    )
                    
                    # Create stock movement record
                    movement = StockMovement(
                        product_id=request.product_id,
                        quantity=request.quantity,
                        movement_type=request.movement_type,
                        reference=request.reference,
                        notes=request.notes,
                        user_id=request.user_id,
                        timestamp=datetime.utcnow()
                    )
                    db.add(movement)
                    
                    await db.commit()
                    
                    # Notify real-time subscribers
                    await self._notify_stock_update(request.product_id, old_stock, new_stock, movement)
                    
                    response = common_pb2.UnifiedGrpcResponse(
                        success=True,
                        message=f"Updated stock for {product.name}",
                        timestamp=datetime.utcnow().isoformat()
                    )
                    
                    return inventory_pb2.StockResponse(
                        response=response,
                        current_stock=new_stock
                    )
                    
        except Exception as e:
            logger.error(f"Error updating stock for {request.product_id}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return inventory_pb2.StockResponse()
    
    async def BulkUpdateStock(self, request, context) -> inventory_pb2.BulkStockResponse:
        """High-frequency bulk stock updates for performance."""
        try:
            results = []
            processed = 0
            failed = 0
            
            # Process all updates in a single transaction for performance
            async with get_async_db() as db:
                async with db.begin():
                    for update_req in request.updates:
                        try:
                            # Process individual update
                            stock_response = await self.UpdateStock(update_req, context)
                            results.append(stock_response)
                            if stock_response.response.success:
                                processed += 1
                            else:
                                failed += 1
                        except Exception as e:
                            logger.error(f"Bulk update failed for product {update_req.product_id}: {e}")
                            failed += 1
                            
                            # Create error response
                            error_response = inventory_pb2.StockResponse(
                                response=common_pb2.UnifiedGrpcResponse(
                                    success=False,
                                    message=f"Failed to update {update_req.product_id}: {str(e)}",
                                    timestamp=datetime.utcnow().isoformat()
                                )
                            )
                            results.append(error_response)
            
            response = common_pb2.UnifiedGrpcResponse(
                success=failed == 0,
                message=f"Bulk update completed: {processed} processed, {failed} failed",
                timestamp=datetime.utcnow().isoformat()
            )
            
            return inventory_pb2.BulkStockResponse(
                response=response,
                results=results,
                processed=processed,
                failed=failed
            )
            
        except Exception as e:
            logger.error(f"Error in bulk stock update: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return inventory_pb2.BulkStockResponse()
    
    async def WatchInventory(self, request, context) -> AsyncIterator[inventory_pb2.InventoryUpdate]:
        """Real-time inventory updates streaming."""
        subscriber_id = id(context)
        self.subscribers[subscriber_id] = {
            'context': context,
            'product_ids': set(request.product_ids) if request.product_ids else None,
            'include_movements': request.include_movements
        }
        
        try:
            logger.info(f"New inventory watcher subscribed: {subscriber_id}")
            
            # Keep the stream alive and send updates
            while not context.cancelled():
                try:
                    # Wait for updates from the queue with timeout
                    update = await asyncio.wait_for(self.stock_updates_queue.get(), timeout=30.0)
                    
                    # Check if this subscriber is interested in this update
                    if self._should_send_update(subscriber_id, update):
                        yield update
                        
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    heartbeat = inventory_pb2.InventoryUpdate(
                        product_id="heartbeat",
                        timestamp=datetime.utcnow().isoformat()
                    )
                    yield heartbeat
                    
        except grpc.RpcError as e:
            if e.code() != grpc.StatusCode.CANCELLED:
                logger.error(f"Inventory watch error: {e}")
        finally:
            # Clean up subscriber
            if subscriber_id in self.subscribers:
                del self.subscribers[subscriber_id]
            logger.info(f"Inventory watcher unsubscribed: {subscriber_id}")
    
    async def StreamStockLevels(self, request, context) -> AsyncIterator[inventory_pb2.StockUpdate]:
        """Stream current stock levels for all products."""
        try:
            while not context.cancelled():
                async with get_async_db() as db:
                    result = await db.execute(
                        select(Product).where(Product.is_inventory == True)
                    )
                    products = result.scalars().all()
                    
                    for product in products:
                        stock_update = inventory_pb2.StockUpdate(
                            product_id=product.id,
                            product_name=product.name,
                            current_stock=product.current_stock or 0,
                            minimum_stock=product.minimum_stock or 0,
                            is_below_minimum=(product.current_stock or 0) < (product.minimum_stock or 0),
                            last_updated=datetime.utcnow().isoformat()
                        )
                        yield stock_update
                
                # Wait before next update cycle
                await asyncio.sleep(60)  # Update every minute
                
        except grpc.RpcError as e:
            if e.code() != grpc.StatusCode.CANCELLED:
                logger.error(f"Stock levels stream error: {e}")
    
    async def _product_to_proto(self, product) -> inventory_pb2.Product:
        """Convert SQLAlchemy Product to protobuf Product."""
        money_amount = common_pb2.MoneyAmount(
            currency="BWP",
            amount_cents=int((product.unit_price or 0) * 100),
            amount_decimal=float(product.unit_price or 0)
        )
        
        audit_info = common_pb2.AuditInfo(
            created_at=product.created_at.isoformat() if product.created_at else "",
            updated_at=product.updated_at.isoformat() if product.updated_at else ""
        )
        
        return inventory_pb2.Product(
            id=product.id,
            name=product.name or "",
            description=product.description or "",
            category=product.category or "",
            sku=product.sku or "",
            barcode=product.barcode or "",
            unit_price=money_amount,
            unit_of_measure=product.unit_of_measure or "",
            is_inventory=product.is_inventory or False,
            current_stock=float(product.current_stock or 0),
            minimum_stock=float(product.minimum_stock or 0),
            maximum_stock=float(product.maximum_stock or 0),
            audit=audit_info
        )
    
    async def _notify_stock_update(self, product_id: str, old_stock: float, new_stock: float, movement):
        """Notify real-time subscribers of stock updates."""
        try:
            update = inventory_pb2.InventoryUpdate(
                product_id=product_id,
                old_stock=old_stock,
                new_stock=new_stock,
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Add to queue for streaming
            await self.stock_updates_queue.put(update)
            
        except Exception as e:
            logger.error(f"Error notifying stock update: {e}")
    
    def _should_send_update(self, subscriber_id: str, update: inventory_pb2.InventoryUpdate) -> bool:
        """Check if update should be sent to specific subscriber."""
        subscriber = self.subscribers.get(subscriber_id)
        if not subscriber:
            return False
        
        # Check product filter
        if subscriber['product_ids'] is not None:
            if update.product_id not in subscriber['product_ids']:
                return False
        
        return True