import React from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import {
  LayoutDashboard, AlertOctagon, ListTodo, Users, UtensilsCrossed,
  CalendarRange, FileText, LogOut, Sparkles, GraduationCap
} from "lucide-react";

const directorNav = [
  { to: "/", label: "Дашборд", icon: LayoutDashboard, end: true },
  { to: "/incidents", label: "Инциденты", icon: AlertOctagon },
  { to: "/tasks", label: "Задачи", icon: ListTodo },
  { to: "/schedule", label: "Расписание", icon: CalendarRange },
  { to: "/canteen", label: "Столовая", icon: UtensilsCrossed },
  { to: "/employees", label: "Сотрудники", icon: Users },
  { to: "/orders", label: "Приказы AI", icon: FileText },
];

const teacherNav = [
  { to: "/cabinet", label: "Мой кабинет", icon: GraduationCap, end: true },
  { to: "/tasks", label: "Мои задачи", icon: ListTodo },
  { to: "/schedule", label: "Расписание", icon: CalendarRange },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const isDirector = (user?.user_role || "").toLowerCase() === "director";
  const nav = isDirector ? directorNav : teacherNav;

  return (
    <aside className="w-64 border-r border-slate-200 bg-white h-screen fixed top-0 left-0 flex flex-col z-20">
      <div className="px-6 pt-6 pb-4 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-lg bg-slate-900 text-white grid place-items-center font-extrabold">А</div>
          <div>
            <div className="font-extrabold tracking-tight text-slate-900 leading-none">Aqbobek ACS</div>
            <div className="text-[11px] uppercase tracking-widest text-slate-500 mt-1">AI-Завуч</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {nav.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            data-testid={`link-${label.toLowerCase().replace(/\s+/g,"-")}`}
            className={({ isActive }) =>
              `sidebar-link flex items-center gap-3 px-4 py-2.5 text-sm rounded-lg font-semibold transition-colors ${
                isActive ? "active bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`
            }
          >
            <Icon size={17} strokeWidth={2.2} /> {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-100 p-4">
        <div className="text-xs text-slate-500 uppercase tracking-wider font-bold mb-2">Аккаунт</div>
        <div className="flex items-center gap-2.5 mb-3">
          <div className="h-9 w-9 rounded-full bg-slate-100 grid place-items-center font-bold text-slate-700">
            {(user?.full_name || "?").charAt(0)}
          </div>
          <div className="min-w-0">
            <div className="text-sm font-bold text-slate-900 truncate">{user?.full_name}</div>
            <div className="text-[11px] text-slate-500 truncate">{user?.role}</div>
          </div>
        </div>
        <button
          onClick={logout}
          data-testid="button-logout"
          className="w-full inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50"
        >
          <LogOut size={14} /> Выйти
        </button>
      </div>
    </aside>
  );
}
