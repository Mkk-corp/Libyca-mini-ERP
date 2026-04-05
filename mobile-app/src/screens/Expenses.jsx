import { useState, useEffect, useCallback } from 'react';
import TopBar from '../components/TopBar';
import BottomNav from '../components/BottomNav';
import { showToast } from '../components/Toast';
import { expenses as expensesApi } from '../api/client';

const fmt = (n) => new Intl.NumberFormat('ar-LY').format(n ?? 0);

const CATS = {
  1:'نقل', 2:'ديزل/وقود', 3:'عمالة', 4:'صيانة', 5:'كهرباء',
  6:'مياه', 7:'إيجار', 8:'اتصالات', 9:'مصاريف إدارية', 10:'أخرى',
  11:'مقدم بضاعة', 12:'شوالات', 13:'مطبخ',
};

export default function Expenses() {
  const [data, setData]       = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage]       = useState(1);
  const [meta, setMeta]       = useState({});
  const [sheet, setSheet]     = useState(false);
  const [form, setForm]       = useState({ date: today(), amount_lyd: '', category_id: '10', notes: '' });
  const [saving, setSaving]   = useState(false);

  function today() { return new Date().toISOString().slice(0, 10); }

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await expensesApi.list({ page, per_page: 20 });
      setData(res.data || []);
      setMeta(res.meta || {});
    } catch { } finally { setLoading(false); }
  }, [page]);

  useEffect(() => { load(); }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await expensesApi.create({
        ...form,
        amount_lyd: Number(form.amount_lyd),
        category_id: Number(form.category_id),
      });
      setSheet(false);
      showToast('تمت إضافة المصروف');
      load();
    } catch (err) {
      showToast(err.response?.data?.detail || 'فشل الحفظ', 'error');
    } finally { setSaving(false); }
  };

  return (
    <div className="screen">
      <TopBar title="المصروفات" />
      <div className="screen-content">
        {loading ? (
          <div className="spinner-wrap"><div className="spinner" /></div>
        ) : data.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">💸</div>
            <div className="empty-text">لا توجد مصروفات</div>
          </div>
        ) : (
          <div className="card" style={{ padding: 0 }}>
            {data.map((e) => (
              <div className="list-item" key={e.id} style={{ padding: '12px 14px' }}>
                <div className="list-item-icon" style={{ background: '#fef3c7', color: '#d97706' }}>💸</div>
                <div className="list-item-body">
                  <div className="list-item-title">{CATS[e.category_id] || 'أخرى'}</div>
                  <div className="list-item-sub">{e.date}{e.notes ? ` · ${e.notes}` : ''}</div>
                </div>
                <div className="list-item-end">
                  <div className="list-item-amount" style={{ color: '#dc2626' }}>{fmt(e.amount_lyd)} د.ل</div>
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

      <button className="fab" onClick={() => { setForm({ date: today(), amount_lyd: '', category_id: '10', notes: '' }); setSheet(true); }}>+</button>

      {sheet && (
        <div className="sheet-overlay" onClick={(e) => e.target === e.currentTarget && setSheet(false)}>
          <div className="sheet">
            <div className="sheet-handle" />
            <div className="sheet-title">إضافة مصروف</div>
            <form onSubmit={submit}>
              <div className="field-group">
                <label className="field-label">التاريخ</label>
                <input type="date" className="field-input" value={form.date}
                  onChange={(e) => setForm({ ...form, date: e.target.value })} required />
              </div>
              <div className="field-group">
                <label className="field-label">الفئة</label>
                <select className="field-input" value={form.category_id}
                  onChange={(e) => setForm({ ...form, category_id: e.target.value })}>
                  {Object.entries(CATS).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>
              <div className="field-group">
                <label className="field-label">المبلغ (د.ل)</label>
                <input type="number" className="field-input" placeholder="0" min="0" step="0.01"
                  value={form.amount_lyd} onChange={(e) => setForm({ ...form, amount_lyd: e.target.value })} required />
              </div>
              <div className="field-group">
                <label className="field-label">ملاحظات</label>
                <input type="text" className="field-input" placeholder="اختياري"
                  value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
              </div>
              <button type="submit" className="btn btn-primary btn-full" disabled={saving}
                style={{ height: 48, fontSize: '1rem' }}>
                {saving ? 'جاري الحفظ...' : 'حفظ المصروف'}
              </button>
            </form>
          </div>
        </div>
      )}

      <BottomNav />
    </div>
  );
}
