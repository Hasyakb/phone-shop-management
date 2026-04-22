from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Customer, Product, Transaction, Payment, UserRole
from datetime import datetime, timedelta, date
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import csv
import io
import os
import sys
from sqlalchemy import func, or_

app = Flask(__name__)

# Ensure instance folder exists for database
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
try:
    os.makedirs(instance_path, mode=0o755, exist_ok=True)
    print(f"✅ Instance folder created at: {instance_path}")
except Exception as e:
    print(f"❌ Error creating instance folder: {e}")

# Logo upload configuration - use static folder for direct serving
STATIC_UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
try:
    os.makedirs(STATIC_UPLOAD_FOLDER, mode=0o755, exist_ok=True)
    print(f"✅ Upload folder created at: {STATIC_UPLOAD_FOLDER}")
except Exception as e:
    print(f"❌ Error creating upload folder: {e}")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
app.config['UPLOAD_FOLDER'] = STATIC_UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database configuration - SQLite
database_path = os.path.join(instance_path, 'phone_shop.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'check_same_thread': False},
    'pool_size': 1,
    'pool_recycle': 3600,
}

print(f"📁 Database path: {database_path}")
print(f"📁 Database exists: {os.path.exists(database_path)}")
print(f"📁 Upload folder: {STATIC_UPLOAD_FOLDER}")
print(f"📁 Upload folder exists: {os.path.exists(STATIC_UPLOAD_FOLDER)}")
sys.stdout.flush()

db.init_app(app)

# FORCE database tables creation on startup
with app.app_context():
    try:
        db.create_all()
        print("✅ Database tables created successfully")
        
        # Verify tables exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📊 Existing tables: {tables}")
        sys.stdout.flush()
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def require_master_admin():
    if current_user.role != UserRole.MASTER_ADMIN:
        abort(403)

def create_master_admin():
    with app.app_context():
        try:
            # Check if master admin exists
            master_admin = User.query.filter_by(role=UserRole.MASTER_ADMIN).first()
            if not master_admin:
                master_admin = User(
                    username='masteradmin',
                    email='admin@phoneshop.com',
                    password=generate_password_hash('Master@123'),
                    role=UserRole.MASTER_ADMIN,
                    is_active=True,
                    shop_name='Master Admin',
                    shop_address='System Administrator'
                )
                db.session.add(master_admin)
                db.session.commit()
                print("="*50)
                print("✅ MASTER ADMIN CREATED!")
                print("👤 Username: masteradmin")
                print("🔑 Password: Master@123")
                print("="*50)
                sys.stdout.flush()
            else:
                print("✅ Master admin already exists")
                sys.stdout.flush()
            
            # Create a demo shop if none exists
            demo_shop = User.query.filter_by(role=UserRole.SHOP_OWNER).first()
            if not demo_shop:
                demo_shop = User(
                    username='demomarket',
                    email='demo@phoneshop.com',
                    password=generate_password_hash('demo123'),
                    role=UserRole.SHOP_OWNER,
                    is_active=True,
                    shop_name='Demo Phone Market',
                    shop_address='Kaduna, Nigeria',
                    shop_phone='08012345678'
                )
                db.session.add(demo_shop)
                db.session.commit()
                print("✅ Demo shop created: demomarket / demo123")
                sys.stdout.flush()
            else:
                print("✅ Demo shop already exists")
                sys.stdout.flush()
                
        except Exception as e:
            print(f"❌ Error in create_master_admin: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()

# Call create_master_admin after app context is ready
with app.app_context():
    create_master_admin()

# Test routes for debugging
@app.route('/test')
def test():
    return "✅ Application is working! Database is connected."

@app.route('/debug-users')
def debug_users():
    try:
        with app.app_context():
            users = User.query.all()
            user_list = [{'username': u.username, 'role': u.role, 'email': u.email} for u in users]
            return {'users': user_list, 'count': len(user_list)}
    except Exception as e:
        return {'error': str(e)}

@app.route('/debug-db')
def debug_db():
    try:
        with app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            return {
                'database_path': app.config['SQLALCHEMY_DATABASE_URI'],
                'tables': tables,
                'tables_count': len(tables)
            }
    except Exception as e:
        return {'error': str(e)}

@app.route('/debug-logo')
@login_required
def debug_logo():
    return {
        'shop_logo_path': current_user.shop_logo,
        'full_url': request.host_url + current_user.shop_logo if current_user.shop_logo else None,
        'file_exists': os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), current_user.shop_logo)) if current_user.shop_logo else False,
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'upload_folder_exists': os.path.exists(app.config['UPLOAD_FOLDER'])
    }

# Logo upload routes
@app.route('/shop/upload-logo', methods=['GET', 'POST'])
@login_required
def upload_logo():
    if current_user.role == UserRole.MASTER_ADMIN:
        flash('Master admin cannot upload shop logo', 'warning')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        if 'logo' not in request.files:
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        file = request.files['logo']
        
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Delete old logo if exists
            if current_user.shop_logo:
                old_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), current_user.shop_logo)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
                    print(f"✅ Deleted old logo: {old_filepath}")
            
            filename = secure_filename(f"shop_{current_user.id}_{int(datetime.now().timestamp())}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            print(f"✅ Logo saved to: {filepath}")
            
            # Save relative path for URL (without leading slash)
            current_user.shop_logo = f"static/uploads/{filename}"
            db.session.commit()
            
            flash('Logo uploaded successfully!', 'success')
            print(f"✅ Logo URL: {current_user.shop_logo}")
        else:
            flash('Invalid file type. Allowed: PNG, JPG, JPEG, GIF, SVG', 'danger')
        
        return redirect(url_for('dashboard'))
    
    return render_template('upload_logo.html')

@app.route('/shop/delete-logo')
@login_required
def delete_logo():
    if current_user.role == UserRole.MASTER_ADMIN:
        return redirect(url_for('admin_dashboard'))
    
    if current_user.shop_logo:
        # Delete file from system
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), current_user.shop_logo)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"✅ Deleted logo: {filepath}")
        
        # Remove from database
        current_user.shop_logo = None
        db.session.commit()
        flash('Logo removed successfully!', 'success')
    
    return redirect(url_for('dashboard'))

# Routes
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            if not user.is_active:
                flash('Your account has been disabled. Please contact administrator.', 'danger')
                return redirect(url_for('login'))
            
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f'Welcome back, {user.username}!', 'success')
            
            # Redirect based on role
            if user.role == UserRole.MASTER_ADMIN:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# API Routes
@app.route('/api/customers', methods=['POST'])
@login_required
def api_create_customer():
    if current_user.role == UserRole.MASTER_ADMIN:
        return jsonify({'success': False, 'message': 'Not allowed'})
    
    data = request.get_json()
    
    if not data.get('full_name') or not data.get('phone_number'):
        return jsonify({'success': False, 'message': 'Name and phone number are required'})
    
    customer = Customer(
        owner_id=current_user.id,
        full_name=data['full_name'],
        phone_number=data['phone_number'],
        address=data.get('address', ''),
        guarantor_name=data.get('guarantor_name', ''),
        guarantor_phone=data.get('guarantor_phone', '')
    )
    
    db.session.add(customer)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'customer_id': customer.id,
        'full_name': customer.full_name,
        'phone_number': customer.phone_number
    })

# Master Admin Routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != UserRole.MASTER_ADMIN:
        return redirect(url_for('dashboard'))
    
    total_shops = User.query.filter_by(role=UserRole.SHOP_OWNER).count()
    active_shops = User.query.filter_by(role=UserRole.SHOP_OWNER, is_active=True).count()
    total_customers = Customer.query.count()
    total_transactions = Transaction.query.count()
    total_revenue = db.session.query(func.sum(Transaction.total_price)).scalar() or 0
    
    recent_shops = User.query.filter_by(role=UserRole.SHOP_OWNER).order_by(User.created_at.desc()).limit(5).all()
    
    return render_template('admin_dashboard.html', 
                         total_shops=total_shops,
                         active_shops=active_shops,
                         total_customers=total_customers,
                         total_transactions=total_transactions,
                         total_revenue=total_revenue,
                         recent_shops=recent_shops)

@app.route('/admin/shops')
@login_required
def admin_shops():
    if current_user.role != UserRole.MASTER_ADMIN:
        return redirect(url_for('dashboard'))
    
    shops = User.query.filter_by(role=UserRole.SHOP_OWNER).order_by(User.created_at.desc()).all()
    return render_template('admin_shops.html', shops=shops)

@app.route('/admin/shop/add', methods=['GET', 'POST'])
@login_required
def admin_add_shop():
    if current_user.role != UserRole.MASTER_ADMIN:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        shop_name = request.form['shop_name']
        shop_address = request.form['shop_address']
        shop_phone = request.form['shop_phone']
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('admin_add_shop'))
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already exists!', 'danger')
            return redirect(url_for('admin_add_shop'))
        
        new_shop = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role=UserRole.SHOP_OWNER,
            is_active=True,
            shop_name=shop_name,
            shop_address=shop_address,
            shop_phone=shop_phone,
            created_by=current_user.id
        )
        
        db.session.add(new_shop)
        db.session.commit()
        
        flash(f'Shop "{shop_name}" created successfully!', 'success')
        return redirect(url_for('admin_shops'))
    
    return render_template('admin_add_shop.html')

@app.route('/admin/shop/<int:id>/toggle-status')
@login_required
def admin_toggle_shop_status(id):
    if current_user.role != UserRole.MASTER_ADMIN:
        return redirect(url_for('dashboard'))
    
    shop = User.query.get_or_404(id)
    shop.is_active = not shop.is_active
    db.session.commit()
    
    status_text = "enabled" if shop.is_active else "disabled"
    flash(f'Shop "{shop.shop_name}" has been {status_text}!', 'success')
    return redirect(url_for('admin_shops'))

@app.route('/admin/shop/<int:id>/reset-password', methods=['GET', 'POST'])
@login_required
def admin_reset_password(id):
    if current_user.role != UserRole.MASTER_ADMIN:
        return redirect(url_for('dashboard'))
    
    shop = User.query.get_or_404(id)
    
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if new_password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('admin_reset_password', id=id))
        
        if len(new_password) < 6:
            flash('Password must be at least 6 characters!', 'danger')
            return redirect(url_for('admin_reset_password', id=id))
        
        shop.password = generate_password_hash(new_password)
        db.session.commit()
        
        flash(f'Password for "{shop.shop_name}" has been reset successfully!', 'success')
        return redirect(url_for('admin_shops'))
    
    return render_template('admin_reset_password.html', shop=shop)

@app.route('/admin/shop/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_shop(id):
    if current_user.role != UserRole.MASTER_ADMIN:
        return redirect(url_for('dashboard'))
    
    shop = User.query.get_or_404(id)
    
    if request.method == 'POST':
        shop.shop_name = request.form['shop_name']
        shop.shop_address = request.form['shop_address']
        shop.shop_phone = request.form['shop_phone']
        shop.email = request.form['email']
        
        db.session.commit()
        flash(f'Shop "{shop.shop_name}" updated successfully!', 'success')
        return redirect(url_for('admin_shops'))
    
    return render_template('admin_edit_shop.html', shop=shop)

@app.route('/admin/shop/<int:id>/delete-logo')
@login_required
def admin_delete_shop_logo(id):
    if current_user.role != UserRole.MASTER_ADMIN:
        return redirect(url_for('dashboard'))
    
    shop = User.query.get_or_404(id)
    if shop.shop_logo:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), shop.shop_logo)
        if os.path.exists(filepath):
            os.remove(filepath)
        shop.shop_logo = None
        db.session.commit()
        flash(f'Logo removed from {shop.shop_name}', 'success')
    
    return redirect(url_for('admin_edit_shop', id=id))

@app.route('/admin/shop/<int:id>/view')
@login_required
def admin_view_shop(id):
    if current_user.role != UserRole.MASTER_ADMIN:
        return redirect(url_for('dashboard'))
    
    shop = User.query.get_or_404(id)
    
    total_customers = Customer.query.filter_by(owner_id=id).count()
    total_products = Product.query.filter_by(owner_id=id).count()
    total_transactions = Transaction.query.filter_by(owner_id=id).count()
    total_revenue = db.session.query(func.sum(Transaction.total_price)).filter_by(owner_id=id).scalar() or 0
    outstanding_debt = db.session.query(func.sum(Transaction.balance)).filter_by(owner_id=id).filter(Transaction.status != 'PAID').scalar() or 0
    
    recent_transactions = Transaction.query.filter_by(owner_id=id).order_by(Transaction.created_at.desc()).limit(10).all()
    
    return render_template('admin_view_shop.html', 
                         shop=shop,
                         total_customers=total_customers,
                         total_products=total_products,
                         total_transactions=total_transactions,
                         total_revenue=total_revenue,
                         outstanding_debt=outstanding_debt,
                         recent_transactions=recent_transactions)

# Shop Owner Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == UserRole.MASTER_ADMIN:
        return redirect(url_for('admin_dashboard'))
    
    total_sales = db.session.query(func.sum(Transaction.total_price)).filter_by(owner_id=current_user.id).scalar() or 0
    total_outstanding = db.session.query(func.sum(Transaction.balance)).filter_by(owner_id=current_user.id).filter(Transaction.status != 'PAID').scalar() or 0
    total_customers = Customer.query.filter_by(owner_id=current_user.id).count()
    total_transactions = Transaction.query.filter_by(owner_id=current_user.id).count()
    
    recent_transactions = Transaction.query.filter_by(owner_id=current_user.id).order_by(Transaction.created_at.desc()).limit(10).all()
    
    today = datetime.now().date()
    overdue_transactions = Transaction.query.filter(
        Transaction.owner_id == current_user.id,
        Transaction.due_date < today,
        Transaction.status != 'PAID'
    ).all()
    
    return render_template('index.html', 
                         total_sales=total_sales,
                         total_outstanding=total_outstanding,
                         total_customers=total_customers,
                         total_transactions=total_transactions,
                         recent_transactions=recent_transactions,
                         overdue_transactions=overdue_transactions,
                         now=date.today())

# Customer routes
@app.route('/customers')
@login_required
def customers():
    if current_user.role == UserRole.MASTER_ADMIN:
        return redirect(url_for('admin_dashboard'))
    
    search = request.args.get('search', '')
    query = Customer.query.filter_by(owner_id=current_user.id)
    
    if search:
        query = query.filter(
            or_(
                Customer.full_name.contains(search),
                Customer.phone_number.contains(search)
            )
        )
    
    customers_list = query.order_by(Customer.created_at.desc()).all()
    return render_template('customers.html', customers=customers_list, search=search)

@app.route('/customer/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    if current_user.role == UserRole.MASTER_ADMIN:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        customer = Customer(
            owner_id=current_user.id,
            full_name=request.form['full_name'],
            phone_number=request.form['phone_number'],
            address=request.form.get('address', ''),
            guarantor_name=request.form.get('guarantor_name', ''),
            guarantor_phone=request.form.get('guarantor_phone', '')
        )
        db.session.add(customer)
        db.session.commit()
        flash('Customer added successfully!', 'success')
        return redirect(url_for('customers'))
    
    return render_template('customer_form.html')

@app.route('/customer/<int:id>')
@login_required
def customer_profile(id):
    if current_user.role == UserRole.MASTER_ADMIN:
        return redirect(url_for('admin_dashboard'))
    
    customer = Customer.query.filter_by(id=id, owner_id=current_user.id).first_or_404()
    transactions = Transaction.query.filter_by(customer_id=id, owner_id=current_user.id).order_by(Transaction.created_at.desc()).all()
    return render_template('customer_profile.html', customer=customer, transactions=transactions)

# Product routes
@app.route('/products')
@login_required
def products():
    if current_user.role == UserRole.MASTER_ADMIN:
        return redirect(url_for('admin_dashboard'))
    
    products_list = Product.query.filter_by(owner_id=current_user.id).all()
    return render_template('products.html', products=products_list)

@app.route('/product/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if current_user.role == UserRole.MASTER_ADMIN:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        product = Product(
            owner_id=current_user.id,
            name=request.form['name'],
            imei=request.form.get('imei', ''),
            price=float(request.form['price']),
            stock_quantity=int(request.form.get('stock_quantity', 1))
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('products'))
    
    return render_template('product_form.html')

@app.route('/product/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    if current_user.role == UserRole.MASTER_ADMIN:
        return redirect(url_for('admin_dashboard'))
    
    product = Product.query.filter_by(id=id, owner_id=current_user.id).first_or_404()
    if request.method == 'POST':
        product.name = request.form['name']
        product.imei = request.form.get('imei', '')
        product.price = float(request.form['price'])
        product.stock_quantity = int(request.form.get('stock_quantity', 1))
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('products'))
    
    return render_template('product_form.html', product=product)

# Transaction routes
@app.route('/transactions')
@login_required
def transactions():
    if current_user.role == UserRole.MASTER_ADMIN:
        return redirect(url_for('admin_dashboard'))
    
    filter_status = request.args.get('status', '')
    query = Transaction.query.filter_by(owner_id=current_user.id)
    
    if filter_status:
        query = query.filter_by(status=filter_status)
    
    transactions_list = query.order_by(Transaction.created_at.desc()).all()
    return render_template('transactions.html', transactions=transactions_list, filter_status=filter_status, now=date.today())

@app.route('/transaction/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if current_user.role == UserRole.MASTER_ADMIN:
        return redirect(url_for('admin_dashboard'))
    
    customers = Customer.query.filter_by(owner_id=current_user.id).all()
    products = Product.query.filter_by(owner_id=current_user.id).all()
    
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        product_id = request.form['product_id']
        phone_imei = request.form.get('phone_imei', '')
        total_price = float(request.form['total_price'])
        amount_paid = float(request.form.get('amount_paid', 0))
        payment_type = request.form['payment_type']
        due_date = request.form.get('due_date')
        
        if amount_paid > total_price:
            flash('Amount paid cannot be more than total price!', 'danger')
            return redirect(url_for('add_transaction'))
        
        balance = total_price - amount_paid
        
        if amount_paid == total_price:
            status = 'PAID'
        elif amount_paid > 0:
            status = 'PARTIAL'
        else:
            status = 'UNPAID'
        
        transaction = Transaction(
            owner_id=current_user.id,
            customer_id=customer_id,
            product_id=product_id,
            phone_imei=phone_imei,
            total_price=total_price,
            amount_paid=amount_paid,
            balance=balance,
            payment_type=payment_type,
            status=status,
            due_date=datetime.strptime(due_date, '%Y-%m-%d').date() if due_date else None
        )
        
        db.session.add(transaction)
        
        product = Product.query.get(product_id)
        if product and product.stock_quantity > 0:
            product.stock_quantity -= 1
        
        db.session.commit()
        flash('Transaction created successfully!', 'success')
        return redirect(url_for('transactions'))
    
    return render_template('transaction_form.html', customers=customers, products=products)

@app.route('/transaction/<int:id>/add-payment', methods=['GET', 'POST'])
@login_required
def add_payment(id):
    if current_user.role == UserRole.MASTER_ADMIN:
        return redirect(url_for('admin_dashboard'))
    
    transaction = Transaction.query.filter_by(id=id, owner_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        amount = float(request.form['amount'])
        notes = request.form.get('notes', '')
        
        if amount <= 0:
            flash('Payment amount must be greater than zero!', 'danger')
            return redirect(url_for('add_payment', id=id))
        
        if amount > transaction.balance:
            flash(f'Payment cannot exceed remaining balance of ₦{transaction.balance:,.2f}!', 'danger')
            return redirect(url_for('add_payment', id=id))
        
        payment = Payment(
            transaction_id=id,
            amount_paid=amount,
            notes=notes
        )
        
        db.session.add(payment)
        transaction.balance -= amount
        
        if transaction.balance <= 0:
            transaction.status = 'PAID'
            transaction.balance = 0
        else:
            transaction.status = 'PARTIAL'
        
        db.session.commit()
        flash(f'Payment of ₦{amount:,.2f} recorded successfully!', 'success')
        return redirect(url_for('customer_profile', id=transaction.customer_id))
    
    return render_template('add_payment.html', transaction=transaction)

@app.route('/receipt/<int:id>')
@login_required
def receipt(id):
    if current_user.role == UserRole.MASTER_ADMIN:
        return redirect(url_for('admin_dashboard'))
    
    transaction = Transaction.query.filter_by(id=id, owner_id=current_user.id).first_or_404()
    return render_template('receipt.html', transaction=transaction)

@app.route('/export/customers')
@login_required
def export_customers():
    if current_user.role == UserRole.MASTER_ADMIN:
        return redirect(url_for('admin_dashboard'))
    
    customers = Customer.query.filter_by(owner_id=current_user.id).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Full Name', 'Phone Number', 'Address', 'Guarantor Name', 'Guarantor Phone', 'Created At'])
    
    for customer in customers:
        writer.writerow([
            customer.id, customer.full_name, customer.phone_number,
            customer.address, customer.guarantor_name, customer.guarantor_phone,
            customer.created_at
        ])
    
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=customers.csv'
    response.headers['Content-type'] = 'text/csv'
    return response

@app.route('/export/transactions')
@login_required
def export_transactions():
    if current_user.role == UserRole.MASTER_ADMIN:
        return redirect(url_for('admin_dashboard'))
    
    transactions = Transaction.query.filter_by(owner_id=current_user.id).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Customer', 'Product', 'IMEI', 'Total Price', 'Amount Paid', 'Balance', 'Status', 'Due Date', 'Created At'])
    
    for transaction in transactions:
        writer.writerow([
            transaction.id, transaction.customer.full_name, transaction.product.name,
            transaction.phone_imei or '',
            transaction.total_price, transaction.amount_paid, transaction.balance,
            transaction.status, transaction.due_date, transaction.created_at
        ])
    
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=transactions.csv'
    response.headers['Content-type'] = 'text/csv'
    return response

@app.route('/backup')
@login_required
def backup():
    if current_user.role == UserRole.MASTER_ADMIN:
        return redirect(url_for('admin_dashboard'))
    
    return render_template('backup.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)