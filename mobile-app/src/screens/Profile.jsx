import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import TopBar from '../components/TopBar';
import BottomNav from '../components/BottomNav';
import { showToast } from '../components/Toast';
import useAuthStore from '../store/authStore';
import api from '../api/client';

const ROLE_LABEL = { superadmin: 'مشرف عام', admin: 'مشرف', user: 'مستخدم' };
const ROLE_COLOR = { superadmin: '#9d174d', admin: '#d97706', user: '#2563eb' };

export default function Profile() {
  const navigate  = useNavigate();
  const { user, logout } = useAuthStore();
  const [tab, setTab]   = useState('info'); // 'info' | 'password'
  const [name, setName]   = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [curPass, setCurPass]   = useState('');
  const [newPass, setNewPass]   = useState('');
  const [confPass, setConfPass] = useState('');
  const [saving, setSaving] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  const saveProfile = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      // Uses the web API endpoint directly
      const fd = new FormData();
      fd.append('name', name);
      fd.append('email', email);
      await api.post('/profile/update', fd, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      showToast('تم تحديث البيانات');
    } catch {
      showToast('فشل التحديث', 'error');
    } finally { setSaving(false); }
  };

  const savePassword = async (e) => {
    e.preventDefault();
    if (newPass !== confPass) { showToast('كلمتا المرور غير متطابقتين', 'error'); return; }
    if (newPass.length < 6)   { showToast('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'error'); return; }
    setSaving(true);
    try {
      const fd = new URLSearchParams();
      fd.append('current_password', curPass);
      fd.append('new_password', newPass);
      fd.append('confirm_password', confPass);
      await api.post('/profile/password', fd, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      showToast('تم تغيير كلمة المرور');
      setCurPass(''); setNewPass(''); setConfPass('');
    } catch {
      showToast('فشل تغيير كلمة المرور', 'error');
    } finally { setSaving(false); }
  };

  return (
    <div className="screen">
      <TopBar title="حسابي" />

      <div className="screen-content">
        {/* Avatar */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: 24 }}>
          <div className="avatar" style={{ width: 72, height: 72, fontSize: '1.8rem', marginBottom: 12 }}>
            {user?.name?.[0]?.toUpperCase() || '؟'}
          </div>
          <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--primary)', marginBottom: 4 }}>
            {user?.name}
          </h2>
          <span style={{
            padding: '3px 12px', borderRadius: 20, fontSize: '.75rem', fontWeight: 600,
            background: `${ROLE_COLOR[user?.role] || '#64748b'}22`,
            color: ROLE_COLOR[user?.role] || '#64748b',
          }}>
            {ROLE_LABEL[user?.role] || 'مستخدم'}
          </span>
          <p style={{ fontSize: '.82rem', color: 'var(--text-muted)', marginTop: 6 }}>{user?.email}</p>
        </div>

        {/* Tabs */}
        <div style={{
          display: 'flex', background: '#f1f5f9', borderRadius: 10, padding: 4, marginBottom: 18,
        }}>
          {[['info', 'البيانات الشخصية'], ['password', 'كلمة المرور']].map(([key, label]) => (
            <button key={key} onClick={() => setTab(key)} style={{
              flex: 1, padding: '9px 0', border: 'none', borderRadius: 8, fontFamily: 'inherit',
              fontSize: '.88rem', fontWeight: 600, cursor: 'pointer', transition: 'all .2s',
              background: tab === key ? '#fff' : 'transparent',
              color: tab === key ? 'var(--primary)' : '#94a3b8',
              boxShadow: tab === key ? '0 2px 8px rgba(0,0,0,.08)' : 'none',
            }}>{label}</button>
          ))}
        </div>

        {/* Profile form */}
        {tab === 'info' && (
          <div className="card">
            <form onSubmit={saveProfile}>
              <div className="field-group">
                <label className="field-label">الاسم الكامل</label>
                <input type="text" className="field-input" value={name}
                  onChange={(e) => setName(e.target.value)} required />
              </div>
              <div className="field-group">
                <label className="field-label">البريد الإلكتروني</label>
                <input type="email" className="field-input" value={email}
                  onChange={(e) => setEmail(e.target.value)} required />
              </div>
              <button type="submit" className="btn btn-primary btn-full" disabled={saving}
                style={{ height: 46, fontSize: '.95rem' }}>
                {saving ? 'جاري الحفظ...' : 'حفظ التغييرات'}
              </button>
            </form>
          </div>
        )}

        {/* Password form */}
        {tab === 'password' && (
          <div className="card">
            <form onSubmit={savePassword}>
              <div className="field-group">
                <label className="field-label">كلمة المرور الحالية</label>
                <input type="password" className="field-input" value={curPass}
                  onChange={(e) => setCurPass(e.target.value)} required />
              </div>
              <div className="field-group">
                <label className="field-label">كلمة المرور الجديدة</label>
                <input type="password" className="field-input" value={newPass} minLength={6}
                  onChange={(e) => setNewPass(e.target.value)} required />
              </div>
              <div className="field-group">
                <label className="field-label">تأكيد كلمة المرور</label>
                <input type="password" className="field-input" value={confPass}
                  onChange={(e) => setConfPass(e.target.value)} required />
              </div>
              <button type="submit" className="btn btn-primary btn-full" disabled={saving}
                style={{ height: 46, fontSize: '.95rem' }}>
                {saving ? 'جاري الحفظ...' : 'تغيير كلمة المرور'}
              </button>
            </form>
          </div>
        )}

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="btn btn-full"
          style={{
            marginTop: 8, height: 46,
            background: '#fee2e2', color: '#dc2626',
            fontSize: '.95rem', fontWeight: 600,
          }}
        >
          تسجيل الخروج
        </button>
      </div>

      <BottomNav />
    </div>
  );
}
