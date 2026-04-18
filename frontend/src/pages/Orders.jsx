import React, { useState } from "react";
import api from "@/lib/api";
import { Loader2, Sparkles, Copy, Check } from "lucide-react";

export default function Orders() {
  const [mode, setMode] = useState("simplify"); // simplify | generate
  const [text, setText] = useState(
    "Приказ МЗ РК №76 «О санитарно-эпидемиологических требованиях к объектам образования» устанавливает требования к проведению влажной уборки, режиму проветривания помещений..."
  );
  const [out, setOut] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const run = async () => {
    setLoading(true); setOut("");
    try {
      const { data } = await api.post("/ai/orders/simplify", { text, mode });
      setOut(data.result);
    } catch (e) {
      setOut("Ошибка: " + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  const copy = async () => {
    await navigator.clipboard.writeText(out);
    setCopied(true); setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="space-y-5">
      <div>
        <div className="text-xs uppercase tracking-widest font-bold text-slate-500">RAG AI</div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 mt-1">Приказы и документы</h1>
        <p className="text-sm text-slate-500 mt-1">Упрощение сложных приказов для учителей · генерация официальных документов</p>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-2 inline-flex">
        <button onClick={() => setMode("simplify")} className={`h-9 px-4 rounded-lg text-sm font-bold ${mode === "simplify" ? "bg-slate-900 text-white" : "text-slate-600"}`}>Упростить для учителей</button>
        <button onClick={() => setMode("generate")} className={`h-9 px-4 rounded-lg text-sm font-bold ${mode === "generate" ? "bg-slate-900 text-white" : "text-slate-600"}`}>Сгенерировать приказ</button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="text-xs uppercase tracking-widest font-bold text-slate-500">
            {mode === "simplify" ? "Исходный текст (сложный приказ)" : "Описание задачи для приказа"}
          </div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={16}
            className="mt-3 w-full rounded-lg border border-slate-300 p-3 text-sm font-mono leading-relaxed"
            data-testid="input-order-text"
          />
          <button
            onClick={run}
            disabled={loading || !text.trim()}
            data-testid="button-run-rag"
            className="mt-3 inline-flex items-center gap-2 h-10 rounded-lg bg-slate-900 px-5 text-sm font-bold text-white hover:bg-slate-800 disabled:opacity-60"
          >
            {loading ? <Loader2 className="animate-spin" size={14} /> : <Sparkles size={14} />}
            {loading ? "Обработка..." : (mode === "simplify" ? "Упростить" : "Сгенерировать")}
          </button>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div className="text-xs uppercase tracking-widest font-bold text-slate-500">
              {mode === "simplify" ? "Чек-лист для учителей" : "Готовый приказ"}
            </div>
            {out && (
              <button onClick={copy} className="text-xs font-bold text-slate-500 hover:text-slate-900 inline-flex items-center gap-1">
                {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? "Скопировано" : "Копировать"}
              </button>
            )}
          </div>
          <div className="mt-3 min-h-[360px] rounded-lg border border-slate-200 bg-slate-50/50 p-4 whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
            {loading && <div className="text-slate-400 italic">AI пишет...</div>}
            {!loading && !out && <div className="text-slate-400 italic">Результат появится здесь</div>}
            {out}
          </div>
        </div>
      </div>
    </div>
  );
}
