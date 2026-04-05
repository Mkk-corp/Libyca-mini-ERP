export default function TopBar({ title, right, left }) {
  return (
    <header className="topbar">
      {right || <div style={{ width: 36 }} />}
      <h1 className="topbar-title" style={{ textAlign: 'center' }}>{title}</h1>
      {left || <div style={{ width: 36 }} />}
    </header>
  );
}
