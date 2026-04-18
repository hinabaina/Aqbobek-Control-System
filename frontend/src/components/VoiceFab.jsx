import React, { useRef, useState } from "react";
import { Mic, Square, Loader2, Sparkles } from "lucide-react";
import api from "@/lib/api";

export default function VoiceFab({ onTasksCreated }) {
  const [state, setState] = useState("idle"); // idle | recording | processing | preview
  const [transcript, setTranscript] = useState("");
  const [tasks, setTasks] = useState([]);
  const [error, setError] = useState("");
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  const start = async () => {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mr = new MediaRecorder(stream);
      mediaRef.current = mr;
      chunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = handleStop;
      mr.start();
      setState("recording");
    } catch (e) {
      setError("Не удалось получить доступ к микрофону");
    }
  };

  const stopRec = () => { if (mediaRef.current) mediaRef.current.stop(); };

  const handleStop = async () => {
    setState("processing");
    try {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      const fd = new FormData();
      fd.append("file", blob, "voice.webm");
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
      const t = await api.post("/ai/voice/transcribe", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setTranscript(t.data.text || "");
      if (!t.data.text) { setState("idle"); setError("Не удалось распознать голос"); return; }
      const p = await api.post("/ai/voice/parse", { text: t.data.text });
      setTasks(p.data.parsed || []);
      setState("preview");
      onTasksCreated?.(p.data.created || []);
    } catch (e) {
      setError("Ошибка обработки: " + (e.response?.data?.detail || e.message));
      setState("idle");
    }
  };

  const close = () => { setState("idle"); setTranscript(""); setTasks([]); setError(""); };

  return (
    <>
      <button
        data-testid="button-voice-fab"
        onClick={state === "recording" ? stopRec : state === "idle" ? start : undefined}
        className={`fixed bottom-8 right-8 h-16 w-16 rounded-full shadow-xl flex items-center justify-center z-50 transition-all ${
          state === "recording" ? "bg-red-500 text-white rec-pulse"
          : state === "processing" ? "bg-slate-200 text-slate-600"
          : "bg-slate-900 text-white hover:scale-105"
        }`}
        title="Голосовая постановка задач"
      >
        {state === "recording" ? <Square size={22} /> : state === "processing" ? <Loader2 className="animate-spin" size={22} /> : <Mic size={22} />}
      </button>

      {(state === "preview" || error) && (
        <div className="fixed bottom-28 right-8 w-96 bg-white border border-slate-200 rounded-2xl shadow-2xl p-5 z-50 fade-up">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={16} className="text-slate-900" />
            <div className="font-extrabold text-slate-900">AI распознал</div>
            <button onClick={close} className="ml-auto text-slate-400 hover:text-slate-900 text-xl leading-none">×</button>
          </div>
          {error && <div className="text-sm text-red-600">{error}</div>}
          {transcript && (
            <div className="text-sm text-slate-600 mb-3 italic border-l-2 border-slate-200 pl-3">«{transcript}»</div>
          )}
          {tasks.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs uppercase font-bold tracking-wider text-slate-500">Созданные задачи</div>
              {tasks.map((t, i) => (
                <div key={i} className="border border-slate-200 rounded-lg p-3">
                  <div className="font-bold text-sm text-slate-900">{t.title}</div>
                  <div className="text-xs text-slate-500 mt-1">{t.description}</div>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-[10px] uppercase tracking-wider font-bold bg-slate-100 text-slate-700 rounded-full px-2 py-0.5">
                      {t.assigned_to_name || "—"}
                    </span>
                    <span className="text-[10px] uppercase tracking-wider font-bold bg-amber-50 text-amber-700 rounded-full px-2 py-0.5">
                      {t.priority}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  );
}
