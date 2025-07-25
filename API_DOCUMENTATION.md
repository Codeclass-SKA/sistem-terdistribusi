# Distributed System Project - API Documentation

## System Overview

This distributed system implements a complete e-commerce platform with the following services:

- **Wallet Service**: User balance management with idempotency
- **Inventory Service**: Product and stock management with reservations
- **Order Service**: Order processing with payments and status tracking

## Running the System

### Using Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f web

# Stop services
docker-compose down
```

The system will be available at:
- **Django App**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin (admin/admin)
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## API Endpoints

### Authentication

Most endpoints require authentication. Use Django session authentication or create users via admin panel.

**Test Users Available:**
- admin/admin (balance: 10,000.00)
- testuser1/testpass123 (balance: 5,000,000)
- testuser2/testpass123 (balance: 7,500,000)

### Wallet Service

#### Top-up Balance
```http
POST /wallet/submit/
Content-Type: application/x-www-form-urlencoded

amount=1000000&_idempotency_key=unique-key-123
```

**Features:**
- Idempotency support (prevents duplicate transactions)
- Atomic operations with race condition protection
- Automatic logging and audit trail

### Inventory Service

#### List Products
```http
GET /inventory/products/
```

#### Get Product Details
```http
GET /inventory/products/{product_id}/
```

#### Add Stock
```http
POST /inventory/stock/add/
Content-Type: application/json

{
    "product_id": "product-uuid",
    "quantity": 10,
    "notes": "Restocking from supplier"
}
```

#### Reserve Stock
```http
POST /inventory/stock/reserve/
Content-Type: application/json

{
    "product_id": "product-uuid",
    "quantity": 2,
    "order_id": "order-uuid"
}
```

#### Confirm Reservation
```http
POST /inventory/stock/confirm/
Content-Type: application/json

{
    "order_id": "order-uuid"
}
```

#### Release Reservation
```http
POST /inventory/stock/release/
Content-Type: application/json

{
    "order_id": "order-uuid"
}
```

#### Stock Movement History
```http
GET /inventory/products/{product_id}/movements/
```

### Order Service

#### Create Order
```http
POST /orders/create/
Content-Type: application/json

{
    "items": [
        {
            "product_id": "product-uuid",
            "quantity": 2
        }
    ],
    "shipping_address": "123 Main St, City, Country",
    "notes": "Please handle with care"
}
```

#### Get Order Details
```http
GET /orders/{order_id}/
```

#### List User Orders
```http
GET /orders/user/orders/
```

#### Process Payment
```http
POST /orders/payment/process/
Content-Type: application/json

{
    "order_id": "order-uuid"
}
```

#### Cancel Order
```http
POST /orders/cancel/
Content-Type: application/json

{
    "order_id": "order-uuid",
    "reason": "Customer request"
}
```

#### Update Order Status (Admin)
```http
POST /orders/admin/update-status/
Content-Type: application/json

{
    "order_id": "order-uuid",
    "status": "SHIPPED",
    "notes": "Shipped via FedEx"
}
```

#### Order Status History
```http
GET /orders/{order_id}/history/
```

## Distributed System Features

### 1. Idempotency
- Implemented in wallet service
- Uses Redis for caching responses
- Prevents duplicate transactions
- Configurable TTL (1 hour default)

### 2. Atomicity
- All database operations wrapped in transactions
- Automatic rollback on errors
- Consistent state across services

### 3. Race Condition Protection
- F() expressions for atomic database updates
- select_for_update() for critical sections
- Optimistic locking where appropriate

### 4. Stock Management
- Temporary reservations with expiration
- Automatic cleanup of expired reservations
- Audit trail for all stock movements

### 5. Order Processing
- Multi-step order workflow
- Payment integration with wallet service
- Automatic refunds on cancellation
- Status tracking and history

## Sample Data

The system automatically creates sample products:

1. **Laptop Gaming** - 15,000,000 (10 units)
2. **Smartphone Android** - 8,000,000 (25 units)
3. **Wireless Headphones** - 2,500,000 (50 units)
4. **Mechanical Keyboard** - 1,500,000 (30 units)
5. **Gaming Mouse** - 800,000 (40 units)

## Error Handling

All APIs return standardized error responses:

```json
{
    "error": "Error description",
    "details": "Additional error details (optional)"
}
```

Common HTTP status codes:
- 200: Success
- 400: Bad Request (validation errors)
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 500: Internal Server Error

## Architecture Patterns

### Microservices Architecture
- Separate services for wallet, inventory, and orders
- Independent data models and business logic
- Scalable and maintainable design

### Event-Driven Architecture (Future)
- Ready for integration with message queues
- Outbox pattern for reliable event publishing
- SAGA pattern for distributed transactions

### CQRS (Command Query Responsibility Segregation)
- Separate read and write operations
- Optimized for different access patterns
- Better scalability and performance

## Monitoring and Observability

### Health Checks
- Database connectivity
- Redis connectivity
- Service availability

### Metrics (Future)
- Request latency
- Transaction volume
- Error rates
- Cache hit rates

### Logging
- Structured logging for all operations
- Correlation IDs for request tracking
- Audit trails for financial operations

## Security Features

### Authentication & Authorization
- Django session-based authentication
- User-level access control
- Admin-only operations

### Data Protection
- SQL injection prevention
- XSS protection
- CSRF protection

### Financial Security
- Idempotency for financial operations
- Audit trails for all transactions
- Balance validation before operations

## Scalability Features

### Horizontal Scaling (Ready)
- Stateless application design
- External session storage (Redis)
- Load balancer ready

### Database Optimization
- Indexed queries
- Connection pooling ready
- Read replicas ready

### Caching Strategy
- Redis for idempotency cache
- Session storage in Redis
- Ready for query result caching

## Testing Strategy

### Unit Tests
- Model validation
- Business logic testing
- Edge case handling

### Integration Tests
- API endpoint testing
- Database interaction testing
- Service communication testing

### Load Testing
- Concurrent transaction testing
- Race condition verification
- Performance benchmarking

## Deployment

### Development
```bash
docker-compose up -d
```

### Production (Ready for)
- Environment variable configuration
- SSL/TLS termination
- Load balancer integration
- Health check endpoints
- Monitoring integration

## Future Enhancements

1. **Service Mesh Integration**
2. **Event Sourcing Implementation**
3. **CQRS with Separate Read Models**
4. **Machine Learning for Fraud Detection**
5. **Real-time Notifications**
6. **Advanced Reporting and Analytics**
7. **Multi-tenant Support**

## Support

For technical support or questions:
- Check the logs: `docker-compose logs -f web`
- Admin panel: http://localhost:8000/admin
- Database console: Access via admin panel or direct connection