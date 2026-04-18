import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Check, X, Clock, Repeat } from "lucide-react";

export default function SubstitutionInbox() {
  const [pending, setPending] = useState([]);
  const [err, setErr] = useState("");

  const load = () => api.get("/substitutions/pending_for_me").then(r => setPending(r.data));
  useEffect(() => { load(); const i = setInterval(load, 10000); return () => clearInterval(i); }, []);

  const decide = async (id, decision) => {
    setErr("");
    try {
      await api.post("/substitutions/decide", { substitution_id: id, decision });
      load();
    } catch (e) { setErr(e.response?.data?.detail || e.message); }
  };

  if (pending.length === 0) return null;

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 fade-up" data-testid="widget-substitution-inbox">
      <div className="flex items-center gap-2 mb-3">
        <Repeat size={16} className="text-amber-700" />
        <h2 className="text-base font-extrabold text-amber-900">Запрос на замену · {pending.length}</h2>
      </div>
      <div className="space-y-2">
        {pending.map(s => (
          <div key={s.id} className="bg-white border border-amber-300 rounded-lg p-3">
            <div className="text-sm text-slate-900">
              <b>{s.original_name}</b> отсутствует — просим заменить в <b>{s.class_name}</b> ({s.day_of_week} {s.lesson_time}, каб. {s.room})
            </div>
            <div className="text-xs text-slate-500 mt-1 flex items-center gap-2">
              <Clock size={11} /> {new Date(s.created_at).toLocaleString("ru-RU")} · причина: {s.reason}
            </div>
            <div className="mt-3 flex items-center gap-2">
              <button onClick={() => decide(s.id, "accept")} data-testid={`accept-sub-${s.id}`} className="h-8 inline-flex items-center gap-1 rounded-lg bg-emerald-500 px-3 text-xs font-bold text-white hover:bg-emerald-600"><Check size={12} /> Подтвердить</button>
              <button onClick={() => decide(s.id, "reject")} data-testid={`reject-sub-${s.id}`} className="h-8 inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 text-xs font-bold text-slate-700 hover:bg-slate-50"><X size={12} /> Отклонить</button>
            </div>
          </div>
        ))}
      </div>
      {err && <div className="text-xs text-red-600 mt-2">{err}</div>}
    </div>
  );
}
