import { useState, useEffect } from 'react';
import TopBar from '../components/TopBar';
import BottomNav from '../components/BottomNav';
import { inventory } from '../api/client';

const fmt = (n) => new Intl.NumberFormat('ar-LY', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n ?? 0);

export default function Inventory() {
  const [data, setData]       = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch]   = useState('');

  useEffect(() => {
    setLoading(true);
    inventory.list({ per_page: 200 })
      .then((r) => setData(r.data || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = data.filter((d) =>
    !search || d.item_name?.toLowerCase().includes(search.toLowerCase())
  );

  const stockColor = (qty) => {
    if (qty <= 0) return { bg: '#fee2e2', color: '#dc2626' };
    if (qty < 5)  return { bg: '#fef3c7', color: '#d97706' };
    return { bg: '#dcfce7', color: '#16a34a' };
  };

  return (
    <div className="screen">
      <TopBar title="المخزون" />
      <div className="screen-content">
        <div className="search-wrap">
          <span className="search-icon">🔍</span>
          <input className="search-input" placeholder="بحث في المخزون..." value={search}
            onChange={(e) => setSearch(e.target.value)} />
        </div>

        {loading ? (
          <div className="spinner-wrap"><div className="spinner" /></div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📦</div>
            <div className="empty-text">المخزون فارغ</div>
          </div>
        ) : (
          <>
            {/* Summary */}
            <div className="stat-grid" style={{ marginBottom: 12 }}>
              <div className="stat-card">
                <div className="stat-label">عدد الأصناف</div>
                <div className="stat-value">{filtered.length}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">المخزون الكلي</div>
                <div className="stat-value positive">
                  {fmt(filtered.reduce((s, d) => s + (d.stock ?? 0), 0))} طن
                </div>
              </div>
            </div>

            <div className="card" style={{ padding: 0 }}>
              {filtered.map((d) => {
                const { bg, color } = stockColor(d.stock);
                return (
                  <div className="list-item" key={d.item_id} style={{ padding: '12px 14px' }}>
                    <div className="list-item-icon" style={{ background: bg, color }}>📦</div>
                    <div className="list-item-body">
                      <div className="list-item-title">{d.item_name}</div>
                      <div className="list-item-sub">
                        وارد: {fmt(d.purchased)} · صادر: {fmt(d.sold)}
                      </div>
                    </div>
                    <div className="list-item-end">
                      <div style={{ fontWeight: 700, color, fontSize: '.92rem' }}>
                        {fmt(d.stock)} طن
                      </div>
                      <span className="badge" style={{ background: bg, color, fontSize: '.68rem' }}>
                        {d.stock <= 0 ? 'نفد' : d.stock < 5 ? 'منخفض' : 'متوفر'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
      <BottomNav />
    </div>
  );
}
