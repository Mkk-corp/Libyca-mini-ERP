import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';

export default function Login() {
  const navigate   = useNavigate();
  const { login, isAuthenticated, loading, error, clearError } = useAuthStore();
  const [email, setEmail]     = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);

  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true });
  }, [isAuthenticated]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearError();
    const ok = await login(email.trim().toLowerCase(), password);
    if (ok) navigate('/', { replace: true });
  };

  return (
    <div style={{
      minHeight: '100dvh', display: 'flex', flexDirection: 'column',
      background: 'linear-gradient(160deg, #0C3D38 0%, #1A6B5C 60%, #0a2e2b 100%)',
    }}>
      {/* Top branding */}
      <div style={{
        flex: 1, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: '40px 24px 24px',
      }}>
        <div style={{
          width: 80, height: 80, borderRadius: 22,
          background: 'rgba(200,220,40,.2)', border: '2px solid rgba(200,220,40,.4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '2.4rem', marginBottom: 18,
        }}>
          ♻
        </div>
        <h1 style={{ color: '#fff', fontSize: '2rem', fontWeight: 700, marginBottom: 6 }}>ليبيكا</h1>
        <p style={{ color: 'rgba(255,255,255,.6)', fontSize: '.9rem', textAlign: 'center' }}>
          نظام إدارة متكامل للتدوير
        </p>
      </div>

      {/* Form card */}
      <div style={{
        background: '#fff', borderRadius: '24px 24px 0 0',
        padding: '28px 24px calc(28px + env(safe-area-inset-bottom))',
        boxShadow: '0 -4px 30px rgba(0,0,0,.15)',
      }}>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: 6, color: '#0C3D38' }}>
          تسجيل الدخول
        </h2>
        <p style={{ fontSize: '.83rem', color: '#64748b', marginBottom: 22 }}>
          أدخل بياناتك للوصول إلى النظام
        </p>

        {error && (
          <div style={{
            background: '#fee2e2', border: '1px solid #fecaca', borderRadius: 10,
            padding: '10px 14px', marginBottom: 16,
            fontSize: '.85rem', color: '#dc2626', display: 'flex', gap: 8, alignItems: 'center',
          }}>
            <span>✕</span> {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="field-group">
            <label className="field-label">البريد الإلكتروني</label>
            <input
              type="email"
              className="field-input"
              placeholder="example@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              inputMode="email"
            />
          </div>

          <div className="field-group" style={{ position: 'relative' }}>
            <label className="field-label">كلمة المرور</label>
            <input
              type={showPass ? 'text' : 'password'}
              className="field-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              style={{ paddingLeft: 44 }}
            />
            <button
              type="button"
              onClick={() => setShowPass((v) => !v)}
              style={{
                position: 'absolute', left: 12, bottom: 10,
                background: 'none', border: 'none', cursor: 'pointer',
                color: '#94a3b8', fontSize: '1rem',
              }}
            >
              {showPass ? '🙈' : '👁'}
            </button>
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-full"
            disabled={loading}
            style={{ marginTop: 8, height: 48, fontSize: '1rem' }}
          >
            {loading ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
                جاري التسجيل...
              </span>
            ) : 'تسجيل الدخول'}
          </button>
        </form>
      </div>
    </div>
  );
}
