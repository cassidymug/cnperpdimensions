# CNPERP Dimensions - Enterprise ERP System

**A comprehensive, full-featured Enterprise Resource Planning (ERP) system built with Python FastAPI and modern web technologies.**

---

## 🚀 Features

### Core Modules
- **Point of Sale (POS)** - Complete POS system with receipt printing, session management, and reconciliation
- **Sales & Invoicing** - Customer management, quotations, invoicing, credit notes
- **Inventory Management** - Stock control, product management, serial numbers, UOM
- **Purchasing** - Purchase orders, supplier management, procurement, landed costs
- **Accounting** - Chart of accounts, journal entries, general ledger, IFRS compliance
- **Banking** - Bank accounts, transactions, transfers, reconciliations
- **Manufacturing** - Production orders, job cards, BOM/recipes
- **VAT Management** - VAT tracking, reconciliation, and settlement
- **Asset Management** - Fixed assets, depreciation, maintenance tracking
- **Reporting** - Financial statements, management reports, analytics

### Advanced Features
- **Role-Based Access Control (RBAC)** - Granular permissions system
- **Multi-Branch Support** - Branch switching and branch-specific data
- **Dimensional Accounting** - Cost centers, departments, projects
- **IFRS Compliance** - International financial reporting standards
- **Workflow Management** - Approval workflows and business process automation
- **Activity Tracking** - Comprehensive audit logs
- **Backup & Restore** - Automated and manual backup capabilities
- **Excel Import/Export** - Template-based data import/export

---

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.8+)
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Authentication**: JWT tokens
- **API**: RESTful with OpenAPI/Swagger docs

### Frontend
- **HTML5/CSS3/JavaScript**
- **Bootstrap 5** - Modern UI framework
- **Chart.js** - Data visualization
- **SweetAlert2** - Beautiful alerts and modals
- **No heavy frameworks** - Pure vanilla JS for performance

### DevOps
- **Git** - Version control
- **Alembic** - Database migrations
- **Docker** - Containerization (optional)

---

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- PostgreSQL 12 or higher
- Git

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/cnperpdimensions.git
   cd cnperpdimensions
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure database**
   - Create PostgreSQL database
   - Update connection string in `app/core/config.py`

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start the server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
   ```

7. **Access the application**
   - Web Interface: http://localhost:8010/static/index.html
   - API Docs: http://localhost:8010/docs
   - Login: Default credentials in seed data

---

## 📚 Documentation

- [Quick Start Guide](deploy/QUICK_START.md)
- [Installation Guide](docs/local-network-installation-guide.md)
- [POS Access Control](docs/POS_ACCESS_CONTROL_IMPLEMENTATION.md)
- [Accounting Dimensions](docs/accounting-dimensions-guide.md)
- [Manufacturing Module](docs/MANUFACTURING_IMPLEMENTATION_COMPLETE.md)
- [Banking Guide](docs/help/banking-guide.md)
- [Inventory Guide](docs/help/inventory-guide.md)

---

## 🎯 Key Capabilities

### Financial Management
- Multi-currency support
- Comprehensive chart of accounts
- Automated journal entries
- Bank reconciliation
- VAT compliance
- Financial statement generation
- IFRS reporting

### Inventory Control
- Real-time stock tracking
- Multiple warehouses/branches
- Serial number tracking
- Product assemblies (BOM)
- Stock adjustments
- Inventory valuation (FIFO, Weighted Average)
- Low stock alerts

### Sales & Customer Management
- Customer profiles and history
- Quotation to invoice workflow
- Credit note management
- Multiple payment methods
- Receipt generation
- Sales analytics
- Customer aging reports

### Procurement
- Purchase requisitions
- RFQ management
- Purchase orders
- Supplier management
- Goods receipt
- Payment tracking
- Landed cost allocation

### Manufacturing
- Production orders
- Job cards with BOM
- Material consumption tracking
- Labor and overhead costing
- Work-in-progress monitoring
- Finished goods tracking

---

## 🔐 Security Features

- JWT-based authentication
- Role-based access control (RBAC)
- Permission-based UI rendering
- Page-level access guards
- Session management
- Password hashing
- Activity audit logs
- User permission matrix

---

## 🏗️ Project Structure

```
cnperp-dimensions/
├── app/
│   ├── api/v1/endpoints/    # API endpoints
│   ├── core/                # Core configuration
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   ├── static/              # Frontend files
│   └── main.py              # Application entry
├── alembic/                 # Database migrations
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── tests/                   # Test suite
└── requirements.txt         # Python dependencies
```

---

## 🧪 Testing

Run tests with pytest:
```bash
pytest tests/
```

Run specific test file:
```bash
pytest tests/api/test_auth_api.py
```

---

## 🚢 Deployment

### Local Network Deployment
See [Local Network Installation Guide](docs/local-network-installation-guide.md)

### Remote Server Deployment
See [Deployment Guide](deploy/QUICK_START.md)

### Update Script
```bash
# Windows
.\deploy\update_app.ps1

# Linux
./deploy/update_app.sh
```

---

## 📊 Recent Updates

### November 2025
- ✅ Implemented POS-only user role with restricted access
- ✅ Added bank transfer approval and rejection endpoints
- ✅ Created professional transfer receipt PDF generator
- ✅ Fixed logout functionality across all pages
- ✅ Added comprehensive page access guards
- ✅ Enhanced navbar with role-based visibility

### October 2025
- ✅ Completed Manufacturing module
- ✅ Enhanced VAT reconciliation
- ✅ Implemented IFRS reporting
- ✅ Added dimensional accounting
- ✅ Created workflow management system

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is proprietary software developed for CNPERP.

---

## 👥 Support

For support and questions:
- Create an issue on GitHub
- Email: dev@cnperp.com
- Documentation: Check the `/docs` folder

---

## 🗺️ Roadmap

### Planned Features
- [ ] Mobile app (React Native)
- [ ] Advanced analytics dashboard
- [ ] Integration with payment gateways
- [ ] HR & Payroll module
- [ ] CRM module
- [ ] Project management
- [ ] E-commerce integration
- [ ] Multi-language support

---

## ⚡ Performance

- Optimized database queries with eager loading
- Indexed critical tables
- Caching for frequently accessed data
- Async operations where applicable
- Minimal frontend dependencies
- Fast page load times

---

## 🎨 Screenshots

_Add screenshots of your application here_

---

## 📞 Contact

**CNPERP Development Team**
- Website: [Coming Soon]
- Email: dev@cnperp.com

---

**Built with ❤️ using Python FastAPI**
