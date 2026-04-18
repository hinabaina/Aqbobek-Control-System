import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from "recharts";

export default function Canteen() {
  const [rows, setRows] = useState([]);
  const [summary, setSummary] = useState(null);
  const [form, setForm] = useState({ date: new Date().toISOString().slice(0,10), class_name: "", students_count: "" });

  const load = () => {
    api.get("/canteen").then(r => setRows(r.data));
    api.get("/canteen/summary").then(r => setSummary(r.data));
  };
  useEffect(() => { load(); }, []);

  const save = async (e) => {
    e.preventDefault();
    await api.post("/canteen", { ...form, students_count: Number(form.students_count) });
    setForm({ date: new Date().toISOString().slice(0,10), class_name: "", students_count: "" });
    load();
  };

  return (
    <div className="space-y-5">
      <div>
        <div className="text-xs uppercase tracking-widest font-bold text-slate-500">Столовая</div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 mt-1">Заявки в столовую</h1>
        <p className="text-sm text-slate-500 mt-1">Свод от учителей — из бота и с дашборда. Считается автоматически.</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <div className="xl:col-span-2 bg-white border border-slate-200 rounded-xl p-5">
          <div className="text-xs uppercase tracking-widest font-bold text-slate-500">Сегодня</div>
          <div className="mt-2 flex items-baseline gap-3">
            <div className="text-5xl font-extrabold tracking-tight text-slate-900">
              {summary?.today?.reduce((s, t) => s + (t.students || 0), 0) || 0}
            </div>
            <div className="text-sm text-slate-500">порций</div>
          </div>
          <div className="mt-5 h-56">
            <ResponsiveContainer>
              <BarChart data={summary?.by_day || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" fontSize={11} tick={{ fill: "#64748b" }} />
                <YAxis fontSize={11} tick={{ fill: "#64748b" }} />
                <Tooltip cursor={{ fill: "#f1f5f9" }} />
                <Bar dataKey="total" fill="#0f172a" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <form onSubmit={save} className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="text-xs uppercase tracking-widest font-bold text-slate-500">Добавить заявку</div>
          <h3 className="text-lg font-extrabold text-slate-900 mt-1">Ввод от учителя</h3>
          <div className="mt-4 space-y-3">
            <input type="date" value={form.date} onChange={(e) => setForm(f => ({ ...f, date: e.target.value }))} className="w-full h-10 rounded-lg border border-slate-300 px-3 text-sm" />
            <input placeholder="Класс (напр. 3А)" value={form.class_name} onChange={(e) => setForm(f => ({ ...f, class_name: e.target.value }))} className="w-full h-10 rounded-lg border border-slate-300 px-3 text-sm" />
            <input type="number" min="0" placeholder="Количество детей" value={form.students_count} onChange={(e) => setForm(f => ({ ...f, students_count: e.target.value }))} className="w-full h-10 rounded-lg border border-slate-300 px-3 text-sm" />
            <button type="submit" data-testid="button-save-canteen" className="w-full h-10 rounded-lg bg-slate-900 text-white text-sm font-bold hover:bg-slate-800">Сохранить</button>
          </div>
        </form>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <div className="text-xs uppercase tracking-widest font-bold text-slate-500">История</div>
            <h3 className="text-lg font-extrabold text-slate-900">Заявки по дням</h3>
          </div>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr className="text-left text-xs uppercase tracking-wider font-bold text-slate-500">
              <th className="py-2.5 px-5">Дата</th>
              <th className="py-2.5 px-5">Класс</th>
              <th className="py-2.5 px-5">Порций</th>
              <th className="py-2.5 px-5">Заметки</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? rows.map(r => (
              <tr key={r.id} className="border-b border-slate-100">
                <td className="py-2.5 px-5 font-mono text-xs text-slate-600">{r.date}</td>
                <td className="py-2.5 px-5 font-bold text-slate-900">{r.class_name}</td>
                <td className="py-2.5 px-5">{r.students_count}</td>
                <td className="py-2.5 px-5 text-slate-500 text-xs">{r.notes || "—"}</td>
              </tr>
            )) : (
              <tr><td colSpan={4} className="py-10 text-center text-slate-400 italic">Пока нет записей — добавь первую заявку справа или через Telegram-бота</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
