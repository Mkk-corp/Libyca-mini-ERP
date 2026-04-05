import { useState, useEffect, useCallback } from 'react';
import TopBar from '../components/TopBar';
import BottomNav from '../components/BottomNav';
import { showToast } from '../components/Toast';
import { items as itemsApi } from '../api/client';

export default function Items() {
  const [data, setData]       = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch]   = useState('');
  const [sheet, setSheet]     = useState(false);
  const [form, setForm]       = useState({ name: '', unit: 'طن', description: '' });
  const [saving, setSaving]   = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await itemsApi.list({ per_page: 200, search });
      setData(res.data || []);
    } catch { } finally { setLoading(false); }
  }, [search]);

  useEffect(() => { load(); }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await itemsApi.create(form);
      setSheet(false);
      showToast('تمت إضافة الصنف');
      load();
    } catch (err) {
      showToast(err.response?.data?.detail || 'فشل الحفظ', 'error');
    } finally { setSaving(false); }
  };

  const COLORS = ['#dcfce7','#fee2e2','#fef3c7','#dbeafe','#f3e8ff','var(--lime-lt)'];
  const color = (i) => COLORS[i % COLORS.length];

  return (
    <div className="screen">
      <TopBar title="الأصناف" />
      <div className="screen-content">
        <div className="search-wrap">
          <span className="search-icon">🔍</span>
          <input className="search-input" placeholder="بحث في الأصناف..." value={search}
            onChange={(e) => setSearch(e.target.value)} />
        </div>

        {loading ? (
          <div className="spinner-wrap"><div className="spinner" /></div>
        ) : data.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🏷</div>
            <div className="empty-text">لا توجد أصناف</div>
          </div>
        ) : (
          <div className="card" style={{ padding: 0 }}>
            {data.map((item, i) => (
              <div className="list-item" key={item.id} style={{ padding: '12px 14px' }}>
                <div className="list-item-icon" style={{ background: color(i), fontSize: '1.2rem' }}>
                  {item.name?.[0] || '📦'}
                </div>
                <div className="list-item-body">
                  <div className="list-item-title">{item.name}</div>
                  <div className="list-item-sub">{item.unit || 'طن'}{item.description ? ` · ${item.description}` : ''}</div>
                </div>
                <div className="list-item-end">
                  <span className="badge badge-gray">#{item.id}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <button className="fab" onClick={() => { setForm({ name: '', unit: 'طن', description: '' }); setSheet(true); }}>+</button>

      {sheet && (
        <div className="sheet-overlay" onClick={(e) => e.target === e.currentTarget && setSheet(false)}>
          <div className="sheet">
            <div className="sheet-handle" />
            <div className="sheet-title">إضافة صنف جديد</div>
            <form onSubmit={submit}>
              <div className="field-group">
                <label className="field-label">اسم الصنف</label>
                <input type="text" className="field-input" placeholder="مثال: بلاستيك PET"
                  value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              </div>
              <div className="field-group">
                <label className="field-label">الوحدة</label>
                <select className="field-input" value={form.unit}
                  onChange={(e) => setForm({ ...form, unit: e.target.value })}>
                  <option value="طن">طن</option>
                  <option value="كغ">كغ</option>
                  <option value="قطعة">قطعة</option>
                  <option value="حبة">حبة</option>
                  <option value="متر">متر</option>
                </select>
              </div>
              <div className="field-group">
                <label className="field-label">وصف (اختياري)</label>
                <input type="text" className="field-input" placeholder="وصف مختصر"
                  value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </div>
              <button type="submit" className="btn btn-primary btn-full" disabled={saving}
                style={{ height: 48, fontSize: '1rem' }}>
                {saving ? 'جاري الحفظ...' : 'حفظ الصنف'}
              </button>
            </form>
          </div>
        </div>
      )}

      <BottomNav />
    </div>
  );
}
