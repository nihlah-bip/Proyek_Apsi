# Pembagian Akses Berdasarkan Role

## 📋 Role & Akses Lengkap

### 1. **Admin** 
**Fokus:** Operasional harian gym

#### ✅ Akses Yang Diberikan:
- **Dashboard Admin** (`/admin`)
  - Grafik pemasukan bulanan
  - Grafik pendaftaran member per program
  
- **Manajemen Member** 
  - Transaksi & Pendaftaran Baru (`/admin/registrasi`)
  - Data Member (`/admin/members`)
  - Detail Member (`/admin/member/<id>`)
  - Hapus Member
  - Pembayaran & Perpanjangan (`/admin/payments`)

- **Training Management**
  - Input Latihan & Progres (`/admin/training`)
  - Hapus Catatan Latihan
  - Lihat semua member program Personal Trainer

- **Quick Access Sidebar**
  - List members (Personal Trainer program)
  - Detail member

#### ❌ TIDAK Bisa Akses:
- ❌ Kelola Staff (`/admin/staff`) - Hanya Manager
- ❌ Kelola Trainer (`/admin/trainers`) - Hanya Manager
- ❌ Analisis Antrian (`/admin/queue`) - Hanya Manager
- ❌ Dashboard Owner (`/owner`) - Hanya Manager

---

### 2. **Personal Trainer (PT)**
**Fokus:** Member binaan sendiri

#### ✅ Akses Yang Diberikan:
- **Dashboard PT** (`/pt/dashboard`)
  - Daftar member binaan
  - Jumlah member binaan

- **Training Management**
  - Input Latihan & Progres **HANYA untuk member binaan** (`/admin/training`)
  - Hapus catatan latihan **HANYA member binaan sendiri**
  - Detail member **HANYA member binaan sendiri** (`/admin/member/<id>`)

- **Quick Access Sidebar**
  - List member binaan saja

#### ❌ TIDAK Bisa Akses:
- ❌ Dashboard Admin/Owner
- ❌ Transaksi & Registrasi member baru
- ❌ Data semua member (hanya member binaan)
- ❌ Pembayaran
- ❌ Kelola Staff
- ❌ Kelola Trainer
- ❌ Analisis Antrian

---

### 3. **Manager / Pemilik**
**Fokus:** Analisis bisnis & kontrol penuh

#### ✅ Akses Yang Diberikan:
**SEMUA akses Admin PLUS:**

- **Dashboard Pemilik** (`/owner`)
  - Analisis bisnis lengkap
  - Grafik pemasukan & pendaftaran
  - Pie chart program member
  - Total member aktif
  - Total personal trainer

- **Manajemen Staff & Trainer**
  - Kelola Staff (`/admin/staff`)
    - Tambah admin baru
    - Hapus admin
  - Kelola Trainer (`/admin/trainers`)
    - Tambah personal trainer
    - Hapus personal trainer
    - Lihat member binaan per trainer

- **Analisis Antrian** (`/admin/queue`)
  - Hitung antrian M/M/c
  - Riwayat analisis
  - Export CSV
  - Preset equipment μ

- **Quick Access Sidebar**
  - List semua trainers + link ke member binaan
  - List semua members

#### ✅ Full Access:
Semua fitur dalam sistem

---

## 🔐 Tabel Akses Route

| Route | Admin | PT | Manager |
|-------|-------|----|---------| 
| `/admin` (Dashboard Admin) | ✅ | ❌ | ✅ |
| `/owner` (Dashboard Owner) | ❌ | ❌ | ✅ |
| `/pt/dashboard` | ❌ | ✅ | ❌ |
| `/admin/registrasi` (Transaksi Baru) | ✅ | ❌ | ✅ |
| `/admin/members` (Data Member) | ✅ | ❌ | ✅ |
| `/admin/member/<id>` (Detail) | ✅ | ✅* | ✅ |
| `/admin/members/delete/<id>` | ✅ | ❌ | ✅ |
| `/admin/payments` (Pembayaran) | ✅ | ❌ | ✅ |
| `/admin/training` (Input Latihan) | ✅ | ✅* | ✅ |
| `/admin/training/delete/<id>` | ✅ | ✅* | ✅ |
| `/admin/staff` (Kelola Staff) | ❌ | ❌ | ✅ |
| `/admin/staff/delete/<id>` | ❌ | ❌ | ✅ |
| `/admin/trainers` (Kelola Trainer) | ❌ | ❌ | ✅ |
| `/admin/trainers/delete/<id>` | ❌ | ❌ | ✅ |
| `/admin/trainer/<id>` (Member per Trainer) | ✅ | ✅ | ✅ |
| `/admin/queue` (Analisis Antrian) | ❌ | ❌ | ✅ |
| `/admin/queue/export` | ❌ | ❌ | ✅ |
| `/admin/queue/clear` | ❌ | ❌ | ✅ |
| `/admin/queue/delete/<id>` | ❌ | ❌ | ✅ |
| `/admin/queue/presets` | ❌ | ❌ | ✅ |

**Catatan:** 
- ✅* = Akses terbatas (PT hanya untuk member binaan sendiri)

---

## 🎯 Implementasi Proteksi

### Decorator yang Digunakan:

```python
# 1. Login Required (semua user harus login)
@login_required
def some_route():
    ...

# 2. Role Required (harus punya role tertentu)
@role_required('admin', 'manager')  # admin ATAU manager
def some_route():
    ...

@role_required('manager')  # hanya manager
def some_route():
    ...
```

### Contoh Implementasi:

```python
# Admin & Manager bisa akses
@app.route('/admin/registrasi')
@role_required('admin', 'manager')
def registrasi():
    ...

# Hanya Manager
@app.route('/admin/staff')
@role_required('manager')
def manage_staff():
    ...

# PT, Admin, Manager (dengan validasi tambahan di dalam)
@app.route('/admin/training')
@role_required('pt', 'admin', 'manager')
def training():
    if session.get('role') == 'pt':
        # PT hanya bisa input untuk member binaan
        members = Member.query.filter_by(trainer_id=session['user_id'])
    ...
```

---

## 🚀 Testing Skenario

### Test Admin:
1. Login sebagai admin
2. ✅ Bisa akses Dashboard Admin
3. ✅ Bisa registrasi member baru
4. ✅ Bisa lihat & kelola semua member
5. ✅ Bisa input pembayaran
6. ✅ Bisa input latihan semua member PT
7. ❌ Tidak bisa akses Kelola Staff
8. ❌ Tidak bisa akses Analisis Antrian
9. ❌ Tidak bisa akses Dashboard Owner

### Test PT:
1. Login sebagai PT
2. ✅ Bisa akses Dashboard PT
3. ✅ Bisa lihat member binaan saja
4. ✅ Bisa input latihan member binaan
5. ❌ Tidak bisa registrasi member
6. ❌ Tidak bisa lihat member lain
7. ❌ Tidak bisa hapus member
8. ❌ Tidak bisa akses apapun di luar scope member binaan

### Test Manager:
1. Login sebagai manager
2. ✅ Bisa akses Dashboard Owner (halaman utama)
3. ✅ Bisa akses SEMUA fitur admin
4. ✅ Bisa kelola staff
5. ✅ Bisa kelola trainer
6. ✅ Bisa analisis antrian
7. ✅ Bisa lihat semua data

---

## 🎨 Sidebar Menu per Role

### Admin Sidebar:
```
📊 Dashboard
└─ Manajemen
   ├─ Transaksi Baru
   ├─ Data Member
   └─ Pembayaran

🏋️ Personal Trainer
├─ Input Latihan & Progres
└─ Members (Quick Access - PT program only)
```

### PT Sidebar:
```
📊 Dashboard

🏋️ Personal Trainer
├─ Input Latihan & Progres
└─ Member Binaan Saya (filtered by trainer_id)
```

### Manager Sidebar:
```
📊 Dashboard

💼 Manajemen Bisnis
├─ Transaksi Baru
├─ Data Member
├─ Pembayaran
├─ Kelola Staff
└─ Kelola Trainer

📈 Analisis Antrian

🏋️ Personal Trainer
├─ Input Latihan & Progres
├─ Personal Trainer (Quick Access with member list)
└─ Members (Quick Access - all PT members)
```

---

**Last Updated:** 28 November 2025
