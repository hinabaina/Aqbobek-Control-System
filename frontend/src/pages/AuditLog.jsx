import React, { useEffect, useState } from "react";
import api from "@/lib/api";

const ENTITY_COLORS = {
  ribbon: "bg-indigo-50 text-indigo-700 border-indigo-200",
  substitution: "bg-amber-50 text-amber-700 border-amber-200",
  schedule: "bg-slate-900 text-white border-slate-900",
  task: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

export default function AuditLog() {
  const [rows, setRows] = useState([]);
  const [entity, setEntity] = useState("");

  const load = () => api.get(`/audit${entity ? `?entity=${entity}` : ""}`).then(r => setRows(r.data));
  useEffect(() => { load(); }, [entity]);

  return (
    <div className="space-y-4">
      <div>
        <div className="text-xs uppercase tracking-widest font-bold text-slate-500">Audit Log</div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 mt-1">Журнал изменений</h1>
        <p className="text-sm text-slate-500 mt-1">Кто, когда и что менял в расписании, лентах и заменах</p>
      </div>

      <div className="flex items-center gap-2">
        {["", "schedule", "ribbon", "substitution", "task"].map(e => (
          <button key={e} onClick={() => setEntity(e)} className={`h-9 px-3 rounded-lg text-xs font-bold uppercase tracking-wider ${entity === e ? "bg-slate-900 text-white" : "bg-white border border-slate-200 text-slate-600"}`}>
            {e || "все"}
          </button>
        ))}
      </div>

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr className="text-left text-xs uppercase tracking-wider font-bold text-slate-500">
              <th className="py-2.5 px-4">Время</th>
              <th className="py-2.5 px-4">Кто</th>
              <th className="py-2.5 px-4">Сущность</th>
              <th className="py-2.5 px-4">Действие</th>
              <th className="py-2.5 px-4">Детали</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.id} className="border-b border-slate-100">
                <td className="py-2.5 px-4 font-mono text-xs text-slate-500">{new Date(r.created_at).toLocaleString("ru-RU")}</td>
                <td className="py-2.5 px-4 font-bold text-slate-900">{r.actor_name}</td>
                <td className="py-2.5 px-4">
                  <span className={`inline-flex items-center text-[10px] uppercase tracking-wider font-bold rounded-full px-2 py-0.5 border ${ENTITY_COLORS[r.entity] || "bg-slate-100 text-slate-700"}`}>
                    {r.entity}
                  </span>
                </td>
                <td className="py-2.5 px-4 font-mono text-xs text-slate-700">{r.action}</td>
                <td className="py-2.5 px-4 font-mono text-[11px] text-slate-500 max-w-lg truncate">{r.payload}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={5} className="py-10 text-center text-slate-400 italic">Журнал пуст</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
