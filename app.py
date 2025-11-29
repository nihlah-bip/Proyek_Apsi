from flask import Flask, render_template, request, redirect, url_for, session, flash
import logging
import os
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func
from functools import wraps

app = Flask(__name__)

# ==========================================
# WAJIB DITAMBAHKAN AGAR LOGIN BISA JALAN
# ==========================================
app.secret_key = 'kunci_rahasia_lembah_fitness_123' 

# Konfigurasi Database
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "lembah_fitness.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ==========================================
# DECORATOR UNTUK PROTEKSI ROUTE
# ==========================================
def login_required(f):
    """Decorator untuk memastikan user sudah login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('select_role'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Decorator untuk memastikan user memiliki role tertentu"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Silakan login terlebih dahulu.', 'warning')
                return redirect(url_for('select_role'))
            
            if session.get('role') not in roles:
                flash(f'Akses ditolak. Halaman ini hanya untuk {", ".join(roles)}.', 'danger')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Compute absolute DB path for debugging; helpful to detect which sqlite file is used at runtime
DB_ABS_PATH = None
try:
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if db_uri.startswith('sqlite:///'):
        path_part = db_uri.replace('sqlite:///', '')
        DB_ABS_PATH = os.path.abspath(path_part)
    else:
        DB_ABS_PATH = db_uri
except Exception:
    DB_ABS_PATH = 'unknown'

# One-time helper: if the manager password needs to be reset automatically
# (useful when working in local dev and the server is restarted), perform
# the reset once and write a sentinel file so we don't overwrite later.
try:
    sentinel = None
    if DB_ABS_PATH and DB_ABS_PATH != 'unknown':
        sentinel = os.path.join(os.path.dirname(DB_ABS_PATH), '.manager_reset_done')
        # Only run once per environment (create sentinel file afterwards)
        if not os.path.exists(sentinel):
            try:
                # perform reset to default password 'lembahfitness' (as requested)
                db_path = DB_ABS_PATH
                if isinstance(db_path, str) and db_path.startswith('sqlite:///'):
                    db_path = db_path.replace('sqlite:///', '')
                db_path = os.path.abspath(db_path)
                from werkzeug.security import generate_password_hash
                import sqlite3
                if os.path.exists(db_path):
                    conn = sqlite3.connect(db_path)
                    cur = conn.cursor()
                    cur.execute("SELECT id FROM user WHERE username = ?", ('manager',))
                    r = cur.fetchone()
                    if r:
                        new_hash = generate_password_hash('lembahfitness', method='scrypt')
                        cur.execute("UPDATE user SET password = ? WHERE id = ?", (new_hash, r[0]))
                        conn.commit()
                        app.logger.info('One-time: manager password reset to default (lembahfitness)')
                    else:
                        app.logger.info('One-time: manager user not found; no reset performed')
                    conn.close()
                    # mark sentinel so this does not run again
                    try:
                        open(sentinel, 'w').close()
                    except Exception:
                        app.logger.exception('Failed to write sentinel file for manager reset')
            except Exception:
                app.logger.exception('Failed to perform one-time manager password reset')
except Exception:
    pass

# Configure logger
app.logger.setLevel(logging.DEBUG)
app.logger.info(f"Flask app started. Using DB: {DB_ABS_PATH}")


@app.context_processor
def inject_sidebar_members():
    # Provide a short list of members to the templates for the sidebar
    try:
        # Sidebar should list only Personal Trainer members (they need quick access)
        members = Member.query.filter_by(program='Personal Trainer').order_by(Member.nama_lengkap.asc()).limit(30).all()
    except Exception:
        members = []
    return dict(sidebar_members=members)


@app.context_processor
def inject_sidebar_trainers():
    # Provide list of personal trainers (users with role 'pt') for sidebar
    try:
        trainers = User.query.filter_by(role='pt').order_by(User.username.asc()).limit(30).all()
    except Exception:
        trainers = []
    return dict(sidebar_trainers=trainers)

# ==========================================
# 2. DEFINISI MODEL (TABEL DATABASE)
# ==========================================

# Tabel User (Login)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'manager', 'admin', 'pt'


# Tabel Member (Data Pelanggan Lengkap)
class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_lengkap = db.Column(db.String(100), nullable=False)
    program = db.Column(db.String(50), nullable=False)  # Insidental / Reguler / Personal Trainer

    # Data Umum (Untuk Reguler & PT)
    no_wa = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    alamat = db.Column(db.Text, nullable=True)
    ttl = db.Column(db.Date, nullable=True)  # Tanggal Lahir

    # Data Fisik (Khusus PT)
    tinggi_badan = db.Column(db.Integer, nullable=True)
    berat_badan = db.Column(db.Integer, nullable=True)
    goals = db.Column(db.String(50), nullable=True)  # Muscle Gain / Bulking / Cutting

    # Personal trainer yang dipilih (khusus program Personal Trainer)
    trainer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # User account untuk login member (optional - untuk member yang punya akun)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Status Membership
    status = db.Column(db.String(20), default='Aktif')
    tgl_daftar = db.Column(db.Date, default=datetime.utcnow)
    tgl_habis = db.Column(db.Date, nullable=False)

    # Relasi
    pembayaran = db.relationship('Pembayaran', backref='member', lazy=True)
    latihan = db.relationship('Latihan', backref='member', lazy=True)
    # Relationship to User (personal trainer)
    trainer = db.relationship('User', foreign_keys=[trainer_id], backref='clients', lazy=True)
    # Relationship to User (member account)
    user_account = db.relationship('User', foreign_keys=[user_id], backref='member_profile', lazy=True)

    @property
    def personal_trainer(self):
        try:
            return self.trainer.username if self.trainer else None
        except Exception:
            return None


# Tabel Latihan (Progres)
class Latihan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    tanggal = db.Column(db.Date, default=datetime.utcnow)
    berat_badan = db.Column(db.Float, nullable=True)
    bmi = db.Column(db.Float, nullable=True)
    jadwal_teks = db.Column(db.String(200), nullable=True)


# Tabel Pembayaran
class Pembayaran(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    tanggal_bayar = db.Column(db.Date, default=datetime.utcnow)
    nominal = db.Column(db.Integer, nullable=False)
    keterangan = db.Column(db.String(100), nullable=True)


# Tabel untuk menyimpan riwayat analisis antrian
class QueueAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment = db.Column(db.String(100), nullable=False)
    lam = db.Column(db.Float, nullable=False)  # lambda
    mu = db.Column(db.Float, nullable=False)   # mu
    m = db.Column(db.Integer, nullable=False)
    rho = db.Column(db.Float, nullable=True)
    Lq = db.Column(db.Float, nullable=True)
    Wq = db.Column(db.Float, nullable=True)
    W = db.Column(db.Float, nullable=True)
    recommendation = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Tabel untuk menyimpan preset μ per equipment (bisa diedit lewat UI)
class EquipmentPreset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment = db.Column(db.String(120), unique=True, nullable=False)
    mu_default = db.Column(db.Float, nullable=False)


# Tabel untuk menyimpan riwayat reset password (hanya catat, bukan autentikasi)
class PasswordResetLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    # Do NOT persist plaintext passwords. Keep this column nullable for
    # backward-compatibility with existing DBs; application will no
    # longer write plaintext here.
    plain_password = db.Column(db.String(200), nullable=True)
    created_by = db.Column(db.Integer, nullable=True)  # admin id who reset
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



# ==========================================
# 3. ROUTE (JALUR HALAMAN)
# ==========================================

# --- BAGIAN PUBLIC (MEMBER/PENGUNJUNG) ---
@app.route('/')
def index():
    # Jika sudah login, redirect ke dashboard sesuai role
    if 'user_id' in session:
        role = session.get('role')
        if role == 'pt':
            return redirect(url_for('pt_dashboard'))
        elif role == 'manager':
            return redirect(url_for('owner_dashboard'))
        elif role == 'admin':
            return redirect(url_for('admin_dashboard'))
    
    return render_template('public/home.html')


@app.route('/about')
def about():
    return render_template('public/about.html')


@app.route('/courses')
def courses():
    return render_template('public/courses.html')


@app.route('/pricing')
def pricing():
    return render_template('public/pricing.html')


@app.route('/gallery')
def gallery():
    return render_template('public/gallery.html')


@app.route('/blog')
def blog():
    return render_template('public/blog.html')


@app.route('/blog/details')
def blog_details():
    return render_template('public/blog_details.html')


@app.route('/contact')
def contact():
    return render_template('public/contact.html')

# @app.route('/login')
# def login():
#     return render_template('login/login.html')


@app.route('/services')
def services():
    return render_template('public/services.html')


@app.route('/elements')
def elements():
    return render_template('public/elements.html')


# --- HALAMAN MEMBER (AREA KHUSUS MEMBER) ---
@app.route('/member')
def member_dashboard_public():
    # Untuk sementara: akses via /member?id=<member_id>
    member_id = request.args.get('id')
    if not member_id:
        return "Gunakan /member?id=<member_id> untuk melihat halaman member sementara.", 400

    try:
        member_id = int(member_id)
    except Exception:
        return "ID member tidak valid.", 400

    member = Member.query.get(member_id)
    if not member:
        return "Member tidak ditemukan.", 404

    # Ambil log latihan terbaru (limit 20)
    logs = Latihan.query.filter_by(member_id=member.id).order_by(Latihan.tanggal.desc()).limit(20).all()

    today = datetime.utcnow().date()
    is_expired = False
    if member.tgl_habis and member.tgl_habis < today:
        is_expired = True

    return render_template('member/dashboard.html', member=member, logs=logs, is_expired=is_expired)


@app.route('/member/profile')
@role_required('member')
def member_profile():
    # Member can view their own profile
    user_id = session.get('user_id')
    if not user_id:
        flash('Silakan login terlebih dahulu.', 'warning')
        return redirect(url_for('member_login_page'))

    member = Member.query.filter_by(user_id=user_id).first()
    if not member:
        flash('Profil member tidak ditemukan. Hubungi admin.', 'danger')
        return redirect(url_for('member_login_page'))

    return render_template('member/profile.html', member=member)

# --- ROUTE PORTAL PEMILIHAN ROLE ---
@app.route('/admin/select-role')
def select_role():
    return render_template('admin/select_role.html')


# --- ROUTE LOGIN MEMBER (PUBLIC) ---
@app.route('/member/login', methods=['GET', 'POST'])
def member_login_page():
    """Halaman login khusus untuk member dari website public"""
    return render_template('public/member_login.html')

@app.route('/member/login-process', methods=['POST'])
def member_login():
    """Proses login member dari public website"""
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Cek user dengan role member
    user = User.query.filter_by(username=username, role='member').first()
    
    if user and check_password_hash(user.password, password):
        # Cari member profile yang linked
        member = Member.query.filter_by(user_id=user.id).first()
        
        if member:
            # Login berhasil
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['member_id'] = member.id
            
            flash(f'Selamat datang, {member.nama_lengkap}!', 'success')
            return redirect(url_for('member_dashboard', id=member.id))
        else:
            flash('Data member tidak ditemukan. Hubungi admin gym.', 'danger')
    else:
        flash('Username atau Password salah! Pastikan Anda member Personal Trainer.', 'danger')
    
    return redirect(url_for('member_login_page'))


# --- ROUTE LOGIN (PINTU MASUK) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Ambil parameter role dari URL (jika ada)
    expected_role = request.args.get('role')
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Cek database
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            # Validasi role jika ada expected_role
            if expected_role and user.role != expected_role:
                flash(f'Akses ditolak! Akun Anda bukan {expected_role}.', 'danger')
                return redirect(url_for('login', role=expected_role))
            
            session.clear() # Bersihkan sesi lama
            # Simpan data login baru
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            
            # Redirect berdasarkan role
            if user.role == 'pt':
                return redirect(url_for('pt_dashboard'))
            elif user.role == 'manager':
                return redirect(url_for('owner_dashboard'))
            elif user.role == 'member':
                # Cari member profile yang linked dengan user ini
                member = Member.query.filter_by(user_id=user.id).first()
                if member:
                    return redirect(url_for('member_dashboard', id=member.id))
                else:
                    flash('Data member tidak ditemukan. Hubungi admin.', 'danger')
                    return redirect(url_for('login'))
            else:  # admin atau role lain
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Username atau Password Salah!', 'danger')
    
    # GET request - tampilkan form login dengan info role
    role_display = {
        'admin': 'Administrator',
        'pt': 'Personal Trainer',
        'manager': 'Pemilik / Manager'
    }.get(expected_role, 'Staff')
    
    return render_template('admin/login.html', expected_role=expected_role, role_display=role_display)

# --- ROUTE LOGOUT ---
@app.route('/logout')
def logout():
    # Cek apakah member yang logout
    is_member = session.get('role') == 'member'
    session.clear()
    
    # Redirect berdasarkan tipe user
    if is_member:
        flash('Anda telah logout. Terima kasih!', 'success')
        return redirect(url_for('index'))
    else:
        return redirect(url_for('select_role'))

# --- BAGIAN ADMIN (DASHBOARD & SISTEM) ---
@app.route('/admin')
@login_required
def admin_dashboard():
    """
    Dashboard admin dengan data:
    - pemasukan bulanan (tabel Pembayaran) tahun ini
    - jumlah pendaftaran per program per bulan tahun ini
    - pemasukan bulan ini & total setahun (untuk kartu kecil)
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))

    today = datetime.utcnow().date()
    year = today.year
    year_str = str(year)

    # Label bulan untuk chart
    month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun',
                    'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']

    # ===== 1. Pemasukan bulanan (Pembayaran) =====
    income_per_month = [0] * 12  # index 0 = Jan

    income_rows = (
        db.session.query(
            func.strftime('%m', Pembayaran.tanggal_bayar).label('month'),
            func.sum(Pembayaran.nominal)
        )
        .filter(func.strftime('%Y', Pembayaran.tanggal_bayar) == year_str)
        .group_by('month')
        .all()
    )

    for month_str, total in income_rows:
        idx = int(month_str) - 1
        income_per_month[idx] = int(total or 0)

    current_month_index = today.month - 1
    month_income_value = income_per_month[current_month_index]
    year_income_value = sum(income_per_month)

    # ===== 2. Pendaftaran member per program per bulan =====
    programs = ['Insidental', 'Reguler', 'Personal Trainer']
    registrations_per_program = {p: [0] * 12 for p in programs}

    reg_rows = (
        db.session.query(
            func.strftime('%m', Member.tgl_daftar).label('month'),
            Member.program,
            func.count(Member.id)
        )
        .filter(func.strftime('%Y', Member.tgl_daftar) == year_str)
        .group_by('month', Member.program)
        .all()
    )

    for month_str, program, count in reg_rows:
        idx = int(month_str) - 1
        if program in registrations_per_program:
            registrations_per_program[program][idx] = int(count or 0)

    return render_template(
        'admin/dashboard.html',
        labels=month_labels,
        income_data=income_per_month,
        registrations_data=registrations_per_program,
        month_income=month_income_value,
        year_income=year_income_value,
        year=year
    )


# --- DASHBOARD KHUSUS OWNER/MANAGER ---
@app.route('/owner')
@role_required('manager')
def owner_dashboard():
    """
    Dashboard khusus untuk pemilik/manager dengan analisis bisnis lengkap
    """
    if 'user_id' not in session or session.get('role') != 'manager':
        flash('Akses ditolak. Hanya untuk Manager.', 'warning')
        return redirect(url_for('login'))

    today = datetime.utcnow().date()
    year = today.year
    year_str = str(year)

    # Label bulan untuk chart
    month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun',
                    'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']

    # ===== 1. Pemasukan bulanan =====
    income_per_month = [0] * 12

    income_rows = (
        db.session.query(
            func.strftime('%m', Pembayaran.tanggal_bayar).label('month'),
            func.sum(Pembayaran.nominal)
        )
        .filter(func.strftime('%Y', Pembayaran.tanggal_bayar) == year_str)
        .group_by('month')
        .all()
    )

    for month_str, total in income_rows:
        idx = int(month_str) - 1
        income_per_month[idx] = int(total or 0)

    current_month_index = today.month - 1
    month_income_value = income_per_month[current_month_index]
    year_income_value = sum(income_per_month)

    # ===== 2. Pendaftaran member per program =====
    programs = ['Insidental', 'Reguler', 'Personal Trainer']
    registrations_per_program = {p: [0] * 12 for p in programs}

    reg_rows = (
        db.session.query(
            func.strftime('%m', Member.tgl_daftar).label('month'),
            Member.program,
            func.count(Member.id)
        )
        .filter(func.strftime('%Y', Member.tgl_daftar) == year_str)
        .group_by('month', Member.program)
        .all()
    )

    for month_str, program, count in reg_rows:
        idx = int(month_str) - 1
        if program in registrations_per_program:
            registrations_per_program[program][idx] = int(count or 0)

    # ===== 3. Total member per program (untuk pie chart) =====
    program_counts = {}
    for prog in programs:
        count = Member.query.filter_by(program=prog).count()
        program_counts[prog] = count

    # ===== 4. Statistik tambahan =====
    active_members = Member.query.filter(Member.tgl_habis >= today).count()
    total_trainers = User.query.filter_by(role='pt').count()

    return render_template(
        'admin/dashboard_owner.html',
        labels=month_labels,
        income_data=income_per_month,
        registrations_data=registrations_per_program,
        program_counts=program_counts,
        month_income=month_income_value,
        year_income=year_income_value,
        active_members=active_members,
        total_trainers=total_trainers,
        year=year
    )


# --- HALAMAN MANAJEMEN MEMBER ---
@app.route('/admin/members')
@role_required('admin')
def manage_members():
    # Ambil semua data member, urutkan dari yang paling baru daftar
    # Include all members in the management table so admin can see active/non-active for everyone
    all_members = Member.query.order_by(Member.id.desc()).all()

    # Kirim tanggal hari ini agar HTML bisa menghitung sisa hari aktif
    today = datetime.utcnow().date()

    return render_template(
        'admin/manage_members.html',
        members=all_members,
        today_date=today
    )


# --- VIEW UNTUK MANAGER: baca-only daftar member ---
@app.route('/manager/members')
@role_required('manager')
def manager_members():
    # Manager sees a read-only member list (no create/delete)
    all_members = Member.query.order_by(Member.id.desc()).all()
    today = datetime.utcnow().date()

    return render_template('admin/manager_members.html', members=all_members, today_date=today)


# HAPUS MEMBER
@app.route('/admin/members/delete/<int:member_id>', methods=['POST'])
@role_required('admin', 'manager')
def delete_member(member_id):
    member = Member.query.get_or_404(member_id)

    # Hapus dulu data yang berelasi (Latihan & Pembayaran)
    Latihan.query.filter_by(member_id=member.id).delete()
    Pembayaran.query.filter_by(member_id=member.id).delete()

    # Hapus member-nya
    db.session.delete(member)
    db.session.commit()

    return redirect(url_for('manage_members'))


# --- HALAMAN INPUT PEMBAYARAN (KASIR) ---
@app.route('/admin/payments', methods=['GET', 'POST'])
@role_required('admin', 'manager')
def payments():
    if request.method == 'POST':
        # Read form safely and support the frontend naming
        member_id = request.form.get('member_id')
        nominal_raw = request.form.get('nominal', '0')
        keterangan = request.form.get('keterangan', '')

        # Frontend provides masa_aktif as two fields: value and unit
        masa_value = request.form.get('masa_aktif_value')
        masa_unit = request.form.get('masa_aktif_unit', 'Bulan')

        # Normalise and validate
        try:
            nominal = int(nominal_raw) if nominal_raw not in (None, '') else 0
        except Exception:
            nominal = 0

        try:
            member_id = int(member_id) if member_id else None
        except Exception:
            member_id = None

        # Determine tambahan period in days
        # Default to 0 (no extension) when not provided
        try:
            masa_val_int = int(masa_value) if masa_value not in (None, '') else 0
        except Exception:
            masa_val_int = 0

        # Convert masa into days for timedelta calculation
        if masa_unit == 'Hari':
            tambahan_hari = masa_val_int
        else:
            # treat as months (approx 30 days per month)
            tambahan_hari = masa_val_int * 30

        # Basic validation
        if not member_id:
            flash('Pilih member yang valid.', 'danger')
            return redirect(url_for('payments'))


        # Simpan ke Tabel Pembayaran (Log Transaksi)
        bayar_baru = Pembayaran(
            member_id=member_id,
            nominal=nominal,
            keterangan=keterangan,
            tanggal_bayar=datetime.utcnow()
        )
        db.session.add(bayar_baru)

        # Update tanggal habis member
        member = Member.query.get(member_id)
        today = datetime.utcnow().date()

        if member.tgl_habis is None or member.tgl_habis < today:
            base_date = today
        else:
            base_date = member.tgl_habis

        # If tambahan_hari is 0, keep existing expiry (but ensure status)
        if tambahan_hari > 0:
            new_expired_date = base_date + timedelta(days=tambahan_hari)
            member.tgl_habis = new_expired_date

        # Ensure member is marked active after payment
        member.status = 'Aktif'

        db.session.commit()

        return redirect(url_for('payments'))

    # GET: tampilkan halaman pembayaran
    all_members = Member.query.order_by(Member.nama_lengkap.asc()).all()
    history = Pembayaran.query.order_by(Pembayaran.id.desc()).limit(10).all()

    return render_template(
        'admin/payments.html',
        members=all_members,
        history_pembayaran=history
    )


@app.route('/admin/payments/clear', methods=['POST'])
@role_required('admin', 'manager')
def clear_payments():
    """Hapus semua riwayat pembayaran dari tabel Pembayaran.
    Route ini hanya dapat diakses oleh admin atau manager dan dijalankan
    melalui form POST dari halaman pembayaran dengan konfirmasi.
    """
    try:
        # Delete all rows in Pembayaran table
        num = db.session.query(Pembayaran).delete()
        db.session.commit()
        flash(f'Semua riwayat ({num}) transaksi berhasil dihapus.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.exception('Gagal menghapus riwayat pembayaran')
        flash('Gagal menghapus riwayat transaksi. Lihat log untuk detail.', 'danger')

    return redirect(url_for('payments'))


@app.route('/admin/training', methods=['GET', 'POST'])
@role_required('pt')
def training():
    # Halaman input latihan & progres (oleh trainer)
    # Access: PT, Manager, Admin
    if request.method == 'POST':
        # Ambil data dari form
        member_id = request.form.get('member_id')
        tanggal_input = request.form.get('tanggal')
        berat_badan = request.form.get('berat_badan')
        bmi = request.form.get('bmi')
        jadwal_teks = request.form.get('jadwal_teks')

        # Validasi minimal
        if not member_id or not tanggal_input:
            flash('Member dan tanggal harus diisi.', 'danger')
            return redirect(url_for('training'))

        # Member must be a Personal Trainer program member
        m_check = Member.query.get(member_id)
        if not m_check or m_check.program != 'Personal Trainer':
            flash('Hanya member dengan program Personal Trainer yang boleh dicatat latihannya di sini.', 'danger')
            return redirect(url_for('training'))

        # If the user is a PT, ensure the selected member belongs to them
        if session.get('role') == 'pt':
            if m_check.trainer_id != session.get('user_id'):
                flash('Anda hanya dapat mencatat latihan untuk member binaan Anda.', 'danger')
                return redirect(url_for('training'))

        try:
            tanggal = datetime.strptime(tanggal_input, '%Y-%m-%d').date()
        except Exception:
            tanggal = datetime.utcnow().date()

        # Konversi angka optional
        berat_val = float(berat_badan) if berat_badan else None
        bmi_val = float(bmi) if bmi else None

        latihan_baru = Latihan(
            member_id=member_id,
            tanggal=tanggal,
            berat_badan=berat_val,
            bmi=bmi_val,
            jadwal_teks=jadwal_teks
        )
        db.session.add(latihan_baru)
        db.session.commit()

        flash('Catatan latihan berhasil disimpan.', 'success')
        return redirect(url_for('training'))

    # GET -> tampilkan form
    if session.get('role') == 'pt':
        # show only clients assigned to this PT (and only PT-program members)
        # Ensure we compare integers (session may store strings)
        try:
            user_id_int = int(session.get('user_id'))
        except Exception:
            user_id_int = None

        members = Member.query.filter(
            Member.program == 'Personal Trainer',
            Member.trainer_id == user_id_int
        ).order_by(Member.nama_lengkap.asc()).all()

        logs = (
            db.session.query(Latihan)
            .join(Member, Latihan.member_id == Member.id)
            .filter(Member.trainer_id == user_id_int, Member.program == 'Personal Trainer')
            .order_by(Latihan.tanggal.desc())
            .limit(50)
            .all()
        )
    else:
        # For manager/admin, only list Personal Trainer program members in the training form
        members = Member.query.filter_by(program='Personal Trainer').order_by(Member.nama_lengkap.asc()).all()
        # Tampilkan log latihan terbaru (limit 50)
        logs = Latihan.query.order_by(Latihan.tanggal.desc()).limit(50).all()
    today = datetime.utcnow().date()
    # optionally preselect a member (from trainer members list link)
    selected_member = request.args.get('member_id')

    # If admin/manager opened training from a trainer's member link (selected_member provided),
    # show only that trainer's clients in the dropdown to match the PT view.
    trainer_context = None
    try:
        if selected_member and session.get('role') in ('manager', 'admin'):
            m_sel = Member.query.get(int(selected_member))
            if m_sel and m_sel.trainer_id:
                trainer_context = m_sel.trainer_id
                members = Member.query.filter_by(program='Personal Trainer', trainer_id=trainer_context).order_by(Member.nama_lengkap.asc()).all()
                # also restrict logs to this trainer's clients
                logs = (
                    db.session.query(Latihan)
                    .join(Member, Latihan.member_id == Member.id)
                    .filter(Member.trainer_id == trainer_context)
                    .order_by(Latihan.tanggal.desc())
                    .limit(50)
                    .all()
                )

        # Debug: log session and member list for troubleshooting
        member_ids = [m.id for m in members]
        app.logger.debug(f"/admin/training render: role={session.get('role')} user_id={session.get('user_id')} members_count={len(members)} member_ids={member_ids} trainer_context={trainer_context}")
    except Exception:
        app.logger.debug(f"/admin/training render: unable to enumerate members; role={session.get('role')} user_id={session.get('user_id')}")

    return render_template('admin/training.html', members=members, logs=logs, today=today, selected_member=selected_member, trainer_context=trainer_context)


@app.route('/admin/training/delete/<int:latihan_id>', methods=['POST'])
def delete_latihan(latihan_id):
    # Protect route: must be logged in
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu.', 'warning')
        return redirect(url_for('login'))

    latihan = Latihan.query.get_or_404(latihan_id)

    role = session.get('role')
    # Convert session user_id to int for safe comparison
    try:
        user_id_int = int(session.get('user_id'))
    except Exception:
        user_id_int = None

    # Permission: PT can only delete their own client's logs; manager/admin can delete any
    if role == 'pt':
        # ensure the latihan belongs to a member of this PT
        member = latihan.member
        if not member or member.trainer_id != user_id_int:
            flash('Akses ditolak. Anda hanya dapat menghapus catatan untuk member binaan Anda.', 'warning')
            return redirect(url_for('training'))
    elif role not in ('manager', 'admin'):
        flash('Akses ditolak.', 'warning')
        return redirect(url_for('training'))

    try:
        db.session.delete(latihan)
        db.session.commit()
        flash('Catatan latihan berhasil dihapus.', 'success')
    except Exception:
        db.session.rollback()
        flash('Gagal menghapus catatan. Cek log server.', 'danger')

    return redirect(url_for('training'))


# --- FITUR ADMIN/MANAGER: KELOLA STAFF (READ & CREATE) ---
# Halaman dapat diakses oleh Admin dan Manager. Password terakhir dan
# tindakan reset hanya terlihat/tersedia untuk Admin (template sudah
# men-guard bagian sensitif berdasarkan `session.role`).
@app.route('/admin/staff', methods=['GET', 'POST'])
@role_required('admin', 'manager')
def manage_staff():
    # Jika admin mengakses route lama, arahkan ke halaman baru `/admin/pegawai`
    if session.get('role') == 'admin':
        return redirect(url_for('admin_pegawai'))

    # LOGIKA TAMBAH STAFF BARU (CREATE)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        # Security: only a manager may create another manager account
        if role == 'manager' and session.get('role') != 'manager':
            flash('Anda tidak berhak membuat akun Manager.', 'danger')
            return redirect(url_for('manage_staff'))




        # Cek apakah username sudah ada?
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username sudah dipakai! Ganti yang lain.', 'danger')
        else:
            # Hash password biar aman
            hashed_pw = generate_password_hash(password)
            new_user = User(username=username, password=hashed_pw, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash('Akun berhasil dibuat!', 'success')
        
        return redirect(url_for('manage_staff'))

    # TAMPILKAN TABEL STAFF (READ)
    all_users = User.query.filter(User.role != 'member').order_by(User.role.asc()).all()

    # Build last-password info map for admin and manager users (sensitive)
    # We no longer persist plaintext for new resets. For compatibility we
    # surface either the legacy plaintext (if present in older logs) or
    # the timestamp of the last reset event so managers/admins can see when
    # a reset occurred.
    last_pw = {}
    if session.get('role') in ('admin', 'manager'):
        user_ids = [u.id for u in all_users]
        # Get all logs ordered by time descending
        logs = PasswordResetLog.query.filter(PasswordResetLog.user_id.in_(user_ids)).order_by(PasswordResetLog.created_at.desc()).all()
        
        for l in logs:
            if l.user_id not in last_pw:
                # Store the most recent timestamp
                last_pw[l.user_id] = {
                    'plain': None,
                    'at': l.created_at
                }
            
            # Try to find a legacy plaintext password (not empty)
            # Keep looking through older logs until we find one with plain_password
            plain_pwd = getattr(l, 'plain_password', None)
            if plain_pwd and plain_pwd.strip() and last_pw[l.user_id]['plain'] is None:
                last_pw[l.user_id]['plain'] = plain_pwd

    return render_template('admin/manage_staff.html', users=all_users, last_passwords=last_pw)


# Route to reset a staff password (admin and manager)
@app.route('/admin/staff/reset-password/<int:id>', methods=['POST'])
@role_required('admin', 'manager')
def reset_staff_password(id):
    # Do not allow resetting the main manager account or yourself via this form
    user = User.query.get_or_404(id)
    if user.username == 'manager' or user.username == session.get('username'):
        flash('Aksi tidak diizinkan untuk akun ini.', 'warning')
        return redirect(url_for('manage_staff'))

    # If admin provides a password, use it. If left blank, generate a secure temporary one.
    raw_pw = request.form.get('new_password', '') or ''
    show_plain = request.form.get('show_plain') == '1'

    generated = False
    if not raw_pw:
        # generate a secure, reasonably friendly password
        import secrets, string
        alphabet = string.ascii_letters + string.digits
        raw_pw = ''.join(secrets.choice(alphabet) for _ in range(10))
        generated = True

    try:
        # Use scrypt to be consistent with other entries
        user.password = generate_password_hash(raw_pw, method='scrypt')

        # Log the reset event but DO NOT persist the plaintext password.
        # For audit, we keep a record that a reset happened and who performed it.
        log = PasswordResetLog(user_id=user.id, plain_password='', created_by=session.get('user_id'))
        db.session.add(log)
        db.session.commit()

        # If admin requested to display plaintext or we generated it, show it once
        if show_plain or generated:
            flash(f"Password untuk {user.username}: {raw_pw} (tampil sekali)", 'info')
        else:
            flash(f'Password untuk {user.username} telah di-set.', 'success')

    except Exception:
        db.session.rollback()
        app.logger.exception('Gagal mereset password')
        flash('Gagal mengatur password. Cek log server.', 'danger')

    return redirect(url_for('manage_staff'))


@app.route('/admin/trainers')
@role_required('manager')
def manage_trainers():
    """List all personal trainers"""
    trainers = User.query.filter_by(role='pt').all()
    # attach clients count
    trainer_rows = []
    for t in trainers:
        clients_count = Member.query.filter_by(trainer_id=t.id).count()
        trainer_rows.append(type('T', (), {'id': t.id, 'username': t.username, 'clients_count': clients_count}))

    return render_template('admin/personal_trainers.html', trainers=trainer_rows)


@app.route('/admin/trainers/delete/<int:id>', methods=['POST'])
@role_required('manager')
def delete_trainer(id):

    pt = User.query.get_or_404(id)
    if pt.role != 'pt':
        flash('Bukan Personal Trainer.', 'warning')
        return redirect(url_for('manage_trainers'))

    # Unassign clients first
    Member.query.filter_by(trainer_id=pt.id).update({'trainer_id': None})
    db.session.delete(pt)
    db.session.commit()
    flash('Personal Trainer dihapus dan kliennya dilepas.', 'success')
    return redirect(url_for('manage_trainers'))

# --- FITUR HAPUS STAFF (DELETE) ---
@app.route('/admin/staff/delete/<int:id>', methods=['POST'])
@role_required('manager')
def delete_staff(id):
    
    user_to_delete = User.query.get_or_404(id)
    
    # Mencegah manager menghapus dirinya sendiri
    if user_to_delete.username == session['username'] or user_to_delete.username == 'manager':
        flash('Tidak bisa menghapus akun utama!', 'warning')
    else:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash('Akun berhasil dihapus.', 'success')
        
    return redirect(url_for('manage_staff'))


# --- FITUR EDIT STAFF (UPDATE USERNAME & PASSWORD) ---
@app.route('/admin/staff/edit/<int:id>', methods=['POST'])
@role_required('manager')
def edit_staff(id):
    
    user_to_edit = User.query.get_or_404(id)
    
    # Mencegah manager mengedit akun manager utama atau dirinya sendiri
    if user_to_edit.username == 'manager':
        flash('Tidak bisa mengedit akun manager utama!', 'warning')
        return redirect(url_for('manage_staff'))
    
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', '').strip()
    
    if not username:
        flash('Username tidak boleh kosong!', 'danger')
        return redirect(url_for('manage_staff'))
    
    # Cek apakah username sudah digunakan oleh user lain
    existing_user = User.query.filter(User.username == username, User.id != id).first()
    if existing_user:
        flash(f'Username "{username}" sudah digunakan oleh user lain!', 'warning')
        return redirect(url_for('manage_staff'))
    
    # Update username
    old_username = user_to_edit.username
    user_to_edit.username = username
    
    # Update password jika diisi
    if password:
        user_to_edit.password = generate_password_hash(password)
        # Log password change (simpan plain_password agar bisa dilihat admin)
        pw_log = PasswordResetLog(
            user_id=user_to_edit.id,
            plain_password=password,  # Simpan password asli
            created_by=session.get('user_id'),
            created_at=datetime.utcnow()
        )
        db.session.add(pw_log)
    
    # Update role jika diubah
    if role and role in ['admin', 'pt', 'manager']:
        user_to_edit.role = role
    
    db.session.commit()
    
    flash(f'Akun "{old_username}" berhasil diupdate!', 'success')
    return redirect(url_for('manage_staff'))


# --- ADMIN-ONLY: Kelola Pegawai (staff CRUD) ---
@app.route('/admin/pegawai', methods=['GET', 'POST'])
@role_required('admin')
def admin_pegawai():
    """Admin-only page to list and create staff accounts (admin/pt/manager).
    This separates staff management from the manager-facing view.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        if not username or not role:
            flash('Username dan role wajib diisi.', 'danger')
            return redirect(url_for('admin_pegawai'))

        # disallow creating a manager unless a manager performs the action
        if role == 'manager' and session.get('role') != 'manager':
            flash('Pembuatan akun Manager dibatasi.', 'danger')
            return redirect(url_for('admin_pegawai'))

        existing = User.query.filter_by(username=username).first()
        if existing:
            flash('Username sudah ada.', 'warning')
            return redirect(url_for('admin_pegawai'))

        hashed = generate_password_hash(password or '')
        new_user = User(username=username, password=hashed, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash(f'Akun {username} dibuat.', 'success')
        return redirect(url_for('admin_pegawai'))

    # GET -> list staff (exclude members)
    staff_users = User.query.filter(User.role != 'member').order_by(User.role.asc(), User.username.asc()).all()
    return render_template('admin/pegawai.html', users=staff_users)


@app.route('/admin/pegawai/delete/<int:id>', methods=['POST'])
@role_required('admin')
def admin_pegawai_delete(id):
    user = User.query.get_or_404(id)

    # prevent deleting main manager account or self
    if user.username == 'manager' or user.username == session.get('username'):
        flash('Aksi tidak diizinkan pada akun ini.', 'warning')
        return redirect(url_for('admin_pegawai'))

    db.session.delete(user)
    db.session.commit()
    flash('Akun pegawai dihapus.', 'success')
    return redirect(url_for('admin_pegawai'))


# --- ADMIN: Kelola Akun Member (user.role == 'member') ---
@app.route('/admin/accounts/members', methods=['GET'])
@role_required('admin')
def admin_member_accounts():
    members_accounts = User.query.filter_by(role='member').order_by(User.id.desc()).all()

    # Build last-password info map for members
    last_pw = {}
    user_ids = [u.id for u in members_accounts]
    if user_ids:
        logs = PasswordResetLog.query.filter(PasswordResetLog.user_id.in_(user_ids)).order_by(PasswordResetLog.created_at.desc()).all()
        for l in logs:
            if l.user_id not in last_pw:
                last_pw[l.user_id] = {'plain': None, 'at': l.created_at}
            
            plain_pwd = getattr(l, 'plain_password', None)
            if plain_pwd and plain_pwd.strip() and last_pw[l.user_id]['plain'] is None:
                last_pw[l.user_id]['plain'] = plain_pwd

    return render_template('admin/member_accounts.html', users=members_accounts, last_passwords=last_pw)


@app.route('/admin/accounts/members/edit/<int:id>', methods=['POST'])
@role_required('admin')
def admin_member_accounts_edit(id):
    user = User.query.get_or_404(id)
    if user.role != 'member':
        flash('Hanya akun member yang bisa diedit di sini.', 'warning')
        return redirect(url_for('admin_member_accounts'))

    username = request.form.get('username')
    password = request.form.get('password')

    if not username:
        flash('Username tidak boleh kosong.', 'danger')
        return redirect(url_for('admin_member_accounts'))

    # Check duplicate username
    existing = User.query.filter(User.username == username, User.id != id).first()
    if existing:
        flash('Username sudah digunakan.', 'warning')
        return redirect(url_for('admin_member_accounts'))

    user.username = username
    
    if password:
        user.password = generate_password_hash(password)
        # Log password change
        pw_log = PasswordResetLog(
            user_id=user.id,
            plain_password=password,
            created_by=session.get('user_id'),
            created_at=datetime.utcnow()
        )
        db.session.add(pw_log)

    db.session.commit()
    flash('Akun member berhasil diupdate.', 'success')
    return redirect(url_for('admin_member_accounts'))


@app.route('/admin/accounts/members/delete/<int:id>', methods=['POST'])
@role_required('admin')
def admin_member_accounts_delete(id):
    user = User.query.get_or_404(id)
    if user.role != 'member':
        flash('Akun bukan member.', 'warning')
        return redirect(url_for('admin_member_accounts'))

    # also unlink member profile if exists
    Member.query.filter_by(user_id=user.id).update({'user_id': None})
    db.session.delete(user)
    db.session.commit()
    flash('Akun member dihapus.', 'success')
    return redirect(url_for('admin_member_accounts'))


@app.route('/admin/member/<int:member_id>')
@role_required('manager', 'admin', 'pt')
def admin_member_detail(member_id):
    member = Member.query.get_or_404(member_id)

    # Allow access if manager/admin, or if PT who owns this member
    role = session.get('role')
    if role == 'pt':
        if member.trainer_id != session.get('user_id'):
            flash('Akses ditolak. Hanya trainer yang membina member ini.', 'warning')
            return redirect(url_for('pt_dashboard'))
    
    logs = Latihan.query.filter_by(member_id=member.id).order_by(Latihan.tanggal.desc()).limit(50).all()

    return render_template('admin/member_detail.html', member=member, logs=logs)


@app.route('/admin/trainer/<int:trainer_id>')
@role_required('manager', 'admin', 'pt')
def admin_trainer_members(trainer_id):

    trainer = User.query.get_or_404(trainer_id)
    # Ambil member yang memilih trainer ini
    members = Member.query.filter_by(trainer_id=trainer.id).order_by(Member.nama_lengkap.asc()).all()

    return render_template('admin/trainer_members.html', trainer=trainer, members=members)

# ==========================================
# 4. INISIALISASI DATABASE
# ==========================================
with app.app_context():
    db.create_all()



# --- HALAMAN REGISTRASI & TRANSAKSI (ALL IN ONE) ---
@app.route('/admin/registrasi', methods=['GET', 'POST'])
@role_required('admin', 'manager')
def registrasi():
    if request.method == 'POST':
        app.logger.debug(f"Registrasi POST received. form keys: {list(request.form.keys())}")
        # 1. Ambil Data Dasar
        program = request.form['program']
        nama = request.form['nama']
        no_wa = request.form['no_wa']
        nominal = int(request.form['nominal'])  # Harga otomatis dari form
        
        # Ambil username & password member (hanya untuk PT)
        username_member = request.form.get('username_member')
        password_member = request.form.get('password_member')
        
        # Validasi username member tidak duplikat (hanya jika ada)
        if username_member:
            existing_user = User.query.filter_by(username=username_member).first()
            if existing_user:
                flash(f'Username "{username_member}" sudah dipakai! Gunakan username lain.', 'danger')
                trainers = User.query.filter_by(role='pt').all()
                return render_template('admin/registrasi.html', trainers=trainers)

        # 2. Siapkan Variabel Opsional
        gender = None
        alamat = None
        ttl_date = None
        tb = None
        bb = None
        goals = None
        personal_trainer = None  # <-- untuk program Personal Trainer

        # Tanggal habis default
        tgl_habis = datetime.utcnow().date()

        # 3. Logika Berdasarkan Program
        if program == 'Insidental':
            # Insidental cuma aktif 1 hari (hari ini)
            tgl_habis = datetime.utcnow().date()

        elif program == 'Reguler' or program == 'Personal Trainer':
            # Data tambahan
            gender = request.form.get('gender')
            alamat = request.form.get('alamat')
            ttl_input = request.form.get('ttl')

            if ttl_input:
                try:
                    ttl_date = datetime.strptime(ttl_input, '%Y-%m-%d').date()
                except Exception:
                    ttl_date = None

            # aktif 1 bulan (30 hari)
            tgl_habis = datetime.utcnow().date() + timedelta(days=30)

            if program == 'Personal Trainer':
                # Data fisik & goals
                tb = request.form.get('tinggi_badan')
                bb = request.form.get('berat_badan')
                goals = request.form.get('goals')
                personal_trainer = request.form.get('personal_trainer')  # <-- ambil dari form

        # 4. Simpan Data Member Baru (buat object untuk semua program)
        try:
            trainer_id_val = int(personal_trainer) if personal_trainer else None
        except Exception:
            trainer_id_val = None

        member_baru = Member(
            nama_lengkap=nama,
            program=program,
            no_wa=no_wa,
            gender=gender,
            alamat=alamat,
            ttl=ttl_date,
            tinggi_badan=tb,
            berat_badan=bb,
            goals=goals,
            trainer_id=trainer_id_val,
            tgl_habis=tgl_habis,
            status='Aktif'
        )

        db.session.add(member_baru)
        try:
            db.session.commit()  # supaya dapat ID
            app.logger.debug(f"Member created: id={member_baru.id} nama={member_baru.nama_lengkap} program={member_baru.program} DB={DB_ABS_PATH}")
        except Exception as e:
            db.session.rollback()
            app.logger.exception("Failed to commit new member during registrasi")
            flash('Gagal menyimpan member. Lihat log server untuk detail.', 'danger')
            return redirect(url_for('registrasi'))

        # 5. Buat Akun Login untuk Member (hanya untuk Personal Trainer)
        user_member_id = None
        if program == 'Personal Trainer' and username_member and password_member:
            hashed_password = generate_password_hash(password_member)
            user_member = User(
                username=username_member,
                password=hashed_password,
                role='member'
            )
            db.session.add(user_member)
            try:
                db.session.commit()
                user_member_id = user_member.id
                app.logger.debug(f"Member user account created: username={username_member} for member_id={member_baru.id}")
                
                # Link user_id ke member
                member_baru.user_id = user_member_id
                db.session.commit()
                flash(f'Member Personal Trainer berhasil didaftarkan dengan akun login!', 'success')
                
            except Exception as e:
                db.session.rollback()
                app.logger.exception("Failed to create member user account")
                flash('Member berhasil dibuat, tapi gagal membuat akun login.', 'warning')
        else:
            flash(f'Member {program} berhasil didaftarkan!', 'success')

        # 6. Otomatis Catat Pembayaran
        bayar_baru = Pembayaran(
            member_id=member_baru.id,
            nominal=nominal,
            keterangan=f"Pendaftaran {program}",
            tanggal_bayar=datetime.utcnow()
        )
        db.session.add(bayar_baru)
        db.session.commit()

        return redirect(url_for('registrasi'))

    # GET -> tampilkan form registrasi
    trainers = User.query.filter_by(role='pt').all()
    return render_template('admin/registrasi.html', trainers=trainers)


@app.route('/admin/members/all')
@role_required('manager', 'admin')
def debug_all_members():

    rows = Member.query.order_by(Member.id.desc()).all()
    lines = ['<h3>All Members (debug)</h3>', '<table border="1" cellpadding="6"><tr><th>ID</th><th>Nama</th><th>Program</th><th>Tgl Habis</th><th>Status</th></tr>']
    for m in rows:
        tgl = m.tgl_habis.strftime('%Y-%m-%d') if m.tgl_habis else ''
        lines.append(f"<tr><td>{m.id}</td><td>{m.nama_lengkap}</td><td>{m.program}</td><td>{tgl}</td><td>{m.status}</td></tr>")
    lines.append('</table>')
    return '\n'.join(lines)

# --- ROUTE DARURAT: PAKSA BUAT AKUN ---
@app.route('/buat_akun_darurat')
def buat_akun_darurat():
    """
    Route untuk membuat akun dummy untuk testing:
    - Manager: username=manager, password=admin123
    - Admin: username=admin, password=admin123
    - PT: username=trainer1, password=trainer123
    """
    messages = []
    
    # 1. MANAGER
    password_manager = generate_password_hash('admin123')
    cek_manager = User.query.filter_by(username='manager').first()
    
    if cek_manager:
        cek_manager.password = password_manager
        db.session.commit()
        messages.append("✅ Akun 'manager' sudah ada. Password di-reset: admin123")
    else:
        manager_baru = User(username='manager', password=password_manager, role='manager')
        db.session.add(manager_baru)
        db.session.commit()
        messages.append("✅ Akun 'manager' berhasil dibuat. Password: admin123")
    
    # 2. ADMIN
    password_admin = generate_password_hash('admin123')
    cek_admin = User.query.filter_by(username='admin').first()
    
    if cek_admin:
        cek_admin.password = password_admin
        db.session.commit()
        messages.append("✅ Akun 'admin' sudah ada. Password di-reset: admin123")
    else:
        admin_baru = User(username='admin', password=password_admin, role='admin')
        db.session.add(admin_baru)
        db.session.commit()
        messages.append("✅ Akun 'admin' berhasil dibuat. Password: admin123")
    
    # 3. PERSONAL TRAINER
    password_pt = generate_password_hash('trainer123')
    cek_pt = User.query.filter_by(username='trainer1').first()
    
    if cek_pt:
        cek_pt.password = password_pt
        db.session.commit()
        messages.append("✅ Akun 'trainer1' sudah ada. Password di-reset: trainer123")
    else:
        pt_baru = User(username='trainer1', password=password_pt, role='pt')
        db.session.add(pt_baru)
        db.session.commit()
        messages.append("✅ Akun 'trainer1' berhasil dibuat. Password: trainer123")
    
    result = "<h2>Akun Dummy Berhasil Dibuat!</h2><br>"
    result += "<h3>Daftar Akun:</h3><ul>"
    result += "<li><strong>Manager:</strong> username=<code>manager</code>, password=<code>admin123</code></li>"
    result += "<li><strong>Admin:</strong> username=<code>admin</code>, password=<code>admin123</code></li>"
    result += "<li><strong>Personal Trainer:</strong> username=<code>trainer1</code>, password=<code>trainer123</code></li>"
    result += "</ul><br><h3>Status:</h3><ul>"
    for msg in messages:
        result += f"<li>{msg}</li>"
    result += "</ul><br>"
    result += f"<a href='{url_for('select_role')}' style='padding:10px 20px; background:#4e73df; color:white; text-decoration:none; border-radius:5px;'>Login Sekarang</a>"
    
    return result

# ==========================================
# ROUTE KHUSUS DASHBOARD PT (TRAINER)
# ==========================================
@app.route('/pt/dashboard')
@role_required('pt')
def pt_dashboard():
    # Require PT login
    if 'user_id' not in session or session.get('role') != 'pt':
        flash('Silakan login sebagai Personal Trainer.', 'warning')
        return redirect(url_for('login'))

    trainer_id = session.get('user_id')
    my_clients = Member.query.filter_by(trainer_id=trainer_id).order_by(Member.nama_lengkap.asc()).all()
    count = len(my_clients)
    return render_template('admin/dashboard_pt.html', my_members=my_clients, my_members_count=count)


@app.route('/admin/queue', methods=['GET', 'POST'])
@role_required('manager')
def queue_analysis():

    # Debug: log who accessed this route and which DB file is active
    try:
        app.logger.debug(f"/admin/queue accessed - method={request.method} username={session.get('username')} role={session.get('role')} user_id={session.get('user_id')} DB={DB_ABS_PATH}")
    except Exception:
        app.logger.debug(f"/admin/queue accessed - unable to read session info. DB={DB_ABS_PATH}")

    equipments = [
        'Treadmill','Static Bike','Elliptical','Rowing Machine','Stair Climber',
        'Bench Press','Chest Press Machine','Lat Pulldown','Smith Machine','Squat Rack',
        'Leg Press','Leg Extension','Leg Curl','Cable Machine','Shoulder Press',
        'Dumbbell Area','Barbell Area'
    ]

    # Ambil presets dari DB jika ada, otherwise gunakan default contoh
    default_presets = {
        'Treadmill': 6.0,
        'Static Bike': 6.0,
        'Elliptical': 6.0,
        'Rowing Machine': 6.0,
        'Stair Climber': 6.0,
        'Bench Press': 12.0,
        'Chest Press Machine': 12.0,
        'Lat Pulldown': 12.0,
        'Smith Machine': 10.0,
        'Squat Rack': 8.0,
        'Leg Press': 8.0,
        'Leg Extension': 12.0,
        'Leg Curl': 12.0,
        'Cable Machine': 10.0,
        'Shoulder Press': 12.0,
        'Dumbbell Area': 20.0,
        'Barbell Area': 15.0
    }

    presets = {}
    try:
        rows = EquipmentPreset.query.all()
        for r in rows:
            presets[r.equipment] = float(r.mu_default)
    except Exception:
        presets = default_presets

    # Pastikan semua equipments ada di presets (fallback ke default)
    for e in equipments:
        if e not in presets:
            presets[e] = default_presets.get(e, '')

    result = None
    form = None

    if request.method == 'POST':
        eq = request.form.get('equipment')
        try:
            lam = float(request.form.get('lambda', '0'))
        except Exception:
            lam = 0.0
        try:
            mu = float(request.form.get('mu', '0'))
        except Exception:
            mu = 0.0
        try:
            m = int(request.form.get('m', '1'))
        except Exception:
            m = 1

        form = type('F', (), {'equipment': eq, 'lambda': lam, 'mu': mu, 'm': m})

        # Validasi
        if lam <= 0 or mu <= 0 or m <= 0:
            flash('Input λ, μ, dan M harus bernilai positif.', 'danger')
            return render_template('admin/queue_analysis.html', equipments=equipments, result=None, form=form)

        # Perhitungan M/M/c dengan penanganan numerik
        import math
        a = lam / mu if mu != 0 else float('inf')  # offered load
        rho = lam / (m * mu) if (m * mu) != 0 else float('inf')  # utilization per server

        Lq = None
        Wq = None
        W = None
        recommendation = None

        if rho >= 1.0:
            # Sistem tidak stabil
            recommendation = 'Sistem tidak stabil (λ ≥ M·μ). Tambah jumlah alat atau kurangi kedatangan.'
        else:
            # sum sampai m-1
            sum_terms = 0.0
            for n in range(0, m):
                sum_terms += (a**n) / math.factorial(n)

            denom = sum_terms + (a**m) / (math.factorial(m) * (1.0 - rho))
            P0 = 1.0 / denom if denom != 0 else 0.0

            # Lq
            numer = P0 * (a**m) * rho
            denom2 = math.factorial(m) * ((1.0 - rho)**2)
            Lq = numer / denom2 if denom2 != 0 else None
            if Lq is not None:
                Wq = Lq / lam if lam != 0 else None
                W = (1.0 / mu) + (Wq if Wq is not None else 0.0)

            recommendation = 'Kapasitas memadai' if rho < 0.8 else 'Risiko kepadatan (ρ ≥ 0.8). Pertimbangkan tambah alat atau batasi durasi.'

        result = type('R', (), {
            'equipment': eq,
            'lambda': lam,
            'mu': mu,
            'm': m,
            'rho': rho,
            'Lq': Lq,
            'Wq': Wq,
            'W': W,
            'recommendation': recommendation
        })

        # Simpan ke database (riwayat)
        try:
            qa = QueueAnalysis(
                equipment=eq,
                lam=lam,
                mu=mu,
                m=m,
                rho=(rho if rho is not None else None),
                Lq=(Lq if Lq is not None else None),
                Wq=(Wq if Wq is not None else None),
                W=(W if W is not None else None),
                recommendation=recommendation
            )
            db.session.add(qa)
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Sertakan riwayat terbaru saat merender
        history = QueueAnalysis.query.order_by(QueueAnalysis.created_at.desc()).limit(50).all()
        # Siapkan data chart (backend memformat tanggal sehingga template tak perlu strftime)
        chart_labels = [r.created_at.strftime('%d-%m %H:%M') for r in history]
        chart_rhos = [r.rho if r.rho is not None else None for r in history]
        chart_Lqs = [r.Lq if r.Lq is not None else None for r in history]

        return render_template('admin/queue_analysis.html', equipments=equipments, presets=presets, result=result, form=form, history=history, chart_labels=chart_labels, chart_rhos=chart_rhos, chart_Lqs=chart_Lqs)

    # GET
    history = QueueAnalysis.query.order_by(QueueAnalysis.created_at.desc()).limit(50).all()
    # Siapkan data chart untuk template
    chart_labels = [r.created_at.strftime('%d-%m %H:%M') for r in history]
    chart_rhos = [r.rho if r.rho is not None else None for r in history]
    chart_Lqs = [r.Lq if r.Lq is not None else None for r in history]
    return render_template('admin/queue_analysis.html', equipments=equipments, presets=presets, result=None, form=None, history=history, chart_labels=chart_labels, chart_rhos=chart_rhos, chart_Lqs=chart_Lqs)


@app.route('/admin/queue/export')
@role_required('manager')
def export_queue_csv():

    import io, csv
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(['created_at','equipment','lambda','mu','m','rho','Lq','Wq','W','recommendation'])

    rows = QueueAnalysis.query.order_by(QueueAnalysis.created_at.desc()).all()
    for r in rows:
        writer.writerow([
            r.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            r.equipment,
            r.lam,
            r.mu,
            r.m,
            r.rho if r.rho is not None else '',
            r.Lq if r.Lq is not None else '',
            r.Wq if r.Wq is not None else '',
            r.W if r.W is not None else '',
            r.recommendation or ''
        ])

    output = out.getvalue()
    return (output, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename="queue_analysis_history.csv"'
    })


@app.route('/admin/queue/clear', methods=['POST'])
@role_required('manager')
def clear_queue_history():

    try:
        # Hapus semua entri QueueAnalysis
        deleted = QueueAnalysis.query.delete()
        db.session.commit()
        flash(f'Riwayat analisis dihapus ({deleted} baris).', 'success')
    except Exception:
        db.session.rollback()
        flash('Gagal menghapus riwayat analisis.', 'danger')

    return redirect(url_for('queue_analysis'))


@app.route('/admin/queue/delete/<int:id>', methods=['POST'])
@role_required('manager')
def delete_queue_entry(id):

    try:
        qa = QueueAnalysis.query.get(id)
        if not qa:
            flash('Entri tidak ditemukan.', 'warning')
            return redirect(url_for('queue_analysis'))
        db.session.delete(qa)
        db.session.commit()
        flash('Satu entri riwayat dihapus.', 'success')
    except Exception:
        db.session.rollback()
        flash('Gagal menghapus entri riwayat.', 'danger')

    return redirect(url_for('queue_analysis'))


@app.route('/admin/queue/presets', methods=['GET', 'POST'])
@role_required('manager')
def queue_presets():

    equipments = [
        'Treadmill','Static Bike','Elliptical','Rowing Machine','Stair Climber',
        'Bench Press','Chest Press Machine','Lat Pulldown','Smith Machine','Squat Rack',
        'Leg Press','Leg Extension','Leg Curl','Cable Machine','Shoulder Press',
        'Dumbbell Area','Barbell Area'
    ]

    if request.method == 'POST':
        equipment = request.form.get('equipment')
        try:
            mu = float(request.form.get('mu', '0'))
        except Exception:
            mu = 0.0

        if not equipment or mu <= 0:
            flash('Alat dan μ harus valid.', 'danger')
            return redirect(url_for('queue_presets'))

        preset = EquipmentPreset.query.filter_by(equipment=equipment).first()
        if preset:
            preset.mu_default = mu
        else:
            preset = EquipmentPreset(equipment=equipment, mu_default=mu)
            db.session.add(preset)
        db.session.commit()
        flash(f'Preset untuk {equipment} disimpan (μ={mu}).', 'success')
        return redirect(url_for('queue_presets'))

    # GET
    presets = {p.equipment: p.mu_default for p in EquipmentPreset.query.all()}
    return render_template('admin/queue_presets.html', equipments=equipments, presets=presets)


# ==========================================
# ROUTE KHUSUS PORTAL MEMBER (PELANGGAN)
# ==========================================
# Akses lewat browser: /member/dashboard/1 (angka 1 adalah ID member)
@app.route('/member/dashboard/<int:id>')
def member_dashboard(id):
    # Validasi: jika logged in sebagai member, hanya bisa akses dashboard sendiri
    if 'role' in session and session['role'] == 'member':
        if 'member_id' in session and session['member_id'] != id:
            flash('Anda tidak memiliki akses ke dashboard member lain!', 'danger')
            return redirect(url_for('member_dashboard', id=session['member_id']))
    
    # Ambil data member
    member = Member.query.get_or_404(id)
    
    # Ambil riwayat latihan
    logs = Latihan.query.filter_by(member_id=id).order_by(Latihan.tanggal.asc()).all()
    
    today = datetime.utcnow().date()
    
    # Arahkan ke folder templates/member/dashboard.html
    return render_template('member/dashboard.html', member=member, logs=logs, today=today)

# -----------------------------------------------------------
# PASTIKAN KODE INI TETAP PALING BAWAH
# -----------------------------------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # ... (kode buat akun admin default) ...
    app.run(debug=True)

