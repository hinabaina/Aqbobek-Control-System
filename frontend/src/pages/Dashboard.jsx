import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Users, AlertOctagon, UtensilsCrossed, Repeat, MessageSquareMore, ListTodo, TrendingUp } from "lucide-react";

function Kpi({ label, value, icon: Icon, accent = "slate" }) {
  const accents = {
    slate: "bg-slate-900 text-white",
    amber: "bg-amber-500 text-white",
    red: "bg-red-500 text-white",
    emerald: "bg-emerald-500 text-white",
    indigo: "bg-indigo-500 text-white",
    cyan: "bg-cyan-600 text-white",
  };
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 fade-up" data-testid={`kpi-${label}`}>
      <div className="flex items-start justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-widest font-bold text-slate-500">{label}</div>
          <div className="text-3xl font-extrabold text-slate-900 mt-2 tracking-tight">{value ?? "—"}</div>
        </div>
        <div className={`h-9 w-9 rounded-lg grid place-items-center ${accents[accent]}`}>
          <Icon size={17} strokeWidth={2.3} />
        </div>
      </div>
    </div>
  );
}

function heatColor(v) {
  if (v === 0) return "bg-slate-100 text-slate-400";
  if (v <= 2) return "bg-amber-100 text-amber-900";
  if (v <= 4) return "bg-amber-300 text-amber-950";
  if (v === 5) return "bg-orange-500 text-white";
  return "bg-red-600 text-white";
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [heat, setHeat] = useState(null);

  const load = () => {
    api.get("/dashboard/stats").then(r => setStats(r.data));
    api.get("/dashboard/heatmap").then(r => setHeat(r.data));
  };
  useEffect(() => { load(); const i = setInterval(load, 30000); return () => clearInterval(i); }, []);

  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs uppercase tracking-widest font-bold text-slate-500">Панель управления</div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 mt-1">Дашборд директора</h1>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        <Kpi label="Сотрудники" value={stats?.employees} icon={Users} />
        <Kpi label="Инциденты" value={stats?.incidents_open} icon={AlertOctagon} accent="red" />
        <Kpi label="Задачи" value={stats?.tasks_open} icon={ListTodo} accent="amber" />
        <Kpi label="Порции сегодня" value={stats?.canteen_today} icon={UtensilsCrossed} accent="emerald" />
        <Kpi label="Замен сегодня" value={stats?.substitutions_today} icon={Repeat} accent="indigo" />
        <Kpi label="Сообщений / 7дн" value={stats?.messages_week} icon={MessageSquareMore} accent="cyan" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 bg-white border border-slate-200 rounded-xl p-5" data-testid="widget-heatmap">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-xs uppercase tracking-widest font-bold text-slate-500">Тепловая карта</div>
              <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">Нагрузка учителей · часы/день</h2>
            </div>
            <div className="flex items-center gap-1 text-[10px] uppercase font-bold tracking-wider">
              <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-500">0</span>
              <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-900">1-2</span>
              <span className="px-2 py-0.5 rounded bg-amber-300 text-amber-950">3-4</span>
              <span className="px-2 py-0.5 rounded bg-orange-500 text-white">5</span>
              <span className="px-2 py-0.5 rounded bg-red-600 text-white">6+</span>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="text-left font-bold text-slate-500 text-xs uppercase tracking-wider pb-2">Сотрудник</th>
                  {heat?.days.map(d => (
                    <th key={d} className="text-center font-bold text-slate-500 text-xs uppercase tracking-wider pb-2 px-2">{d.slice(0,2)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heat?.rows.map(r => (
                  <tr key={r.teacher_id}>
                    <td className="pr-4 py-1.5">
                      <div className="text-sm font-semibold text-slate-900 truncate max-w-xs">{r.full_name}</div>
                      <div className="text-[11px] text-slate-500">{r.subject || "—"}</div>
                    </td>
                    {heat.days.map(d => (
                      <td key={d} className="px-1 py-1">
                        <div className={`heat-cell h-8 rounded text-xs font-bold flex items-center justify-center ${heatColor(r[d])}`}>
                          {r[d] || ""}
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5" data-testid="widget-recent-incidents">
          <div className="text-xs uppercase tracking-widest font-bold text-slate-500">Последние инциденты</div>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">Что сломалось</h2>
          <div className="mt-4 space-y-2">
            {stats?.incidents_recent?.length ? stats.incidents_recent.map(i => (
              <div key={i.id} className="border border-slate-200 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <span className={`h-1.5 w-1.5 rounded-full mt-2 ${
                    i.priority === "high" ? "bg-red-500" : i.priority === "medium" ? "bg-amber-500" : "bg-slate-400"
                  }`} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-bold text-slate-900 truncate">{i.title}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      {new Date(i.created_at).toLocaleString("ru-RU")} · {i.status}
                    </div>
                  </div>
                </div>
              </div>
            )) : <div className="text-sm text-slate-500 italic">Инцидентов пока нет — тишина</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
