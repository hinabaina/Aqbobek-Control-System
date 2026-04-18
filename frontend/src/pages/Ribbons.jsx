import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Plus, Trash2, Sparkles, AlertCircle, X, Layers, Check } from "lucide-react";

const DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"];
const TIMES = ["08:00", "09:05", "10:10", "11:00", "11:50", "13:05", "14:20", "15:05"];

const emptyGroup = () => ({ group_name: "", subject: "", teacher_id: "", room: "", capacity: 20, level: "", students: "" });

export default function Ribbons() {
  const [ribbons, setRibbons] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    name: "", strategy: "split", parallel: "", day_of_week: "Понедельник", lesson_time: "08:00",
    source_classes: "", groups: [emptyGroup(), emptyGroup()],
  });
  const [validation, setValidation] = useState(null);
  const [err, setErr] = useState("");

  const load = () => {
    api.get("/ribbons").then(r => setRibbons(r.data));
    api.get("/employees").then(r => setEmployees(r.data));
    api.get("/ribbons/strategies").then(r => setStrategies(r.data));
  };
  useEffect(() => { load(); }, []);

  const updateGroup = (i, key, val) => {
    const gs = [...form.groups];
    gs[i] = { ...gs[i], [key]: val };
    setForm({ ...form, groups: gs });
  };

  const toPayload = () => ({
    name: form.name || `Лента ${form.lesson_time}`,
    strategy: form.strategy,
    parallel: form.parallel || null,
    day_of_week: form.day_of_week,
    lesson_time: form.lesson_time,
    source_classes: form.source_classes.split(",").map(s => s.trim()).filter(Boolean),
    groups: form.groups
      .filter(g => g.teacher_id && g.room && g.group_name)
      .map(g => ({
        group_name: g.group_name, subject: g.subject || "—", teacher_id: Number(g.teacher_id),
        room: g.room, capacity: Number(g.capacity) || 20, level: g.level || null,
        students: (g.students || "").split(",").map(s => s.trim()).filter(Boolean),
      })),
  });

  const validate = async () => {
    setErr("");
    try { const { data } = await api.post("/ribbons/validate", toPayload()); setValidation(data); }
    catch (e) { setErr(e.response?.data?.detail || e.message); }
  };

  const save = async () => {
    setErr("");
    try {
      await api.post("/ribbons", toPayload());
      setOpen(false);
      setForm({ name: "", strategy: "split", parallel: "", day_of_week: "Понедельник", lesson_time: "08:00", source_classes: "", groups: [emptyGroup(), emptyGroup()] });
      setValidation(null);
      load();
    } catch (e) {
      const d = e.response?.data?.detail;
      if (d && d.conflicts) { setErr(d.conflicts.join(" · ")); }
      else { setErr(typeof d === "string" ? d : e.message); }
    }
  };

  const del = async (id) => {
    if (!window.confirm("Удалить ленту?")) return;
    await api.delete(`/ribbons/${id}`);
    load();
  };

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-widest font-bold text-slate-500">Ribbon Scheduling</div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 mt-1">Ленты (НИШ / Сингапурская методика)</h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">Одновременное деление параллели классов на уровневые группы. 4 стратегии с валидацией конфликтов в реальном времени.</p>
        </div>
        <button onClick={() => setOpen(true)} data-testid="button-create-ribbon" className="h-10 inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 text-sm font-bold text-white hover:bg-slate-800">
          <Plus size={16} /> Новая лента
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {ribbons.length === 0 && (
          <div className="col-span-full bg-white border border-dashed border-slate-300 rounded-xl p-12 text-center">
            <Layers size={28} className="mx-auto text-slate-400" />
            <div className="text-sm text-slate-500 mt-3 italic">Пока нет лент. Создайте первую — например, английский по уровням для 7 параллели.</div>
          </div>
        )}
        {ribbons.map(r => (
          <div key={r.id} className="bg-white border border-slate-200 rounded-xl p-4 fade-up" data-testid={`card-ribbon-${r.id}`}>
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-widest font-bold text-slate-500">{r.strategy} · {r.day_of_week} {r.lesson_time}</div>
                <div className="text-base font-extrabold text-slate-900 truncate">{r.name}</div>
                <div className="text-xs text-slate-500 mt-0.5 truncate">классы: {(() => {
                  try { return JSON.parse(r.source_classes || "[]").join(" + "); } catch { return r.source_classes; }
                })()}</div>
              </div>
              <button onClick={() => del(r.id)} className="text-slate-400 hover:text-red-600" title="Удалить"><Trash2 size={15} /></button>
            </div>
            <div className="mt-3 space-y-1.5">
              {(r.groups || []).map(g => (
                <div key={g.id} className="flex items-center gap-2 text-xs border border-slate-100 rounded-lg p-2">
                  <span className="font-bold bg-slate-900 text-white rounded px-1.5 py-0.5">{g.group_name}</span>
                  <span className="text-slate-700 truncate flex-1">{g.subject} · {g.teacher_name} · каб.{g.room}</span>
                  <span className="text-slate-400">{g.students?.length || 0}/{g.capacity}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {open && (
        <div className="fixed inset-0 bg-slate-900/40 z-40 flex items-center justify-center p-4" onClick={() => setOpen(false)}>
          <div onClick={(e) => e.stopPropagation()} className="w-full max-w-3xl bg-white rounded-2xl shadow-2xl p-6 max-h-[92vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-extrabold text-slate-900">Создать ленту</h3>
              <button onClick={() => setOpen(false)}><X size={20} className="text-slate-400 hover:text-slate-900" /></button>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <label className="col-span-2 text-xs font-bold uppercase tracking-wider text-slate-500">Название
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Напр. Англ.язык по уровням 7 параллель" className="mt-1 w-full h-10 rounded-lg border border-slate-300 px-3 text-sm font-normal" />
              </label>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Стратегия
                <select value={form.strategy} onChange={e => setForm(f => ({ ...f, strategy: e.target.value }))} className="mt-1 w-full h-10 rounded-lg border border-slate-300 px-3 text-sm font-normal">
                  {strategies.map(s => <option key={s.key} value={s.key}>{s.title}</option>)}
                </select>
              </label>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Параллель
                <input value={form.parallel} onChange={e => setForm(f => ({ ...f, parallel: e.target.value }))} placeholder="7" className="mt-1 w-full h-10 rounded-lg border border-slate-300 px-3 text-sm font-normal" />
              </label>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">День
                <select value={form.day_of_week} onChange={e => setForm(f => ({ ...f, day_of_week: e.target.value }))} className="mt-1 w-full h-10 rounded-lg border border-slate-300 px-3 text-sm font-normal">
                  {DAYS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </label>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Время
                <select value={form.lesson_time} onChange={e => setForm(f => ({ ...f, lesson_time: e.target.value }))} className="mt-1 w-full h-10 rounded-lg border border-slate-300 px-3 text-sm font-normal">
                  {TIMES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </label>
              <label className="col-span-2 text-xs font-bold uppercase tracking-wider text-slate-500">Исходные классы (через запятую)
                <input value={form.source_classes} onChange={e => setForm(f => ({ ...f, source_classes: e.target.value }))} placeholder="7А, 7Б, 7В" className="mt-1 w-full h-10 rounded-lg border border-slate-300 px-3 text-sm font-normal" />
              </label>
            </div>

            <div className="mt-5">
              <div className="flex items-center justify-between">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Группы</div>
                <button onClick={() => setForm(f => ({ ...f, groups: [...f.groups, emptyGroup()] }))} className="text-xs font-bold text-slate-600 hover:text-slate-900 inline-flex items-center gap-1">
                  <Plus size={12} /> Добавить группу
                </button>
              </div>
              <div className="mt-2 space-y-2">
                {form.groups.map((g, i) => (
                  <div key={i} className="grid grid-cols-12 gap-2 border border-slate-200 rounded-lg p-2">
                    <input value={g.group_name} onChange={e => updateGroup(i, "group_name", e.target.value)} placeholder="Beg" className="col-span-2 h-9 rounded border border-slate-200 px-2 text-sm" />
                    <input value={g.subject} onChange={e => updateGroup(i, "subject", e.target.value)} placeholder="Англ.язык" className="col-span-3 h-9 rounded border border-slate-200 px-2 text-sm" />
                    <select value={g.teacher_id} onChange={e => updateGroup(i, "teacher_id", e.target.value)} className="col-span-3 h-9 rounded border border-slate-200 px-2 text-sm">
                      <option value="">Учитель</option>
                      {employees.map(e => <option key={e.id} value={e.id}>{e.full_name}</option>)}
                    </select>
                    <input value={g.room} onChange={e => updateGroup(i, "room", e.target.value)} placeholder="101" className="col-span-1 h-9 rounded border border-slate-200 px-2 text-sm" />
                    <input type="number" value={g.capacity} onChange={e => updateGroup(i, "capacity", e.target.value)} placeholder="20" className="col-span-1 h-9 rounded border border-slate-200 px-2 text-sm" />
                    <input value={g.students} onChange={e => updateGroup(i, "students", e.target.value)} placeholder="ученики..." className="col-span-2 h-9 rounded border border-slate-200 px-2 text-sm" />
                  </div>
                ))}
              </div>
            </div>

            {validation && (
              <div className={`mt-4 rounded-lg border p-3 ${validation.valid ? "bg-emerald-50 border-emerald-200" : "bg-red-50 border-red-200"}`}>
                <div className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5" style={{ color: validation.valid ? "#065f46" : "#991b1b" }}>
                  {validation.valid ? <Check size={12} /> : <AlertCircle size={12} />}
                  {validation.valid ? "Конфликтов нет" : "Конфликты"}
                </div>
                <div className="text-sm mt-1 text-slate-700">{validation.describe}</div>
                {!validation.valid && (
                  <ul className="list-disc ml-4 mt-2 text-xs text-red-700 space-y-0.5">
                    {validation.conflicts.map((c, i) => <li key={i}>{c}</li>)}
                  </ul>
                )}
              </div>
            )}
            {err && <div className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-2">{err}</div>}

            <div className="mt-5 flex items-center justify-end gap-2">
              <button onClick={validate} className="h-10 rounded-lg border border-slate-200 px-4 text-sm font-bold text-slate-900 inline-flex items-center gap-1.5">
                <Sparkles size={14} /> Проверить конфликты
              </button>
              <button onClick={save} className="h-10 rounded-lg bg-slate-900 px-5 text-sm font-bold text-white">Сохранить</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
