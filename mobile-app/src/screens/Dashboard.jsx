import { useState, useEffect } from 'react';
import TopBar from '../components/TopBar';
import BottomNav from '../components/BottomNav';
import OfflineBanner from '../components/OfflineBanner';
import { dashboard, sales, purchases } from '../api/client';
import useAuthStore from '../store/authStore';

const fmt = (n) =>
  new Intl.NumberFormat('ar-LY', { minimumFractionDigits: 0 }).format(n ?? 0);

export default function Dashboard() {
  const user = useAuthStore((s) => s.user);
  const [report, setReport]       = useState(null);
  const [recentSales, setRecentSales]       = useState([]);
  const [recentPurchases, setRecentPurchases] = useState([]);
  const [loading, setLoading]     = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [rep, s, p] = await Promise.all([
        dashboard.monthly(),
        sales.list({ per_page: 5 }),
        purchases.list({ per_page: 5 }),
      ]);
      setReport(rep);
      setRecentSales(s.data || []);
      setRecentPurchases(p.data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const cur = report?.current || {};

  return (
    <div className="screen">
      <TopBar
        title="لوحة التحكم"
        left={
          <button className="topbar-btn" onClick={load} title="تحديث">
            ↻
          </button>
        }
      />
      <OfflineBanner />

      <div className="screen-content">
        {/* Greeting */}
        <div style={{ marginBottom: 18 }}>
          <p style={{ fontSize: '.82rem', color: 'var(--text-muted)' }}>مرحباً،</p>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--primary)' }}>
            {user?.name || 'مستخدم'}
          </h2>
        </div>

        {loading ? (
          <div className="spinner-wrap"><div className="spinner" /></div>
        ) : (
          <>
            {/* KPI grid */}
            <div className="stat-grid">
              <div className="stat-card">
                <div className="stat-icon" style={{ background: '#dcfce7' }}>💰</div>
                <div className="stat-label">مبيعات الشهر</div>
                <div className="stat-value positive">{fmt(cur.sales)} د.ل</div>
              </div>
              <div className="stat-card">
                <div className="stat-icon" style={{ background: '#fee2e2' }}>🛒</div>
                <div className="stat-label">مشتريات الشهر</div>
                <div className="stat-value negative">{fmt(cur.purchases)} د.ل</div>
              </div>
              <div className="stat-card">
                <div className="stat-icon" style={{ background: '#fef3c7' }}>📊</div>
                <div className="stat-label">المصروفات</div>
                <div className="stat-value" style={{ color: 'var(--warning)' }}>{fmt(cur.expenses)} د.ل</div>
              </div>
              <div className="stat-card">
                <div className="stat-icon" style={{ background: 'var(--lime-lt)' }}>📈</div>
                <div className="stat-label">صافي الربح</div>
                <div className={`stat-value ${cur.net_profit >= 0 ? 'positive' : 'negative'}`}>
                  {fmt(cur.net_profit)} د.ل
                </div>
              </div>
            </div>

            {/* Recent Sales */}
            <div className="card">
              <div className="section-header">
                <span className="section-title">آخر المبيعات</span>
                <a href="/sales" style={{ fontSize: '.78rem', color: 'var(--accent)' }}>عرض الكل</a>
              </div>
              {recentSales.length === 0 ? (
                <p style={{ fontSize: '.85rem', color: 'var(--text-muted)', textAlign: 'center', padding: '12px 0' }}>لا توجد مبيعات</p>
              ) : recentSales.map((s) => (
                <div className="list-item" key={s.id}>
                  <div className="list-item-icon" style={{ background: '#dcfce7', color: 'var(--success)' }}>💰</div>
                  <div className="list-item-body">
                    <div className="list-item-title">{s.customer_name || s.notes || 'بيع'}</div>
                    <div className="list-item-sub">{s.date}</div>
                  </div>
                  <div className="list-item-end">
                    <div className="list-item-amount positive">{fmt(s.amount_lyd)} د.ل</div>
                  </div>
                </div>
              ))}
            </div>

            {/* Recent Purchases */}
            <div className="card">
              <div className="section-header">
                <span className="section-title">آخر المشتريات</span>
                <a href="/purchases" style={{ fontSize: '.78rem', color: 'var(--accent)' }}>عرض الكل</a>
              </div>
              {recentPurchases.length === 0 ? (
                <p style={{ fontSize: '.85rem', color: 'var(--text-muted)', textAlign: 'center', padding: '12px 0' }}>لا توجد مشتريات</p>
              ) : recentPurchases.map((p) => (
                <div className="list-item" key={p.id}>
                  <div className="list-item-icon" style={{ background: '#fee2e2', color: 'var(--danger)' }}>🛒</div>
                  <div className="list-item-body">
                    <div className="list-item-title">{p.supplier_name || p.notes || 'شراء'}</div>
                    <div className="list-item-sub">{p.date}</div>
                  </div>
                  <div className="list-item-end">
                    <div className="list-item-amount negative">{fmt(p.amount_lyd)} د.ل</div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      <BottomNav />
    </div>
  );
}
