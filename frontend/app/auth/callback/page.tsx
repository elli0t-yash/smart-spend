"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function GmailCallbackPage() {
  const [status, setStatus] = useState("Connecting to Gmail…");
  const [error, setError] = useState("");
  const router = useRouter();
  const params = useSearchParams();

  useEffect(() => {
    const code = params.get("code");
    const err = params.get("error");

    if (err || !code) {
      setError(err === "access_denied" ? "Access denied." : "OAuth failed — please try again.");
      return;
    }

    (async () => {
      try {
        // 1. Exchange code for access token
        setStatus("Authenticating…");
        const tokenRes = await fetch("http://localhost:8000/auth/gmail/token", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code }),
        });
        if (!tokenRes.ok) throw new Error((await tokenRes.json()).detail);
        const { access_token } = await tokenRes.json();

        // 2. Fetch + analyze emails
        setStatus("Reading transaction emails…");
        const analyzeRes = await fetch("http://localhost:8000/analyze/gmail", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ access_token }),
        });
        if (!analyzeRes.ok) throw new Error((await analyzeRes.json()).detail);
        const data = await analyzeRes.json();

        sessionStorage.setItem("smart-spend-result", JSON.stringify(data));
        router.replace("/results");
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Something went wrong.");
      }
    })();
  }, [params, router]);

  if (error) {
    return (
      <main
        className="flex-1 flex flex-col items-center justify-center px-4"
        style={{ background: "#0f0f13" }}
      >
        <div
          className="rounded-2xl px-6 py-5 max-w-sm w-full text-center"
          style={{ background: "#2a1a1a", border: "1px solid #4a2020" }}
        >
          <p className="text-sm mb-4" style={{ color: "#f87171" }}>
            {error}
          </p>
          <button
            onClick={() => router.replace("/")}
            className="text-sm underline"
            style={{ color: "#8888aa" }}
          >
            Go back
          </button>
        </div>
      </main>
    );
  }

  return (
    <main
      className="flex-1 flex flex-col items-center justify-center gap-4 px-4"
      style={{ background: "#0f0f13" }}
    >
      <div
        className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin"
        style={{ borderColor: "#7c6af7", borderTopColor: "transparent" }}
      />
      <p className="text-sm" style={{ color: "#8888aa" }}>
        {status}
      </p>
      <p className="text-xs" style={{ color: "#55556a" }}>
        We only read transaction emails. Nothing is stored.
      </p>
    </main>
  );
}
