import { useState, useEffect, useCallback } from 'react';
import TopBar from '../components/TopBar';
import BottomNav from '../components/BottomNav';
import OfflineBanner from '../components/OfflineBanner';
import { showToast } from '../components/Toast';
import { purchases as purchasesApi, items as itemsApi, suppliers as suppliersApi } from '../api/client';

const fmt = (n) => new Intl.NumberFormat('ar-LY').format(n ?? 0);

export default function Purchases() {
  const [data, setData]       = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage]       = useState(1);
  const [meta, setMeta]       = useState({});
  const [search, setSearch]   = useState('');
  const [sheet, setSheet]     = useState(false);
  const [form, setForm]       = useState({ date: today(), item_id: '', supplier_id: '', qty: '', price_lyd: '', notes: '' });
  const [items, setItems]     = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [saving, setSaving]   = useState(false);

  function today() { return new Date().toISOString().slice(0, 10); }

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await purchasesApi.list({ page, per_page: 20, search });
      setData(res.data || []);
      setMeta(res.meta || {});
    } catch { } finally { setLoading(false); }
  }, [page, search]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    Promise.all([itemsApi.list({ per_page: 200 }), suppliersApi.list({ per_page: 200 })])
      .then(([i, s]) => { setItems(i.data || []); setSuppliers(s.data || []); });
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await purchasesApi.create({
        ...form,
        item_id: Number(form.item_id) || null,
        supplier_id: Number(form.supplier_id) || null,
        qty: Number(form.qty),
        price_lyd: Number(form.price_lyd),
      });
      setSheet(false);
      showToast('تمت إضافة الشراء بنجاح');
      load();
    } catch (err) {
      showToast(err.response?.data?.detail || 'فشل الحفظ', 'error');
    } finally { setSaving(false); }
  };

  return (
    <div className="screen">
      <TopBar title="المشتريات" />
      <OfflineBanner />

      <div className="screen-content">
        <div className="search-wrap">
          <span className="search-icon">🔍</span>
          <input className="search-input" placeholder="بحث..." value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
        </div>

        {loading ? (
          <div className="spinner-wrap"><div className="spinner" /></div>
        ) : data.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🛒</div>
            <div className="empty-text">لا توجد مشتريات</div>
          </div>
        ) : (
          <div className="card" style={{ padding: 0 }}>
            {data.map((p) => (
              <div className="list-item" key={p.id} style={{ padding: '12px 14px' }}>
                <div className="list-item-icon" style={{ background: '#fee2e2', color: '#dc2626' }}>🛒</div>
                <div className="list-item-body">
                  <div className="list-item-title">{p.supplier_name || p.item_name || 'شراء'}</div>
                  <div className="list-item-sub">{p.date}{p.item_name ? ` · ${p.item_name}` : ''}</div>
                </div>
                <div className="list-item-end">
                  <div className="list-item-amount" style={{ color: '#dc2626' }}>{fmt(p.amount_lyd)} د.ل</div>
                  {p.qty && <div style={{ fontSize: '.72rem', color: 'var(--text-muted)' }}>الكمية: {p.qty}</div>}
                </div>
              </div>
            ))}
          </div>
        )}

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

      <button className="fab" onClick={() => { setForm({ date: today(), item_id: '', supplier_id: '', qty: '', price_lyd: '', notes: '' }); setSheet(true); }}>+</button>

      {sheet && (
        <div className="sheet-overlay" onClick={(e) => e.target === e.currentTarget && setSheet(false)}>
          <div className="sheet">
            <div className="sheet-handle" />
            <div className="sheet-title">إضافة شراء جديد</div>
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
                <label className="field-label">المورد</label>
                <select className="field-input" value={form.supplier_id}
                  onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}>
                  <option value="">— اختر مورد —</option>
                  {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
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
                {saving ? 'جاري الحفظ...' : 'حفظ الشراء'}
              </button>
            </form>
          </div>
        </div>
      )}

      <BottomNav />
    </div>
  );
}
