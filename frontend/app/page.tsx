'use client';
import { useState } from 'react';
import BeeqSetup from './beeq';
import ReactMarkdown from 'react-markdown';

export default function Home() {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: 'Hello! How can I help you today?' },
  ]);
  const [input, setInput] = useState('');

  const handleSend = async () => {
    if (input.trim() === '') return;
    setMessages(prev => [...prev, { sender: 'user', text: input }]);
    const userMessage = input;
    setInput('');

    try {
      const res = await fetch('http://localhost:8000/api/openai/response', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_query: userMessage }),
      });
      const responseText = await res.text();
      setMessages(prev => [...prev, { sender: 'bot', text: responseText || 'No response' }]);
        }
    catch (err) {
        setMessages(prev => [...prev, { sender: 'bot', text: 'Error: Could not get response.' }]);
      }
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
          <h2 style={{ textAlign: "center", marginBottom: 24 }}>Smart Librarian Chatbot</h2>
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
                {msg.sender === "bot" ? (
                  <span style={{
                    display: "inline-block",
                    padding: "16px 20px",
                    borderRadius: 18,
                    background: "linear-gradient(135deg, #f3f6fc 60%, #e9f0fb 100%)",
                    color: "#222",
                    maxWidth: "80%",
                    textAlign: "left",
                    whiteSpace: "pre-wrap",
                    fontSize: "1.08rem",
                    fontFamily: "Segoe UI, Arial, sans-serif",
                    border: "1px solid #dbeafe",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
                  }}>
                    <ReactMarkdown>{msg.text.replace(/\\n/g, '\n')}</ReactMarkdown>
                  </span>
                ) : (
                  <span style={{ display: "inline-block", padding: "8px 16px", borderRadius: 16, background: "#0070f3", color: "#fff" }}>
                    {msg.text}
                  </span>
                )}
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
