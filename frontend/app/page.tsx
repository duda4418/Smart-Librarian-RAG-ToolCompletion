
'use client';
import { useState } from 'react';
import BeeqSetup from './beeq';

export default function Home() {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: 'Hello! How can I help you today?' },
  ]);
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (input.trim() === '') return;
    setMessages([...messages, { sender: 'user', text: input }]);
    setInput('');
    // Add chatbot API logic here
  };

  return (
      <div
        style={{
          minHeight: "100vh",
          width: "100vw",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "#f5f7fa",
          padding: 0,
          margin: 0,
        }}
      >
        <div
          style={{
            width: "90vw",
            maxWidth: "1200px",
            height: "90vh",
            minHeight: "500px",
            display: "flex",
            flexDirection: "column",
            background: "#fff",
            borderRadius: 24,
            boxShadow: "0 4px 32px rgba(0,0,0,0.12)",
            padding: "2vw 2vw",
          }}
        >
          <h2 style={{ textAlign: "center", marginBottom: 24 }}>Chatbot Discussion</h2>
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              marginBottom: 24,
              border: "1px solid #eee",
              borderRadius: 8,
              padding: 16,
              background: "#fafafa",
              minHeight: 0,
            }}
          >
            {messages.map((msg, idx) => (
              <div key={idx} style={{ textAlign: msg.sender === "user" ? "right" : "left", marginBottom: 12 }}>
                <span style={{ display: "inline-block", padding: "8px 16px", borderRadius: 16, background: msg.sender === "user" ? "#0070f3" : "#eaeaea", color: msg.sender === "user" ? "#fff" : "#333" }}>
                  {msg.text}
                </span>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Type your message..."
              style={{ flex: 1, padding: 10, borderRadius: 8, border: "1px solid #ccc" }}
              onKeyDown={e => { if (e.key === "Enter") handleSend(); }}
            />
            <button
              onClick={handleSend}
              style={{ padding: "10px 20px", borderRadius: 8, background: "#0070f3", color: "#fff", border: "none", cursor: "pointer" }}
            >
              Send
            </button>
          </div>
        </div>
      </div>
  );
}
