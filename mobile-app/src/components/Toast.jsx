import { useState, useEffect, useCallback } from 'react';

let _show = null;

export function showToast(message, type = 'success', duration = 3000) {
  if (_show) _show({ message, type, duration });
}

export default function ToastProvider() {
  const [toast, setToast] = useState(null);

  useEffect(() => {
    _show = setToast;
    return () => { _show = null; };
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), toast.duration);
    return () => clearTimeout(t);
  }, [toast]);

  if (!toast) return null;
  return (
    <div className={`toast ${toast.type}`} onClick={() => setToast(null)}>
      {toast.type === 'success' ? '✓' : '✕'}
      <span>{toast.message}</span>
    </div>
  );
}
