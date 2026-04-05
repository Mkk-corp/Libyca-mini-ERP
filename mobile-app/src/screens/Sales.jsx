import { useState, useEffect, useCallback } from 'react';
import TopBar from '../components/TopBar';
import BottomNav from '../components/BottomNav';
import OfflineBanner from '../components/OfflineBanner';
import { showToast } from '../components/Toast';
import { sales as salesApi, items as itemsApi, customers as customersApi } from '../api/client';

const fmt = (n) => new Intl.NumberFormat('ar-LY').format(n ?? 0);

export default function Sales() {
  const [data, setData]         = useState([]);
  const [loading, setLoading]   = useState(true);
  const [page, setPage]         = useState(1);
  const [meta, setMeta]         = useState({});
  const [search, setSearch]     = useState('');
  const [sheet, setSheet]       = useState(false);
  const [form, setForm]         = useState({ date: today(), item_id: '', customer_id: '', qty: '', price_lyd: '', notes: '' });
  const [items, setItems]       = useState([]);
  const [customers, setCustomers] = useState([]);
  const [saving, setSaving]     = useState(false);

  function today() { return new Date().toISOString().slice(0, 10); }

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await salesApi.list({ page, per_page: 20, search });
      setData(res.data || []);
      setMeta(res.meta || {});
    } catch { } finally { setLoading(false); }
  }, [page, search]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    Promise.all([
      itemsApi.list({ per_page: 200 }),
      customersApi.list({ per_page: 200 }),
    ]).then(([i, c]) => {
      setItems(i.data || []);
      setCustomers(c.data || []);
    });
  }, []);

  const openSheet = () => {
    setForm({ date: today(), item_id: '', customer_id: '', qty: '', price_lyd: '', notes: '' });
    setSheet(true);
  };

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await salesApi.create({
        ...form,
        item_id: Number(form.item_id) || null,
        customer_id: Number(form.customer_id) || null,
        qty: Number(form.qty),
        price_lyd: Number(form.price_lyd),
      });
      setSheet(false);
      showToast('تمت إضافة البيع بنجاح');
      load();
    } catch (err) {
      showToast(err.response?.data?.detail || 'فشل الحفظ', 'error');
    } finally { setSaving(false); }
  };

  return (
    <div className="screen">
      <TopBar title="المبيعات" />
      <OfflineBanner />

      <div className="screen-content">
        <div className="search-wrap">
          <span className="search-icon">🔍</span>
          <input
            className="search-input"
            placeholder="بحث..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>

        {loading ? (
          <div className="spinner-wrap"><div className="spinner" /></div>
        ) : data.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">💰</div>
            <div className="empty-text">لا توجد مبيعات</div>
          </div>
        ) : (
          <div className="card" style={{ padding: 0 }}>
            {data.map((s) => (
              <div className="list-item" key={s.id} style={{ padding: '12px 14px' }}>
                <div className="list-item-icon" style={{ background: '#dcfce7', color: '#16a34a' }}>💰</div>
                <div className="list-item-body">
                  <div className="list-item-title">{s.customer_name || s.item_name || 'بيع'}</div>
                  <div className="list-item-sub">{s.date} {s.item_name ? `· ${s.item_name}` : ''}</div>
                </div>
                <div className="list-item-end">
                  <div className="list-item-amount" style={{ color: '#16a34a' }}>{fmt(s.amount_lyd)} د.ل</div>
                  {s.qty && <div style={{ fontSize: '.72rem', color: 'var(--text-muted)' }}>الكمية: {s.qty}</div>}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {meta.pages > 1 && (
          <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 12 }}>
            <button className="btn btn-ghost" style={{ padding: '8px 16px', fontSize: '.82rem' }}
              disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>→ السابق</button>
            <span style={{ lineHeight: '36px', fontSize: '.82rem', color: 'var(--text-muted)' }}>
              {page} / {meta.pages}
            </span>
            <button className="btn btn-ghost" style={{ padding: '8px 16px', fontSize: '.82rem' }}
              disabled={page >= meta.pages} onClick={() => setPage((p) => p + 1)}>التالي ←</button>
          </div>
        )}
      </div>

      {/* FAB */}
      <button className="fab" onClick={openSheet} title="إضافة بيع">+</button>

      {/* Add sheet */}
      {sheet && (
        <div className="sheet-overlay" onClick={(e) => e.target === e.currentTarget && setSheet(false)}>
          <div className="sheet">
            <div className="sheet-handle" />
            <div className="sheet-title">إضافة بيع جديد</div>
            <form onSubmit={submit}>
              <div className="field-group">
                <label className="field-label">التاريخ</label>
                <input type="date" className="field-input" value={form.date}
                  onChange={(e) => setForm({ ...form, date: e.target.value })} required />
              </div>
              <div className="field-group">
                <label className="field-label">الصنف</label>
                <select className="field-input" value={form.item_id}
                  onChange={(e) => setForm({ ...form, item_id: e.target.value })}>
                  <option value="">— اختر صنف —</option>
                  {items.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
                </select>
              </div>
              <div className="field-group">
                <label className="field-label">العميل</label>
                <select className="field-input" value={form.customer_id}
                  onChange={(e) => setForm({ ...form, customer_id: e.target.value })}>
                  <option value="">— اختر عميل —</option>
                  {customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div className="field-group">
                  <label className="field-label">الكمية (طن)</label>
                  <input type="number" className="field-input" placeholder="0" min="0" step="0.01"
                    value={form.qty} onChange={(e) => setForm({ ...form, qty: e.target.value })} required />
                </div>
                <div className="field-group">
                  <label className="field-label">السعر (د.ل)</label>
                  <input type="number" className="field-input" placeholder="0" min="0" step="0.01"
                    value={form.price_lyd} onChange={(e) => setForm({ ...form, price_lyd: e.target.value })} required />
                </div>
              </div>
              <div className="field-group">
                <label className="field-label">ملاحظات</label>
                <input type="text" className="field-input" placeholder="اختياري"
                  value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
              </div>
              <button type="submit" className="btn btn-primary btn-full" disabled={saving}
                style={{ height: 48, fontSize: '1rem' }}>
                {saving ? 'جاري الحفظ...' : 'حفظ البيع'}
              </button>
            </form>
          </div>
        </div>
      )}

      <BottomNav />
    </div>
  );
}
