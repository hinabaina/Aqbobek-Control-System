import React from "react";
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import "@/App.css";
import { AuthProvider, useAuth } from "@/lib/auth";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Incidents from "@/pages/Incidents";
import Tasks from "@/pages/Tasks";
import Employees from "@/pages/Employees";
import Canteen from "@/pages/Canteen";
import Schedule from "@/pages/Schedule";
import Orders from "@/pages/Orders";
import TeacherCabinet from "@/pages/TeacherCabinet";
import Sidebar from "@/components/Sidebar";
import VoiceFab from "@/components/VoiceFab";
import { Toaster } from "sonner";

function Shell() {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen grid place-items-center text-slate-400">Загрузка...</div>;
  if (!user) return <Navigate to="/login" replace />;
  const isDirector = (user.user_role || "").toLowerCase() === "director";
  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar />
      <main className="pl-64">
        <div className="max-w-[1500px] mx-auto p-8 fade-up">
          <Outlet />
        </div>
      </main>
      {isDirector && <VoiceFab />}
    </div>
  );
}

function DirectorOnly({ children }) {
  const { user } = useAuth();
  if ((user?.user_role || "").toLowerCase() !== "director") return <Navigate to="/cabinet" replace />;
  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-right" />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<Shell />}>
            <Route path="/" element={<DirectorOnly><Dashboard /></DirectorOnly>} />
            <Route path="/incidents" element={<DirectorOnly><Incidents /></DirectorOnly>} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/schedule" element={<Schedule />} />
            <Route path="/canteen" element={<DirectorOnly><Canteen /></DirectorOnly>} />
            <Route path="/employees" element={<DirectorOnly><Employees /></DirectorOnly>} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/cabinet" element={<TeacherCabinet />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
