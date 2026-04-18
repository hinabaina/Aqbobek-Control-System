import React, { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { Loader2, Sparkles, Trash2, Plus, Users, Repeat, AlertCircle, Eraser, UserX } from "lucide-react";

const DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"];
const TIMES = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00"];
const PALETTE = ["#0f172a", "#1e40af", "#065f46", "#854d0e", "#7c2d12", "#4338ca", "#9d174d", "#166534", "#9a3412", "#5b21b6"];

function colorForTeacher(id) { return PALETTE[id % PALETTE.length]; }

export default function Schedule() {
  const [rows, setRows] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [filter, setFilter] = useState({ mode: "class", value: "" }); // mode: teacher|class|room
  const [creating, setCreating] = useState(null); // {day, time}
  const [form, setForm] = useState({ teacher_id: "", class_name: "", room: "" });
  const [genOpen, setGenOpen] = useState(false);
  const [subOpen, setSubOpen] = useState(false);
  const [subState, setSubState] = useState({ teacher_id: "", loading: false, result: null });
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [genResult, setGenResult] = useState(null);
  const [genForm, setGenForm] = useState({
    classes: "3А:Алгебра=4,Английский=3,История=2\n3Б:Алгебра=4,Английский=3,Физика=2",
    rooms: "101,102,103,Лингафон,Спортзал",
    replace: false,
  });

  const load = () => {
    api.get("/schedule").then(r => setRows(r.data));
    api.get("/employees").then(r => setEmployees(r.data));
  };
  useEffect(() => { load(); }, []);

  const classes = useMemo(() => [...new Set(rows.map(r => r.class_name))].sort(), [rows]);
  const rooms = useMemo(() => [...new Set(rows.map(r => r.room))].sort(), [rows]);

  const filtered = rows.filter(r => {
    if (!filter.value) return true;
    if (filter.mode === "teacher") return String(r.teacher_id) === filter.value;
    if (filter.mode === "class") return r.class_name === filter.value;
    return r.room === filter.value;
  });

  const cellMap = useMemo(() => {
    const m = {};
    for (const r of filtered) {
      const key = `${r.day_of_week}|${r.lesson_time}`;
      (m[key] = m[key] || []).push(r);
    }
    return m;
  }, [filtered]);

  const submitCell = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/schedule", {
        teacher_id: Number(form.teacher_id),
        class_name: form.class_name,
        day_of_week: creating.day,
        lesson_time: creating.time,
        room: form.room,
      });
      setCreating(null);
      setForm({ teacher_id: "", class_name: "", room: "" });
      load();
    } catch (e) {
      setError(e.response?.data?.detail || "Ошибка");
    }
  };

  const del = async (id) => {
    if (!window.confirm("Удалить урок?")) return;
    await api.delete(`/schedule/${id}`);
    load();
  };

  const requestSubstitute = async (scheduleId) => {
    if (!window.confirm("Запросить замену для этого урока? AI подберёт учителя и отправит запрос.")) return;
    try {
      const { data } = await api.post("/substitutions/request", { schedule_id: scheduleId, reason: "Болезнь" });
      if (data.candidate) {
        alert(`Запрос отправлен учителю: ${data.candidate.full_name}. Он должен подтвердить в своём кабинете.`);
      } else {
        alert("Свободных кандидатов нет. Смотрите журнал для ручного решения.");
      }
    } catch (e) { setError(e.response?.data?.detail || "Ошибка"); }
  };

  const clearBulk = async (scope, day = null) => {
    const msg = scope === "day" ? `Удалить всё расписание на ${day}?` : "Удалить ВСЁ расписание и все ленты?";
    if (!window.confirm(msg)) return;
    const { data } = await api.post("/admin/schedule/clear", { scope, day });
    alert(`Удалено: ${data.deleted} слотов`);
    load();
  };

  const runGenerate = async () => {
    setGenerating(true); setGenResult(null);
    try {
      const classes = genForm.classes.split("\n").filter(Boolean).map(line => {
        const [name, rest] = line.split(":");
        const subjects = (rest || "").split(",").filter(Boolean).map(s => {
          const [subject, hours] = s.split("=");
          return { subject: subject.trim(), hours: Number(hours) || 1 };
        });
        return { class_name: name.trim(), subjects };
      });
      const rooms = genForm.rooms.split(",").map(s => s.trim()).filter(Boolean);
      const { data } = await api.post("/ai/schedule/generate", { classes, rooms, replace: genForm.replace });
      setGenResult(data);
      if (genForm.replace) load();
    } catch (e) {
      setError(e.response?.data?.detail || "Ошибка генератора");
    } finally {
      setGenerating(false);
    }
  };

  const runSubstitute = async () => {
    if (!subState.teacher_id) return;
    setSubState(s => ({ ...s, loading: true, result: null }));
    try {
      const { data } = await api.post("/ai/substitute", {
        teacher_id: Number(subState.teacher_id),
        date: new Date().toISOString().slice(0, 10),
        reason: "Болезнь",
      });
      setSubState(s => ({ ...s, loading: false, result: data }));
    } catch (e) {
      setSubState(s => ({ ...s, loading: false }));
      setError(e.response?.data?.detail || "Ошибка");
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest font-bold text-slate-500">Расписание</div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 mt-1">Сетка уроков</h1>
          <p className="text-sm text-slate-500 mt-1">Drag-and-Drop, конфликты, AI-генератор и замены</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select value={filter.mode} onChange={(e) => setFilter({ mode: e.target.value, value: "" })} className="h-10 rounded-lg border border-slate-200 px-3 text-sm bg-white">
            <option value="class">По классу</option>
            <option value="teacher">По учителю</option>
            <option value="room">По кабинету</option>
          </select>
          <select value={filter.value} onChange={(e) => setFilter(f => ({ ...f, value: e.target.value }))} className="h-10 rounded-lg border border-slate-200 px-3 text-sm bg-white min-w-[180px]">
            <option value="">Все</option>
            {filter.mode === "class" && classes.map(c => <option key={c} value={c}>{c}</option>)}
            {filter.mode === "teacher" && employees.filter(e => e.role === "Учитель").map(t => <option key={t.id} value={t.id}>{t.full_name}</option>)}
            {filter.mode === "room" && rooms.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <button onClick={() => setSubOpen(true)} data-testid="button-open-substitute" className="h-10 inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 text-sm font-bold text-slate-900 hover:bg-slate-50">
            <Repeat size={14} /> Учитель заболел
          </button>
          <button onClick={() => clearBulk("week")} data-testid="button-clear-week" className="h-10 inline-flex items-center gap-2 rounded-lg border border-red-200 text-red-600 px-3 text-xs font-bold hover:bg-red-50">
            <Eraser size={13} /> Очистить неделю
          </button>
          <button onClick={() => setGenOpen(true)} data-testid="button-open-generate" className="h-10 inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 text-sm font-bold text-white hover:bg-slate-800">
            <Sparkles size={14} /> AI-генератор
          </button>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="py-3 px-3 text-left text-xs uppercase font-bold tracking-wider text-slate-500 w-20">Время</th>
                {DAYS.map(d => (
                  <th key={d} className="py-3 px-3 text-left text-xs uppercase font-bold tracking-wider text-slate-500 min-w-[180px]">{d}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {TIMES.map(t => (
                <tr key={t} className="border-b border-slate-100 align-top">
                  <td className="py-3 px-3 font-mono text-xs text-slate-400">{t}</td>
                  {DAYS.map(d => {
                    const items = cellMap[`${d}|${t}`] || [];
                    return (
                      <td key={d} className="py-2 px-2 min-w-[180px]">
                        <div className="space-y-1.5">
                          {items.map(it => (
                            <div
                              key={it.id}
                              className="rounded-lg p-2 text-white text-xs shadow-sm fade-up group relative"
                              style={{ background: colorForTeacher(it.teacher_id || 0) }}
                            >
                              <div className="font-bold">{it.class_name}</div>
                              <div className="opacity-90 truncate">{it.teacher_name}</div>
                              <div className="opacity-70 text-[10px] mt-0.5">каб. {it.room}</div>
                              <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 flex items-center gap-0.5">
                                <button onClick={() => requestSubstitute(it.id)} className="text-white/80 hover:text-white" title="Запросить замену">
                                  <UserX size={12} />
                                </button>
                                <button onClick={() => del(it.id)} className="text-white/80 hover:text-white" title="Удалить">
                                  <Trash2 size={12} />
                                </button>
                              </div>
                            </div>
                          ))}
                          <button
                            onClick={() => { setCreating({ day: d, time: t }); setError(""); }}
                            className="w-full h-6 rounded border border-dashed border-slate-200 text-slate-400 hover:text-slate-900 hover:border-slate-400 text-xs"
                          >+</button>
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create cell modal */}
      {creating && (
        <div className="fixed inset-0 bg-slate-900/40 z-40 flex items-center justify-center p-4" onClick={() => setCreating(null)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={submitCell} className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-6">
            <h3 className="text-xl font-extrabold text-slate-900">Добавить урок</h3>
            <p className="text-xs text-slate-500 mt-1">{creating.day} · {creating.time}</p>
            <div className="mt-4 space-y-3">
              <select required value={form.teacher_id} onChange={(e) => setForm(f => ({ ...f, teacher_id: e.target.value }))} className="w-full h-10 rounded-lg border border-slate-300 px-3 text-sm">
                <option value="">Учитель...</option>
                {employees.map(e => <option key={e.id} value={e.id}>{e.full_name} · {e.subject || e.role}</option>)}
              </select>
              <input required placeholder="Класс (3А)" value={form.class_name} onChange={(e) => setForm(f => ({ ...f, class_name: e.target.value }))} className="w-full h-10 rounded-lg border border-slate-300 px-3 text-sm" />
              <input required placeholder="Кабинет (101)" value={form.room} onChange={(e) => setForm(f => ({ ...f, room: e.target.value }))} className="w-full h-10 rounded-lg border border-slate-300 px-3 text-sm" />
              {error && <div className="text-sm text-red-600 flex items-center gap-1.5"><AlertCircle size={14} /> {error}</div>}
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setCreating(null)} className="h-10 rounded-lg border border-slate-200 px-4 text-sm font-bold text-slate-700">Отмена</button>
              <button type="submit" className="h-10 rounded-lg bg-slate-900 px-4 text-sm font-bold text-white">Сохранить</button>
            </div>
          </form>
        </div>
      )}

      {/* Generator modal */}
      {genOpen && (
        <div className="fixed inset-0 bg-slate-900/40 z-40 flex items-center justify-center p-4" onClick={() => setGenOpen(false)}>
          <div onClick={(e) => e.stopPropagation()} className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl p-6">
            <div className="flex items-center gap-2">
              <Sparkles size={18} /> <h3 className="text-xl font-extrabold text-slate-900">AI-Генератор расписания</h3>
            </div>
            <p className="text-xs text-slate-500 mt-1">Алгоритм подбирает учителей и кабинеты без конфликтов</p>
            <div className="mt-4 space-y-3">
              <label className="block">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-600">Классы и предметы (формат: <span className="font-mono">Класс:Предмет=часы,Предмет=часы</span>)</span>
                <textarea rows={5} value={genForm.classes} onChange={(e) => setGenForm(g => ({ ...g, classes: e.target.value }))} className="mt-1 w-full rounded-lg border border-slate-300 p-3 text-sm font-mono" />
              </label>
              <label className="block">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-600">Кабинеты (через запятую)</span>
                <input value={genForm.rooms} onChange={(e) => setGenForm(g => ({ ...g, rooms: e.target.value }))} className="mt-1 w-full h-10 rounded-lg border border-slate-300 px-3 text-sm font-mono" />
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={genForm.replace} onChange={(e) => setGenForm(g => ({ ...g, replace: e.target.checked }))} /> Заменить текущее расписание
              </label>
            </div>
            <div className="mt-4 flex items-center justify-end gap-2">
              <button onClick={() => setGenOpen(false)} className="h-10 rounded-lg border border-slate-200 px-4 text-sm font-bold text-slate-700">Закрыть</button>
              <button onClick={runGenerate} disabled={generating} data-testid="button-run-generate" className="h-10 inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 text-sm font-bold text-white hover:bg-slate-800 disabled:opacity-60">
                {generating ? <Loader2 className="animate-spin" size={14} /> : <Sparkles size={14} />}
                {generating ? "Генерация..." : "Сгенерировать"}
              </button>
            </div>
            {genResult && (
              <div className="mt-5 border-t pt-4">
                <div className="text-sm font-bold text-slate-900">Создано слотов: {genResult.schedule?.length}</div>
                {genResult.conflicts?.length > 0 && (
                  <div className="mt-2 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-3">
                    <div className="font-bold mb-1">Внимание — нерешённые ограничения:</div>
                    <ul className="list-disc ml-4 space-y-0.5">{genResult.conflicts.map((c, i) => <li key={i}>{c}</li>)}</ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Substitute modal */}
      {subOpen && (
        <div className="fixed inset-0 bg-slate-900/40 z-40 flex items-center justify-center p-4" onClick={() => { setSubOpen(false); setSubState({ teacher_id: "", loading: false, result: null }); }}>
          <div onClick={(e) => e.stopPropagation()} className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl p-6 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center gap-2">
              <Repeat size={18} /> <h3 className="text-xl font-extrabold text-slate-900">Учитель заболел — поиск замены</h3>
            </div>
            <p className="text-xs text-slate-500 mt-1">AI подберёт наиболее подходящего свободного учителя</p>
            <div className="mt-4 flex gap-2">
              <select value={subState.teacher_id} onChange={(e) => setSubState(s => ({ ...s, teacher_id: e.target.value }))} className="flex-1 h-10 rounded-lg border border-slate-300 px-3 text-sm">
                <option value="">Выберите отсутствующего учителя</option>
                {employees.filter(e => e.role === "Учитель").map(t => <option key={t.id} value={t.id}>{t.full_name} · {t.subject}</option>)}
              </select>
              <button onClick={runSubstitute} disabled={!subState.teacher_id || subState.loading} data-testid="button-run-substitute" className="h-10 inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 text-sm font-bold text-white disabled:opacity-60">
                {subState.loading ? <Loader2 className="animate-spin" size={14} /> : "Найти замену"}
              </button>
            </div>

            {subState.loading && (
              <div className="mt-5 space-y-2 animate-pulse">
                <div className="h-10 bg-slate-100 rounded" />
                <div className="h-10 bg-slate-100 rounded" />
                <div className="h-10 bg-slate-100 rounded" />
              </div>
            )}

            {subState.result && (
              <div className="mt-5 space-y-3">
                <div className="text-xs uppercase tracking-widest font-bold text-slate-500">Рекомендации по заменам</div>
                {subState.result.suggestions.length === 0 && (
                  <div className="text-sm text-slate-500 italic">У этого учителя нет уроков в расписании.</div>
                )}
                {subState.result.suggestions.map((s, i) => (
                  <div key={i} className="border border-slate-200 rounded-lg p-3">
                    <div className="flex items-center justify-between">
                      <div className="font-bold text-slate-900 text-sm">{s.lesson.class_name} · {s.lesson.day_of_week} {s.lesson.lesson_time} · каб. {s.lesson.room}</div>
                    </div>
                    {s.picked ? (
                      <div className="mt-2 text-sm bg-emerald-50 text-emerald-900 border border-emerald-200 rounded-lg px-3 py-2">
                        <b>{s.picked.full_name}</b> · {s.picked.subject} · сегодня уроков: {s.picked.load_today}
                        {s.picked.subject_match && <span className="ml-2 text-[10px] uppercase font-bold tracking-wider text-emerald-700">Совпадение предмета</span>}
                      </div>
                    ) : (
                      <div className="mt-2 text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">Свободных кандидатов нет — требуется ручное решение</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
