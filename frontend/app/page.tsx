"use client";

import { useState, useRef, DragEvent, ChangeEvent } from "react";
import { useRouter } from "next/navigation";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [bank, setBank] = useState("auto");
  const [password, setPassword] = useState("");
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [gmailLoading, setGmailLoading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  function handleFile(f: File | null) {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }
    setError("");
    setFile(f);
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0] ?? null);
  }

  function onChange(e: ChangeEvent<HTMLInputElement>) {
    handleFile(e.target.files?.[0] ?? null);
  }

  async function onConnectGmail() {
    setGmailLoading(true);
    setError("");
    try {
      const res = await fetch("http://localhost:8000/auth/gmail-url");
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Gmail integration not configured.");
      }
      const { url } = await res.json();
      window.location.href = url;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setGmailLoading(false);
    }
  }

  async function onAnalyze() {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("password", password);
      form.append("bank", bank);

      const res = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `Error ${res.status}`);
      }

      const data = await res.json();
      sessionStorage.setItem("smart-spend-result", JSON.stringify(data));
      router.push("/results");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main
      className="flex-1 flex flex-col items-center justify-center px-4 py-16"
      style={{ background: "#0f0f13" }}
    >
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="mb-10 text-center">
          <h1
            className="text-3xl font-bold tracking-tight mb-2"
            style={{ color: "#e8e8f0" }}
          >
            Smart Spend
          </h1>
          <p style={{ color: "#8888aa" }} className="text-sm">
            Upload your bank statement and see where your money actually goes.
          </p>
        </div>

        {/* Drop zone */}
        <div
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className="rounded-2xl border-2 border-dashed cursor-pointer transition-all mb-4 p-10 flex flex-col items-center gap-3"
          style={{
            borderColor: dragging ? "#7c6af7" : "#2e2e3e",
            background: dragging ? "#1a1a3a" : "#1a1a24",
          }}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={onChange}
          />
          <div className="text-4xl">📄</div>
          {file ? (
            <div className="text-center">
              <p className="font-medium" style={{ color: "#a59bff" }}>
                {file.name}
              </p>
              <p className="text-xs mt-1" style={{ color: "#8888aa" }}>
                {(file.size / 1024).toFixed(0)} KB · Click to change
              </p>
            </div>
          ) : (
            <div className="text-center">
              <p className="font-medium" style={{ color: "#e8e8f0" }}>
                Drop your bank statement here
              </p>
              <p className="text-xs mt-1" style={{ color: "#8888aa" }}>
                PDF format · HDFC, SBI, ICICI, Axis, Kotak
              </p>
            </div>
          )}
        </div>

        {/* Bank selector */}
        <div className="mb-4">
          <label
            className="block text-xs font-medium mb-1.5"
            style={{ color: "#8888aa" }}
          >
            Bank
          </label>
          <select
            value={bank}
            onChange={(e) => setBank(e.target.value)}
            className="w-full rounded-xl px-4 py-3 text-sm outline-none transition-colors appearance-none"
            style={{
              background: "#1a1a24",
              border: "1px solid #2e2e3e",
              color: "#e8e8f0",
            }}
            onFocus={(e) => (e.target.style.borderColor = "#7c6af7")}
            onBlur={(e) => (e.target.style.borderColor = "#2e2e3e")}
          >
            <option value="auto">Auto-detect</option>
            <option value="hdfc">HDFC Bank</option>
            <option value="sbi">State Bank of India</option>
            <option value="icici">ICICI Bank</option>
            <option value="axis">Axis Bank</option>
            <option value="kotak">Kotak Mahindra Bank</option>
          </select>
        </div>

        {/* Password */}
        <div className="mb-4">
          <label
            className="block text-xs font-medium mb-1.5"
            style={{ color: "#8888aa" }}
          >
            PDF Password (if protected)
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="e.g. your date of birth"
            className="w-full rounded-xl px-4 py-3 text-sm outline-none transition-colors"
            style={{
              background: "#1a1a24",
              border: "1px solid #2e2e3e",
              color: "#e8e8f0",
            }}
            onFocus={(e) => (e.target.style.borderColor = "#7c6af7")}
            onBlur={(e) => (e.target.style.borderColor = "#2e2e3e")}
          />
        </div>

        {/* Error */}
        {error && (
          <div
            className="mb-4 rounded-xl px-4 py-3 text-sm"
            style={{
              background: "#2a1a1a",
              color: "#f87171",
              border: "1px solid #4a2020",
            }}
          >
            {error}
          </div>
        )}

        {/* CTA */}
        <button
          onClick={onAnalyze}
          disabled={!file || loading}
          className="w-full rounded-xl py-3.5 font-semibold text-sm transition-all"
          style={{
            background: !file || loading ? "#2e2e3e" : "#7c6af7",
            color: !file || loading ? "#8888aa" : "#fff",
            cursor: !file || loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Analyzing…" : "Analyze Statement"}
        </button>

        {/* Divider */}
        <div className="flex items-center gap-3 my-5">
          <div className="flex-1 h-px" style={{ background: "#2e2e3e" }} />
          <span className="text-xs" style={{ color: "#55556a" }}>or</span>
          <div className="flex-1 h-px" style={{ background: "#2e2e3e" }} />
        </div>

        {/* Gmail button */}
        <button
          onClick={onConnectGmail}
          disabled={gmailLoading || loading}
          className="w-full rounded-xl py-3.5 font-semibold text-sm transition-all flex items-center justify-center gap-2"
          style={{
            background: "#1a1a24",
            border: "1px solid #2e2e3e",
            color: gmailLoading || loading ? "#55556a" : "#c8c8e0",
            cursor: gmailLoading || loading ? "not-allowed" : "pointer",
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M22 6c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6zm-2 0-8 5-8-5h16zm0 12H4V8l8 5 8-5v10z" fill="currentColor"/>
          </svg>
          {gmailLoading ? "Redirecting…" : "Connect Gmail"}
        </button>

        <p className="text-xs text-center mt-3" style={{ color: "#55556a" }}>
          Only transaction emails · Read-only · Nothing stored
        </p>

        <p className="text-xs text-center mt-6" style={{ color: "#55556a" }}>
          Your file is processed locally and never stored.
        </p>
      </div>
    </main>
  );
}
