import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { LogIn } from "lucide-react";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("director@aqbobek.kz");
  const [password, setPassword] = useState("director123");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setLoading(true);
    try {
      const user = await login(email, password);
      nav(user.user_role === "director" ? "/" : "/cabinet", { replace: true });
    } catch (e) {
      setErr(e.response?.data?.detail || "Ошибка входа");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="relative hidden lg:block">
        <img
          src="https://images.unsplash.com/photo-1762088776943-28a9fbadcec4?crop=entropy&cs=srgb&fm=jpg&q=85&w=1600"
          alt=""
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-slate-900/75" />
        <div className="relative z-10 p-12 h-full flex flex-col">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-white text-slate-900 grid place-items-center font-extrabold">А</div>
            <div className="text-white">
              <div className="font-extrabold tracking-tight text-xl">Aqbobek ACS</div>
              <div className="text-[11px] uppercase tracking-widest text-white/60 mt-0.5">AI Control System</div>
            </div>
          </div>
          <div className="mt-auto text-white">
            <h1 className="text-4xl font-extrabold tracking-tight leading-[1.05]">Цифровой завуч для школы Aqbobek</h1>
            <p className="mt-4 text-white/75 text-base leading-relaxed max-w-md">
              Автоматическая обработка WhatsApp/Telegram, умное расписание с лентами, мгновенные замены и
              голосовая постановка задач. Всё в одной панели.
            </p>
            <div className="mt-6 flex gap-2 text-[11px] uppercase tracking-widest font-bold text-white/70">
              <span className="border border-white/20 rounded-full px-3 py-1.5">NLP-парсер чатов</span>
              <span className="border border-white/20 rounded-full px-3 py-1.5">Smart Schedule</span>
              <span className="border border-white/20 rounded-full px-3 py-1.5">RAG Приказы</span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-center p-6 lg:p-12 bg-white">
        <form onSubmit={submit} className="w-full max-w-sm" data-testid="login-form">
          <div className="text-xs uppercase tracking-widest font-bold text-slate-500 mb-2">Вход в систему</div>
          <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Добро пожаловать</h2>
          <p className="text-sm text-slate-500 mt-1.5 mb-8">
            Войдите как директор или учитель. Учителя получают задания в личный кабинет.
          </p>

          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600">Почта</span>
            <input
              data-testid="input-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1.5 flex h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
              required
            />
          </label>

          <label className="block mt-4">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600">Пароль</span>
            <input
              data-testid="input-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1.5 flex h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
              required
            />
          </label>

          {err && <div className="mt-3 text-sm text-red-600 font-semibold" data-testid="login-error">{err}</div>}

          <button
            type="submit"
            disabled={loading}
            data-testid="button-login-submit"
            className="mt-6 inline-flex items-center justify-center gap-2 w-full h-11 rounded-lg bg-slate-900 px-4 text-sm font-bold text-white hover:bg-slate-800 disabled:opacity-60"
          >
            <LogIn size={16} /> {loading ? "Проверка..." : "Войти"}
          </button>

          <div className="mt-6 text-xs text-slate-500 leading-relaxed border-t pt-4">
            <div className="font-bold text-slate-700 mb-1">Тестовые аккаунты</div>
            <div><span className="font-mono">director@aqbobek.kz</span> / <span className="font-mono">director123</span> — директор</div>
            <div><span className="font-mono">teacher&lt;id&gt;@aqbobek.kz</span> / <span className="font-mono">teacher123</span> — учитель</div>
          </div>
        </form>
      </div>
    </div>
  );
}
