from flask import Flask, render_template, request, redirect, url_for, session, flash
import logging
import os
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func

app = Flask(__name__)

# ==========================================
# WAJIB DITAMBAHKAN AGAR LOGIN BISA JALAN
# ==========================================
app.secret_key = 'kunci_rahasia_lembah_fitness_123' 

# Konfigurasi Database (yang sudah ada)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lembah_fitness.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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

    # Status Membership
    status = db.Column(db.String(20), default='Aktif')
    tgl_daftar = db.Column(db.Date, default=datetime.utcnow)
    tgl_habis = db.Column(db.Date, nullable=False)

    # Relasi
    pembayaran = db.relationship('Pembayaran', backref='member', lazy=True)
    latihan = db.relationship('Latihan', backref='member', lazy=True)
    # Relationship to User (personal trainer)
    trainer = db.relationship('User', foreign_keys=[trainer_id], backref='clients', lazy=True)

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



# ==========================================
# 3. ROUTE (JALUR HALAMAN)
# ==========================================

# --- BAGIAN PUBLIC (MEMBER/PENGUNJUNG) ---
@app.route('/')
def index():
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

# --- ROUTE LOGIN (PINTU MASUK) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Cek database
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session.clear() # Bersihkan sesi lama
            # Simpan data login baru
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Username atau Password Salah!', 'danger')
            
    return render_template('admin/login.html')

# --- ROUTE LOGOUT ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- BAGIAN ADMIN (DASHBOARD & SISTEM) ---
@app.route('/admin')
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


# --- HALAMAN MANAJEMEN MEMBER ---
@app.route('/admin/members')
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


# HAPUS MEMBER
@app.route('/admin/members/delete/<int:member_id>', methods=['POST'])
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
def payments():
    if request.method == 'POST':
        member_id = request.form['member_id']
        nominal = int(request.form['nominal'])
        bulan_tambah = int(request.form['bulan_tambah'])  # 1, 3, 6, atau 12
        keterangan = request.form['keterangan']

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

        if member.tgl_habis < today:
            base_date = today
        else:
            base_date = member.tgl_habis

        new_expired_date = base_date + timedelta(days=30 * bulan_tambah)

        member.tgl_habis = new_expired_date
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


@app.route('/admin/training', methods=['GET', 'POST'])
def training():
    # Halaman input latihan & progres (oleh trainer)
    # Access: PT, Manager, Admin
    if 'user_id' not in session or session.get('role') not in ('pt', 'manager', 'admin'):
        flash('Silakan login sebagai Personal Trainer/Manager/Admin untuk mengakses halaman ini.', 'warning')
        return redirect(url_for('login'))
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


# --- FITUR MANAGER: KELOLA STAFF (READ & CREATE) ---
@app.route('/admin/staff', methods=['GET', 'POST'])
def manage_staff():
    # Cek Login & Cek Role (Hanya Manager yang boleh akses)
    if 'user_id' not in session: return redirect(url_for('login'))
    if session.get('role') != 'manager': return "Akses Ditolak! Hanya Manager.", 403

    # LOGIKA TAMBAH STAFF BARU (CREATE)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']




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
    all_users = User.query.order_by(User.role.asc()).all()
    return render_template('admin/manage_staff.html', users=all_users)


@app.route('/admin/trainers', methods=['GET', 'POST'])
def manage_trainers():
    # Admin/Manager only
    if 'user_id' not in session or session.get('role') not in ('manager', 'admin'):
        flash('Akses ditolak.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form.get('username')
        # Do not require password on creation — admin will set or instruct PT to create password later
        if not username:
            flash('Username wajib diisi.', 'danger')
            return redirect(url_for('manage_trainers'))

        existing = User.query.filter_by(username=username).first()
        if existing:
            flash('Username sudah ada.', 'warning')
            return redirect(url_for('manage_trainers'))

        # store a hashed empty password as placeholder
        hashed = generate_password_hash('')
        new_pt = User(username=username, password=hashed, role='pt')
        db.session.add(new_pt)
        db.session.commit()
        flash(f'Personal Trainer {username} dibuat tanpa password. Silakan atur password nanti.', 'success')
        return redirect(url_for('manage_trainers'))

    # GET -> list trainers
    trainers = User.query.filter_by(role='pt').all()
    # attach clients count
    trainer_rows = []
    for t in trainers:
        clients_count = Member.query.filter_by(trainer_id=t.id).count()
        trainer_rows.append(type('T', (), {'id': t.id, 'username': t.username, 'clients_count': clients_count}))

    return render_template('admin/personal_trainers.html', trainers=trainer_rows)


@app.route('/admin/trainers/delete/<int:id>', methods=['POST'])
def delete_trainer(id):
    if 'user_id' not in session or session.get('role') not in ('manager', 'admin'):
        flash('Akses ditolak.', 'warning')
        return redirect(url_for('login'))

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
def delete_staff(id):
    if 'user_id' not in session or session.get('role') != 'manager':
        return redirect(url_for('login'))
    
    user_to_delete = User.query.get_or_404(id)
    
    # Mencegah manager menghapus dirinya sendiri
    if user_to_delete.username == session['username'] or user_to_delete.username == 'manager':
        flash('Tidak bisa menghapus akun utama!', 'warning')
    else:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash('Akun berhasil dihapus.', 'success')
        
    return redirect(url_for('manage_staff'))


@app.route('/admin/member/<int:member_id>')
def admin_member_detail(member_id):
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu.', 'warning')
        return redirect(url_for('login'))

    member = Member.query.get_or_404(member_id)

    # Allow access if manager/admin, or if PT who owns this member
    role = session.get('role')
    if role == 'pt':
        if member.trainer_id != session.get('user_id'):
            flash('Akses ditolak. Hanya trainer yang membina member ini.', 'warning')
            return redirect(url_for('login'))
    elif role not in ('manager', 'admin'):
        flash('Akses ditolak.', 'warning')
        return redirect(url_for('login'))
    logs = Latihan.query.filter_by(member_id=member.id).order_by(Latihan.tanggal.desc()).limit(50).all()

    return render_template('admin/member_detail.html', member=member, logs=logs)


@app.route('/admin/trainer/<int:trainer_id>')
def admin_trainer_members(trainer_id):
    if 'user_id' not in session or session.get('role') not in ('manager', 'admin'):
        flash('Akses ditolak.', 'warning')
        return redirect(url_for('login'))

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
def registrasi():
    if request.method == 'POST':
        app.logger.debug(f"Registrasi POST received. form keys: {list(request.form.keys())}")
        # 1. Ambil Data Dasar
        program = request.form['program']
        nama = request.form['nama']
        no_wa = request.form['no_wa']
        nominal = int(request.form['nominal'])  # Harga otomatis dari form

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

        # 5. Otomatis Catat Pembayaran
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
def debug_all_members():
    # Admin-only debug route to list all members (temporary)
    if 'user_id' not in session or session.get('role') not in ('manager', 'admin'):
        flash('Akses ditolak.', 'warning')
        return redirect(url_for('login'))

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
    # 1. Hash Password
    password_aman = generate_password_hash('admin123')
    
    # 2. Cek apakah user manager sudah ada?
    cek_user = User.query.filter_by(username='manager').first()
    
    if cek_user:
        # Kalau ada, kita update passwordnya saja biar yakin
        cek_user.password = password_aman
        db.session.commit()
        return "Akun 'manager' SUDAH ADA. Password telah di-reset jadi: admin123. Silakan Login."
    else:
        # Kalau belum ada, kita buat baru
        manager_baru = User(username='manager', password=password_aman, role='manager')
        db.session.add(manager_baru)
        db.session.commit()
        return "BERHASIL! Akun 'manager' baru saja dibuat. Password: admin123. Silakan Login."

# ==========================================
# ROUTE KHUSUS DASHBOARD PT (TRAINER)
# ==========================================
@app.route('/pt/dashboard')
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
def queue_analysis():
    # Cek login & role (hanya manager/admin boleh akses)
    if 'user_id' not in session or session.get('role') not in ('manager', 'admin'):
        flash('Akses ditolak. Silakan login sebagai Manager/Admin.', 'warning')
        return redirect(url_for('login'))

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
def export_queue_csv():
    if 'user_id' not in session or session.get('role') not in ('manager', 'admin'):
        flash('Akses ditolak.', 'warning')
        return redirect(url_for('login'))

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
def clear_queue_history():
    if 'user_id' not in session or session.get('role') not in ('manager', 'admin'):
        flash('Akses ditolak.', 'warning')
        return redirect(url_for('login'))

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
def delete_queue_entry(id):
    if 'user_id' not in session or session.get('role') not in ('manager', 'admin'):
        flash('Akses ditolak.', 'warning')
        return redirect(url_for('login'))

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
def queue_presets():
    if 'user_id' not in session or session.get('role') not in ('manager', 'admin'):
        flash('Akses ditolak.', 'warning')
        return redirect(url_for('login'))

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

