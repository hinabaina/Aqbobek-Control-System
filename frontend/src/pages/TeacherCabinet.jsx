import React, { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CalendarRange, ListTodo, MessageCircle, Check } from "lucide-react";
import SubstitutionInbox from "@/components/SubstitutionInbox";

const DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"];
const TIMES = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00"];

export default function TeacherCabinet() {
  const { user } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [schedule, setSchedule] = useState([]);

  const load = () => {
    api.get("/tasks?mine=true").then(r => setTasks(r.data));
    api.get(`/schedule?teacher_id=${user.id}`).then(r => setSchedule(r.data));
  };
  useEffect(() => { if (user) load(); const i = setInterval(load, 15000); return () => clearInterval(i); }, [user?.id]);

  const scheduleMap = useMemo(() => {
    const m = {};
    for (const s of schedule) m[`${s.day_of_week}|${s.lesson_time}`] = s;
    return m;
  }, [schedule]);

  const mark = async (id, status) => {
    await api.patch(`/tasks/${id}/status`, { status });
    load();
  };

  const open = tasks.filter(t => t.status !== "done");
  const done = tasks.filter(t => t.status === "done");

  return (
    <div className="space-y-5">
      <div>
        <div className="text-xs uppercase tracking-widest font-bold text-slate-500">Личный кабинет</div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 mt-1">Здравствуйте, {user?.full_name?.split(" ")[0]}</h1>
        <p className="text-sm text-slate-500 mt-1">Ваши задачи и расписание. Задания приходят от директора — здесь и в Telegram.</p>
      </div>

      <SubstitutionInbox />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <div className="xl:col-span-2 bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center gap-2">
            <CalendarRange size={16} className="text-slate-500" />
            <h2 className="text-lg font-extrabold text-slate-900">Моё расписание</h2>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="text-left font-bold text-slate-500 text-xs uppercase tracking-wider pb-2 w-16">Время</th>
                  {DAYS.map(d => <th key={d} className="text-left font-bold text-slate-500 text-xs uppercase tracking-wider pb-2 px-2">{d}</th>)}
                </tr>
              </thead>
              <tbody>
                {TIMES.map(t => (
                  <tr key={t} className="border-b border-slate-100">
                    <td className="py-2 font-mono text-xs text-slate-400">{t}</td>
                    {DAYS.map(d => {
                      const s = scheduleMap[`${d}|${t}`];
                      return (
                        <td key={d} className="py-2 px-1">
                          {s ? (
                            <div className="bg-slate-900 text-white rounded-lg px-2 py-1.5 text-xs">
                              <div className="font-bold">{s.class_name}</div>
                              <div className="text-[10px] opacity-75">каб. {s.room}</div>
                            </div>
                          ) : <div className="h-10" />}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {schedule.length === 0 && (
            <div className="mt-6 text-sm text-slate-500 italic text-center py-8">
              Ваше расписание пока пустое. Попросите директора сгенерировать его через AI-Генератор.
            </div>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center gap-2">
            <ListTodo size={16} className="text-slate-500" />
            <h2 className="text-lg font-extrabold text-slate-900">Мои задачи</h2>
            <span className="ml-auto text-xs font-bold text-slate-400">{open.length} открытых</span>
          </div>
          <div className="mt-4 space-y-2">
            {open.length === 0 && <div className="text-sm text-slate-500 italic">Пока задач нет 🎉</div>}
            {open.map(t => (
              <div key={t.id} className="border border-slate-200 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <span className={`h-1.5 w-1.5 rounded-full mt-2 ${t.priority === "high" ? "bg-red-500" : t.priority === "medium" ? "bg-amber-500" : "bg-slate-400"}`} />
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-sm text-slate-900">{t.title}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{t.description}</div>
                    <div className="text-[10px] text-slate-400 mt-1 uppercase tracking-wider font-bold">от {t.creator_name || "директора"} · {new Date(t.created_at).toLocaleDateString("ru-RU")}</div>
                  </div>
                </div>
                <div className="mt-3 flex gap-1">
                  {t.status === "new" && (
                    <button onClick={() => mark(t.id, "in_progress")} className="text-[10px] font-bold uppercase tracking-wider border border-slate-200 rounded px-2 py-1 hover:bg-slate-50">Взять в работу</button>
                  )}
                  <button onClick={() => mark(t.id, "done")} className="text-[10px] font-bold uppercase tracking-wider rounded px-2 py-1 bg-emerald-500 text-white hover:bg-emerald-600 inline-flex items-center gap-1">
                    <Check size={12} /> Выполнено
                  </button>
                </div>
              </div>
            ))}
          </div>
          {done.length > 0 && (
            <div className="mt-5 pt-4 border-t border-slate-100">
              <div className="text-[11px] uppercase tracking-widest font-bold text-slate-400 mb-2">Выполненные · {done.length}</div>
              {done.slice(0,3).map(t => (
                <div key={t.id} className="text-xs text-slate-500 flex items-center gap-2 py-1">
                  <Check size={12} className="text-emerald-500" /> <span className="line-through truncate">{t.title}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
