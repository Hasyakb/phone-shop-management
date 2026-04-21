from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import relationship

db = SQLAlchemy()

class UserRole:
    MASTER_ADMIN = 'master_admin'
    SHOP_OWNER = 'shop_owner'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default=UserRole.SHOP_OWNER)
    is_active = db.Column(db.Boolean, default=True)
    shop_name = db.Column(db.String(100))
    shop_address = db.Column(db.String(200))
    shop_phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    creator = relationship('User', remote_side=[id], backref='created_users')
    customers = relationship('Customer', backref='owner', lazy=True)
    products = relationship('Product', backref='owner', lazy=True)
    transactions = relationship('Transaction', backref='owner', lazy=True)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200))
    guarantor_name = db.Column(db.String(100))
    guarantor_phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    transactions = relationship('Transaction', backref='customer', lazy=True)
    
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    imei = db.Column(db.String(50))
    price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    transactions = relationship('Transaction', backref='product', lazy=True)
    
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    phone_imei = db.Column(db.String(50))  # Added IMEI field for the specific phone sold
    total_price = db.Column(db.Float, nullable=False)
    amount_paid = db.Column(db.Float, default=0)
    balance = db.Column(db.Float, default=0)
    payment_type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='PARTIAL')
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    payments = relationship('Payment', backref='transaction', lazy=True, cascade='all, delete-orphan')
    
    def calculate_balance(self):
        total_paid = sum(payment.amount_paid for payment in self.payments) + self.amount_paid
        self.balance = self.total_price - total_paid
        if self.balance <= 0:
            self.status = 'PAID'
            self.balance = 0
        elif self.amount_paid == 0 and total_paid == 0:
            self.status = 'UNPAID'
        else:
            self.status = 'PARTIAL'
        return self.balance
    
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.String(200))