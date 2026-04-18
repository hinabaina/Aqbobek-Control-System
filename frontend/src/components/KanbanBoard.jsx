import React, { useEffect, useState } from "react";
import api from "@/lib/api";

const COLUMNS = [
  { key: "new", label: "Новые", dot: "bg-slate-400" },
  { key: "in_progress", label: "В работе", dot: "bg-amber-500" },
  { key: "done", label: "Выполнено", dot: "bg-emerald-500" },
];

function Card({ item, onMove, employees, onAssign, entity }) {
  const prio = (p) => p === "high" ? "bg-red-50 text-red-700 border-red-200"
    : p === "medium" ? "bg-amber-50 text-amber-700 border-amber-200"
    : "bg-slate-50 text-slate-700 border-slate-200";
  return (
    <div
      draggable
      onDragStart={(e) => e.dataTransfer.setData("id", String(item.id))}
      className="kanban-card bg-white border border-slate-200 rounded-lg p-3.5 cursor-grab active:cursor-grabbing"
      data-testid={`card-${entity}-${item.id}`}
    >
      <div className="flex items-start gap-2 mb-2">
        <span className={`text-[10px] uppercase font-bold tracking-wider rounded-full border px-2 py-0.5 ${prio(item.priority)}`}>{item.priority}</span>
        {item.assignee_name && <span className="text-[10px] uppercase font-bold tracking-wider rounded-full bg-slate-100 text-slate-700 px-2 py-0.5 truncate">{item.assignee_name}</span>}
      </div>
      <div className="text-sm font-bold text-slate-900 leading-snug">{item.title}</div>
      {item.description && item.description !== item.title && (
        <div className="text-[12px] text-slate-600 mt-1 line-clamp-2">{item.description}</div>
      )}
      <div className="mt-3 flex items-center justify-between">
        <div className="text-[10px] text-slate-400">
          {item.created_at ? new Date(item.created_at).toLocaleDateString("ru-RU") : ""}
        </div>
        {entity === "incidents" && onAssign && (
          <select
            value={item.assigned_to || ""}
            onChange={(e) => onAssign(item, e.target.value ? Number(e.target.value) : null)}
            className="text-xs border border-slate-200 rounded px-1.5 py-0.5 bg-white"
          >
            <option value="">— Исполнитель —</option>
            {employees?.map(e => <option key={e.id} value={e.id}>{e.full_name}</option>)}
          </select>
        )}
      </div>
      <div className="mt-2 flex gap-1">
        {COLUMNS.filter(c => c.key !== item.status).map(c => (
          <button
            key={c.key}
            onClick={() => onMove(item, c.key)}
            className="text-[10px] font-bold uppercase tracking-wider text-slate-500 hover:text-slate-900 border border-slate-200 hover:border-slate-400 rounded px-1.5 py-0.5"
          >
            → {c.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function KanbanBoard({ entity = "tasks", allowCreate = true }) {
  const [items, setItems] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", assigned_to: "", priority: "medium" });
  const [filter, setFilter] = useState({ priority: "", assigned_to: "" });

  const load = () => {
    api.get(`/${entity}`).then(r => setItems(r.data));
    api.get("/employees").then(r => setEmployees(r.data));
  };
  useEffect(() => { load(); const i = setInterval(load, 15000); return () => clearInterval(i); }, [entity]);

  const move = async (item, status) => {
    await api.patch(`/${entity}/${item.id}/status`, { status });
    load();
  };
  const assign = async (item, assigned_to) => {
    if (entity !== "incidents") return;
    await api.patch(`/incidents/${item.id}/assign`, { assigned_to });
    load();
  };
  const create = async (e) => {
    e.preventDefault();
    const body = {
      title: form.title,
      description: form.description,
      priority: form.priority,
      assigned_to: form.assigned_to ? Number(form.assigned_to) : null,
    };
    await api.post(`/${entity}`, body);
    setCreating(false);
    setForm({ title: "", description: "", assigned_to: "", priority: "medium" });
    load();
  };

  const filtered = items.filter(i =>
    (!filter.priority || i.priority === filter.priority) &&
    (!filter.assigned_to || String(i.assigned_to) === filter.assigned_to)
  );

  const title = entity === "incidents" ? "Инциденты" : "Задачи";
  const subtitle = entity === "incidents"
    ? "Всё, что сломалось в школе — из чатов и с дашборда"
    : "Поручения директора — текст или голос";

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-widest font-bold text-slate-500">Канбан</div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 mt-1">{title}</h1>
          <p className="text-sm text-slate-500 mt-1">{subtitle}</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={filter.priority}
            onChange={(e) => setFilter(f => ({ ...f, priority: e.target.value }))}
            className="h-10 rounded-lg border border-slate-200 px-3 text-sm bg-white"
          >
            <option value="">Все приоритеты</option>
            <option value="high">Высокий</option>
            <option value="medium">Средний</option>
            <option value="low">Низкий</option>
          </select>
          <select
            value={filter.assigned_to}
            onChange={(e) => setFilter(f => ({ ...f, assigned_to: e.target.value }))}
            className="h-10 rounded-lg border border-slate-200 px-3 text-sm bg-white max-w-xs"
          >
            <option value="">Все исполнители</option>
            {employees.map(e => <option key={e.id} value={e.id}>{e.full_name}</option>)}
          </select>
          {allowCreate && (
            <button
              onClick={() => setCreating(true)}
              data-testid={`button-create-${entity}`}
              className="h-10 inline-flex items-center rounded-lg bg-slate-900 px-4 text-sm font-bold text-white hover:bg-slate-800"
            >+ Создать</button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {COLUMNS.map(col => (
          <div
            key={col.key}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              const id = Number(e.dataTransfer.getData("id"));
              const item = items.find(i => i.id === id);
              if (item && item.status !== col.key) move(item, col.key);
            }}
            className="bg-slate-50 border border-slate-200 rounded-xl p-3 flex flex-col gap-3 min-h-[280px]"
          >
            <div className="flex items-center gap-2 px-1 pt-1">
              <span className={`h-2 w-2 rounded-full ${col.dot}`} />
              <div className="text-xs uppercase font-bold tracking-wider text-slate-700">{col.label}</div>
              <div className="ml-auto text-xs font-bold text-slate-400">
                {filtered.filter(i => i.status === col.key).length}
              </div>
            </div>
            {filtered.filter(i => i.status === col.key).map(it => (
              <Card key={it.id} item={it} onMove={move} employees={employees} onAssign={assign} entity={entity} />
            ))}
          </div>
        ))}
      </div>

      {creating && (
        <div className="fixed inset-0 bg-slate-900/40 z-40 flex items-center justify-center p-4" onClick={() => setCreating(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={create} className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-6">
            <div className="text-xs uppercase tracking-widest font-bold text-slate-500">Новая карточка</div>
            <h3 className="text-xl font-extrabold text-slate-900 mt-1">{entity === "incidents" ? "Новый инцидент" : "Новая задача"}</h3>
            <div className="mt-4 space-y-3">
              <input required placeholder="Заголовок" value={form.title} onChange={(e) => setForm(f => ({ ...f, title: e.target.value }))} className="w-full h-10 rounded-lg border border-slate-300 px-3 text-sm" />
              <textarea placeholder="Описание" rows={3} value={form.description} onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))} className="w-full rounded-lg border border-slate-300 p-3 text-sm" />
              <div className="grid grid-cols-2 gap-2">
                <select value={form.priority} onChange={(e) => setForm(f => ({ ...f, priority: e.target.value }))} className="h-10 rounded-lg border border-slate-300 px-3 text-sm">
                  <option value="low">Низкий</option>
                  <option value="medium">Средний</option>
                  <option value="high">Высокий</option>
                </select>
                <select value={form.assigned_to} onChange={(e) => setForm(f => ({ ...f, assigned_to: e.target.value }))} className="h-10 rounded-lg border border-slate-300 px-3 text-sm">
                  <option value="">Без исполнителя</option>
                  {employees.map(e => <option key={e.id} value={e.id}>{e.full_name}</option>)}
                </select>
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setCreating(false)} className="h-10 rounded-lg border border-slate-200 px-4 text-sm font-bold text-slate-700">Отмена</button>
              <button type="submit" className="h-10 rounded-lg bg-slate-900 px-4 text-sm font-bold text-white hover:bg-slate-800">Создать</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
