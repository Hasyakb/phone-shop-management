# seed_data.py
import sys
import os
from datetime import datetime, timedelta

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Customer, Product, Transaction, User, UserRole
from werkzeug.security import generate_password_hash

def seed_database():
    with app.app_context():
        print("Clearing existing data...")
        db.drop_all()
        db.create_all()
        
        # Create Master Admin
        print("Creating Master Admin...")
        master_admin = User(
            username='masteradmin',
            email='master@phoneshop.com',
            password=generate_password_hash('Master@123'),
            role=UserRole.MASTER_ADMIN,
            is_active=True,
            shop_name='System Master Admin',
            shop_address='Headquarters'
        )
        db.session.add(master_admin)
        db.session.commit()
        
        # Create Shop Owners
        print("Creating Shop Owners...")
        
        shop1 = User(
            username='ahmadushop',
            email='ahmadu@phoneshop.com',
            password=generate_password_hash('shop123'),
            role=UserRole.SHOP_OWNER,
            is_active=True,
            shop_name='Ahmadu Phone Store',
            shop_address='Kaduna Central Market, Shop 15',
            shop_phone='08012345678',
            created_by=master_admin.id
        )
        
        shop2 = User(
            username='fatimashop',
            email='fatima@phoneshop.com',
            password=generate_password_hash('shop123'),
            role=UserRole.SHOP_OWNER,
            is_active=True,
            shop_name='Fatima Mobile World',
            shop_address='Unguwan Sarki, Kaduna',
            shop_phone='08023456789',
            created_by=master_admin.id
        )
        
        db.session.add_all([shop1, shop2])
        db.session.commit()
        
        # Add test data for shop1
        print("Adding test data for Shop 1...")
        customer1 = Customer(
            owner_id=shop1.id,
            full_name='Musa Abdullahi',
            phone_number='08034567890',
            address='Tudun Wada, Kaduna',
            guarantor_name='Sani Musa',
            guarantor_phone='08045678901'
        )
        db.session.add(customer1)
        db.session.commit()
        
        product1 = Product(
            owner_id=shop1.id,
            name='Samsung Galaxy A14',
            imei='123456789012345',
            price=150000,
            stock_quantity=10
        )
        db.session.add(product1)
        db.session.commit()
        
        transaction1 = Transaction(
            owner_id=shop1.id,
            customer_id=customer1.id,
            product_id=product1.id,
            total_price=150000,
            amount_paid=150000,
            balance=0,
            payment_type='FULL',
            status='PAID',
            created_at=datetime.now() - timedelta(days=2)
        )
        db.session.add(transaction1)
        
        # Add test data for shop2
        print("Adding test data for Shop 2...")
        customer2 = Customer(
            owner_id=shop2.id,
            full_name='Aisha Bello',
            phone_number='08056789012',
            address='Malali, Kaduna',
            guarantor_name='Bello Usman',
            guarantor_phone='08067890123'
        )
        db.session.add(customer2)
        db.session.commit()
        
        product2 = Product(
            owner_id=shop2.id,
            name='Tecno Spark 10 Pro',
            imei='234567890123456',
            price=120000,
            stock_quantity=8
        )
        db.session.add(product2)
        db.session.commit()
        
        transaction2 = Transaction(
            owner_id=shop2.id,
            customer_id=customer2.id,
            product_id=product2.id,
            total_price=120000,
            amount_paid=50000,
            balance=70000,
            payment_type='INSTALLMENT',
            status='PARTIAL',
            due_date=datetime.now().date() + timedelta(days=10),
            created_at=datetime.now()
        )
        db.session.add(transaction2)
        
        db.session.commit()
        
        print("\n" + "="*60)
        print("DATABASE SEEDED SUCCESSFULLY!")
        print("="*60)
        print("\nLOGIN CREDENTIALS:")
        print("-" * 40)
        print("MASTER ADMIN:")
        print("   Username: masteradmin")
        print("   Password: Master@123")
        print("\nSHOP OWNERS:")
        print("   1. Username: ahmadushop | Password: shop123 | Shop: Ahmadu Phone Store")
        print("   2. Username: fatimashop | Password: shop123 | Shop: Fatima Mobile World")
        print("="*60)
        print("\nMaster Admin can:")
        print("   Create/Edit/Disable shop owner accounts")
        print("   Reset shop owner passwords")
        print("   View all shops' statistics")
        print("\nShop Owners can:")
        print("   Only access their own shop data")
        print("   Manage customers, products, transactions")
        print("="*60)

if __name__ == '__main__':
    seed_database()