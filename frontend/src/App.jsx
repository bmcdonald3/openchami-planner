import React, { useState } from "react";
import axios from "axios";

export default function App() {
  const [text, setText] = useState("");
  const [session, setSession] = useState(null);
  const [question, setQuestion] = useState(null);
  const [answer, setAnswer] = useState("");
  const [completion, setCompletion] = useState(0);

  async function analyze() {
    const resp = await axios.post("/analyze", text, {
      headers: { "Content-Type": "text/plain" },
    });
    setSession(resp.data.session_id);
    setQuestion(resp.data.next_question);
  }

  async function submitAnswer() {
    if (!session || !question) return;
    const resp = await axios.post("/answer", {
      session_id: session,
      key: question,
      value: answer,
    });
    setQuestion(resp.data.next_question);
    setCompletion(resp.data.completion || 0);
    setAnswer("");
  }

  async function doExport() {
    if (!session) return;
    const resp = await axios.get("/export", {
      responseType: "blob",
      params: { session_id: session },
    });
    // download blob
    const url = window.URL.createObjectURL(new Blob([resp.data]));
    const a = document.createElement("a");
    a.href = url;
    a.download = `apis_${session}.zip`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  return (
    <div style={{ padding: 20 }}>
      <h3>Analyze RFD</h3>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={8} cols={60} />
      <div>
        <button onClick={analyze}>Analyze</button>
      </div>

      {question && (
        <div style={{ marginTop: 20 }}>
          <h4>{question}</h4>
          <input value={answer} onChange={(e) => setAnswer(e.target.value)} />
          <button onClick={submitAnswer}>Submit</button>
        </div>
      )}

      {completion === 100 && (
        <div style={{ marginTop: 20 }}>
          <button onClick={doExport}>Export</button>
        </div>
      )}
    </div>
  );
}