import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Plus, Trash2, Link2 } from "lucide-react";

export default function Employees() {
  const [rows, setRows] = useState([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ full_name: "", role: "Учитель", subject: "", email: "", user_role: "teacher" });
  const [search, setSearch] = useState("");

  const load = () => api.get("/employees").then(r => setRows(r.data));
  useEffect(() => { load(); }, []);

  const save = async (e) => {
    e.preventDefault();
    await api.post("/employees", form);
    setCreating(false);
    setForm({ full_name: "", role: "Учитель", subject: "", email: "", user_role: "teacher" });
    load();
  };

  const del = async (id) => {
    if (!window.confirm("Удалить сотрудника?")) return;
    await api.delete(`/employees/${id}`);
    load();
  };

  const filtered = rows.filter(r =>
    !search || r.full_name.toLowerCase().includes(search.toLowerCase()) ||
    (r.subject || "").toLowerCase().includes(search.toLowerCase()) ||
    (r.role || "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-widest font-bold text-slate-500">Справочник</div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 mt-1">Сотрудники</h1>
          <p className="text-sm text-slate-500 mt-1">База педагогов и персонала. Синхронизирована с Telegram-ботом.</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            placeholder="Поиск..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-10 rounded-lg border border-slate-200 px-3 text-sm w-56 bg-white"
            data-testid="input-search-employee"
          />
          <button
            onClick={() => setCreating(true)}
            data-testid="button-create-employee"
            className="h-10 inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 text-sm font-bold text-white hover:bg-slate-800"
          >
            <Plus size={16} /> Добавить
          </button>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr className="text-left text-xs uppercase tracking-wider font-bold text-slate-500">
              <th className="py-3 px-4">ID</th>
              <th className="py-3 px-4">ФИО</th>
              <th className="py-3 px-4">Должность</th>
              <th className="py-3 px-4">Предмет</th>
              <th className="py-3 px-4">Почта</th>
              <th className="py-3 px-4">Telegram</th>
              <th className="py-3 px-4"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(r => (
              <tr key={r.id} className="border-b border-slate-100 hover:bg-slate-50/50" data-testid={`row-employee-${r.id}`}>
                <td className="py-3 px-4 text-xs font-mono text-slate-400">{r.id}</td>
                <td className="py-3 px-4">
                  <div className="font-bold text-slate-900">{r.full_name}</div>
                  {r.user_role === "director" && <div className="text-[10px] uppercase tracking-widest font-bold text-amber-600 mt-0.5">Директор</div>}
                </td>
                <td className="py-3 px-4 text-slate-700">{r.role}</td>
                <td className="py-3 px-4 text-slate-500">{r.subject || "—"}</td>
                <td className="py-3 px-4 font-mono text-xs text-slate-500">{r.email || "—"}</td>
                <td className="py-3 px-4">
                  {r.telegram_id ? (
                    <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-50 rounded-full px-2.5 py-0.5 border border-emerald-200">
                      <Link2 size={11} /> {r.telegram_id}
                    </span>
                  ) : (
                    <span className="text-xs text-slate-400">Не привязан</span>
                  )}
                </td>
                <td className="py-3 px-4 text-right">
                  <button onClick={() => del(r.id)} className="text-slate-400 hover:text-red-600" title="Удалить">
                    <Trash2 size={15} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {creating && (
        <div className="fixed inset-0 bg-slate-900/40 z-40 flex items-center justify-center p-4" onClick={() => setCreating(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={save} className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-6">
            <h3 className="text-xl font-extrabold text-slate-900">Новый сотрудник</h3>
            <div className="mt-4 space-y-3">
              <input required placeholder="ФИО" value={form.full_name} onChange={(e) => setForm(f => ({ ...f, full_name: e.target.value }))} className="w-full h-10 rounded-lg border border-slate-300 px-3 text-sm" />
              <input placeholder="Должность" value={form.role} onChange={(e) => setForm(f => ({ ...f, role: e.target.value }))} className="w-full h-10 rounded-lg border border-slate-300 px-3 text-sm" />
              <input placeholder="Предмет / квалификация" value={form.subject} onChange={(e) => setForm(f => ({ ...f, subject: e.target.value }))} className="w-full h-10 rounded-lg border border-slate-300 px-3 text-sm" />
              <input type="email" placeholder="Почта" value={form.email} onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))} className="w-full h-10 rounded-lg border border-slate-300 px-3 text-sm" />
              <select value={form.user_role} onChange={(e) => setForm(f => ({ ...f, user_role: e.target.value }))} className="w-full h-10 rounded-lg border border-slate-300 px-3 text-sm">
                <option value="teacher">Учитель</option>
                <option value="director">Директор</option>
              </select>
              <div className="text-xs text-slate-500">Пароль по умолчанию: <span className="font-mono">teacher123</span></div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setCreating(false)} className="h-10 rounded-lg border border-slate-200 px-4 text-sm font-bold text-slate-700">Отмена</button>
              <button type="submit" className="h-10 rounded-lg bg-slate-900 px-4 text-sm font-bold text-white">Сохранить</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
