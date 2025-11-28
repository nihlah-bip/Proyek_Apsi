# Sistem Role-Based Access Control (RBAC)
## Lembah Fitness Management System

---

## 🎯 Overview

Sistem ini sekarang menggunakan **Role-Based Access Control** untuk memisahkan akses berdasarkan peran pengguna:
- **Admin** - Mengelola operasional harian, member, dan transaksi
- **Personal Trainer (PT)** - Mengelola member binaan dan input latihan
- **Manager/Pemilik** - Akses penuh untuk analisis bisnis dan kelola staff
- **Member** - Melihat dashboard pribadi dan progres latihan

---

## 🚪 Portal Login

### Portal Staff (Admin/PT/Manager)
**URL:** `/admin/select-role`

Portal ini menampilkan 3 pilihan role:
1. **Administrator** - Untuk staff admin
2. **Personal Trainer** - Untuk trainer
3. **Pemilik/Manager** - Untuk manager

Setelah memilih role, user akan diarahkan ke halaman login dengan validasi role.

### Login Member
Member tetap login dari **website public** (halaman utama).

---

## 🔐 Flow Login

```
1. User mengakses /admin/select-role
   ↓
2. User memilih role (Admin/PT/Manager)
   ↓
3. Redirect ke /login?role=<role_selected>
   ↓
4. User input username & password
   ↓
5. System validasi:
   - Cek username & password
   - Validasi role sesuai pilihan
   ↓
6. Redirect ke dashboard sesuai role:
   - PT → /pt/dashboard
   - Manager → /owner
   - Admin → /admin
```

---

## 📊 Dashboard per Role

### 1. Admin Dashboard (`/admin`)
**Akses:** Admin, Manager
**Fitur:**
- Grafik pemasukan bulanan
- Grafik pendaftaran member
- Data member
- Input transaksi baru
- Input pembayaran

### 2. PT Dashboard (`/pt/dashboard`)
**Akses:** Personal Trainer only
**Fitur:**
- Daftar member binaan
- Input latihan & progres
- Detail member binaan

### 3. Owner Dashboard (`/owner`)
**Akses:** Manager only
**Fitur:**
- Analisis bisnis lengkap
- Grafik pemasukan & pendaftaran
- Pie chart program member
- Kelola staff & trainer
- Analisis antrian equipment
- Akses ke semua fitur admin

---

## 🎨 Sidebar Dinamis

Sidebar berubah otomatis berdasarkan role user yang login:

### Admin
- Dashboard
- Manajemen (Transaksi, Data Member, Pembayaran)
- Input Latihan & Progres
- Quick Access Members

### Personal Trainer
- Dashboard
- Input Latihan & Progres
- Member Binaan Saya (hanya member yang dia bina)

### Manager
- Dashboard
- Manajemen Bisnis (semua fitur admin)
- Kelola Staff
- Kelola Trainer
- Analisis Antrian
- Quick Access Trainers & Members

---

## 🛡️ Proteksi Route

Menggunakan decorator untuk melindungi route:

### `@login_required`
Memastikan user sudah login.

```python
@app.route('/admin')
@login_required
def admin_dashboard():
    ...
```

### `@role_required('role1', 'role2', ...)`
Memastikan user memiliki role tertentu.

```python
@app.route('/owner')
@role_required('manager')
def owner_dashboard():
    ...
```

---

## 🔄 Logout

Saat logout, user akan diarahkan kembali ke **portal pemilihan role** (`/admin/select-role`) untuk login ulang.

---

## 📝 Testing

### Test Account (Default)
```
Manager:
- Username: manager
- Password: admin123

Admin:
- Buat melalui halaman kelola staff (oleh manager)

PT:
- Buat melalui halaman kelola trainer (oleh manager/admin)
```

### Test Flow
1. Akses `http://localhost:5000/admin/select-role`
2. Pilih role "Pemilik/Manager"
3. Login dengan manager/admin123
4. Explore dashboard owner
5. Logout dan coba login sebagai PT atau Admin

---

## 🎨 UI/UX Improvements

### Portal Selection Page
- Card interaktif dengan hover effect
- Icon per role (shield, dumbbell, crown)
- Responsive design
- Link ke member login

### Login Page
- Menampilkan role yang dipilih
- Alert untuk role mismatch
- Link kembali ke portal selection

### Sidebar
- Badge role di user dropdown
- Menu dinamis per role
- Quick access member/trainer

### Navbar
- Menampilkan username & role badge
- Dropdown profile dengan logout

---

## 📋 TODO / Enhancement Ideas

- [ ] Reset password functionality
- [ ] User profile page
- [ ] Activity log per user
- [ ] Permission granular (di luar role)
- [ ] Dashboard member dengan login credentials
- [ ] 2FA untuk manager
- [ ] Email notification untuk member

---

## 🐛 Troubleshooting

### "Akses Ditolak" saat login
- Pastikan username & role sesuai
- Cek akun di database (tabel User)

### Sidebar tidak muncul menu
- Cek session.role di browser console
- Clear cookies & login ulang

### Member tidak muncul di PT dashboard
- Cek trainer_id di tabel Member
- Pastikan member memilih PT saat registrasi

---

## 📞 Contact

Untuk pertanyaan atau bug report, hubungi tim developer.

**Last Updated:** 28 November 2025
