import { useEffect, useRef, useState } from "react";
import Plot from "react-plotly.js";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

function App() {
  const fileInputRef = useRef(null);
  const conversationScrollRef = useRef(null);
  const conversationEndRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [dataset, setDataset] = useState(null);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    requestAnimationFrame(() => {
      const conversation = conversationScrollRef.current;

      if (conversation) {
        conversation.scrollTo({
          top: conversation.scrollHeight,
          behavior: "smooth",
        });
      }

      conversationEndRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "end",
      });
    });
  }, [messages, asking]);

  const handleFileSelect = (event) => {
    const file = event.target.files?.[0];

    if (!file) return;

    const allowedExtensions = [".csv", ".xlsx", ".xls"];
    const extension = file.name
      .substring(file.name.lastIndexOf("."))
      .toLowerCase();

    if (!allowedExtensions.includes(extension)) {
      setError("Please upload a CSV or Excel file.");
      return;
    }

    setSelectedFile(file);
    setError("");
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError("Please choose a dataset first.");
      return;
    }

    setUploading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Dataset upload failed.");
      }

      setDataset(data);

      setMessages([
        {
          role: "assistant",
          type: "welcome",
          content: `I've loaded "${data.filename}". You can now ask questions about your data.`,
        },
      ]);

      setSelectedFile(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      setError(
        err.message ||
          "Something went wrong while uploading the dataset."
      );
    } finally {
      setUploading(false);
    }
  };

  const handleAskQuestion = async () => {
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) return;

    if (!dataset) {
      setError("Please upload a dataset before asking a question.");
      return;
    }

    const userMessage = {
      role: "user",
      content: trimmedQuestion,
    };

    setMessages((previous) => [...previous, userMessage]);
    setQuestion("");
    setAsking(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          dataset_id: dataset.dataset_id,
          question: trimmedQuestion,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to analyze the question."
        );
      }

      const assistantMessage = {
        role: "assistant",
        content:
          data.answer ||
          "I couldn't generate an answer for that question.",
        result: data.result,
        plan: data.plan,
        visualization: data.visualization,
      };

      setMessages((previous) => [...previous, assistantMessage]);
    } catch (err) {
      setError(
        err.message ||
          "Something went wrong while analyzing your data."
      );

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          type: "error",
          content:
            "I couldn't process that question. Please try again.",
        },
      ]);
    } finally {
      setAsking(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleAskQuestion();
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setQuestion("");
    setError("");
  };

  const handleCopyAnswer = async (content) => {
    try {
      await navigator.clipboard.writeText(content);
    } catch {
      setError("Unable to copy the answer.");
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return "";

    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const recentQuestions = messages
    .filter((message) => message.role === "user")
    .slice(-5)
    .reverse();

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand-mark">AI</div>

          <div className="brand-text">
            <div className="brand-name">Data Analyst</div>
            <div className="brand-subtitle">
              Ask anything about your data
            </div>
          </div>
        </div>

        <button
          type="button"
          className="new-chat-button"
          onClick={handleNewChat}
        >
          <span className="new-chat-icon">+</span>
          <span>New chat</span>
        </button>

        <div className="sidebar-section">
          <div className="sidebar-label">DATASET</div>

          {dataset ? (
            <div className="dataset-card">
              <div className="dataset-icon">CSV</div>

              <div className="dataset-info">
                <div className="dataset-name">
                  {dataset.filename}
                </div>

                <div className="dataset-meta">
                  {dataset.rows} rows · {dataset.columns} columns
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-dataset">
              No dataset uploaded
            </div>
          )}
        </div>

        <div className="sidebar-section recent-section">
          <div className="sidebar-label">RECENT CHATS</div>

          {recentQuestions.length > 0 ? (
            <div className="recent-chats">
              {recentQuestions.map((message, index) => (
                <div
                  className="recent-chat-item"
                  key={`${message.content}-${index}`}
                  title={message.content}
                >
                  <span className="recent-chat-text">
                    {message.content}
                  </span>

                  <span className="recent-chat-arrow">›</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-recent">
              Your recent questions will appear here.
            </div>
          )}
        </div>

        <div className="sidebar-spacer" />

        <div className="tip-card">
          <div className="tip-title">
            <span>💡</span>
            <span>Tip</span>
          </div>

          <div className="tip-heading">
            Ask questions in natural language
          </div>

          <div className="tip-text">
            Try asking about trends, totals, averages,
            rankings, or comparisons.
          </div>
        </div>

        <div className="sidebar-footer">
          <div className="status-dot" />

          <div className="workspace-info">
            <div className="status-title">
              AI Data Analyst
            </div>

            <div className="status-text">
              Local workspace
            </div>
          </div>

          <button
            type="button"
            className="settings-button"
            title="Settings"
            onClick={() => setError("Settings are coming soon.")}
          >
            ⚙
          </button>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="mobile-brand">
            AI Data Analyst
          </div>

          <div className="topbar-right">
            <div className="topbar-status">
              <span className="online-dot" />
              Ready
            </div>

            <button
              type="button"
              className="theme-button"
              title="Theme"
              onClick={() =>
                setError("Dark mode is coming soon.")
              }
            >
              ☾
            </button>
          </div>
        </header>

        <section className="chat-area">
          <div
            className="chat-scroll-area"
            ref={conversationScrollRef}
          >
            {!dataset && messages.length === 0 ? (
              <div className="empty-state">
                <div className="hero-icon">AI</div>

                <h1>Analyze your data</h1>

                <p>
                  Upload a dataset and ask questions
                  in natural language.
                </p>
              </div>
            ) : (
              <div className="conversation">
                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`message-row ${message.role}`}
                  >
                    {message.role === "assistant" && (
                      <div className="avatar assistant-avatar">
                        AI
                      </div>
                    )}

                    <div
                      className={`message-content ${
                        message.type === "error"
                          ? "error-message"
                          : ""
                      }`}
                    >
                      {message.role === "user" ? (
                        <div className="user-bubble">
                          {message.content}
                        </div>
                      ) : (
                        <div className="assistant-content">
                          <div className="answer">
                            {message.content}
                          </div>

                          {message.type !== "welcome" &&
                            message.type !== "error" && (
                              <div className="message-actions">
                                <button
                                  type="button"
                                  title="Copy answer"
                                  onClick={() =>
                                    handleCopyAnswer(
                                      message.content
                                    )
                                  }
                                >
                                  ▢
                                </button>

                                <button
                                  type="button"
                                  title="Helpful"
                                  onClick={() =>
                                    setError(
                                      "Thanks for the feedback."
                                    )
                                  }
                                >
                                  ♡
                                </button>

                                <button
                                  type="button"
                                  title="Not helpful"
                                  onClick={() =>
                                    setError(
                                      "Thanks for the feedback."
                                    )
                                  }
                                >
                                  ♧
                                </button>
                              </div>
                            )}

                          {message.visualization &&
                            message.visualization.chart_type &&
                            message.visualization.chart_type !==
                              "none" &&
                            message.visualization.figure &&
                            message.visualization.figure.data && (
                              <div
                                className="chart-container"
                                style={{
                                  width: "100%",
                                  flexShrink: 0,
                                }}
                              >
                                <div className="chart-header">
                                  <span>Visualization</span>

                                  <span className="chart-type">
                                    {
                                      message.visualization
                                        .chart_type
                                    }
                                  </span>
                                </div>

                                <div
                                  className="plotly-wrapper"
                                  style={{
                                    width: "100%",
                                    minHeight: "360px",
                                    flexShrink: 0,
                                  }}
                                >
                                  <Plot
                                    data={
                                      message.visualization
                                        .figure.data
                                    }
                                    layout={{
                                      ...(
                                        message.visualization
                                          .figure.layout || {}
                                      ),
                                      autosize: true,
                                      height: 360,
                                      margin: {
                                        l: 60,
                                        r: 30,
                                        t: 60,
                                        b: 70,
                                      },
                                      paper_bgcolor:
                                        "rgba(0,0,0,0)",
                                      plot_bgcolor:
                                        "rgba(0,0,0,0)",
                                    }}
                                    config={{
                                      responsive: true,
                                      displaylogo: false,
                                      modeBarButtonsToRemove: [
                                        "lasso2d",
                                        "select2d",
                                      ],
                                    }}
                                    style={{
                                      width: "100%",
                                      height: "360px",
                                    }}
                                    useResizeHandler
                                  />
                                </div>
                              </div>
                            )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {asking && (
                  <div className="message-row assistant">
                    <div className="avatar assistant-avatar">
                      AI
                    </div>

                    <div className="typing-indicator">
                      <span />
                      <span />
                      <span />
                    </div>
                  </div>
                )}

                <div
                  ref={conversationEndRef}
                  className="conversation-end"
                />
              </div>
            )}
          </div>
        </section>

        {error && (
          <div className="error-banner">
            <span>{error}</span>

            <button
              type="button"
              onClick={() => setError("")}
              title="Dismiss"
            >
              ×
            </button>
          </div>
        )}

        <div className="composer-container">
          <div className="composer">
            <button
              type="button"
              className="attach-button"
              onClick={() => fileInputRef.current?.click()}
              title="Upload dataset"
            >
              +
            </button>

            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={handleFileSelect}
              hidden
            />

            <div className="composer-main">
              {selectedFile && (
                <div className="selected-file">
                  <span className="file-icon">CSV</span>

                  <span className="selected-file-name">
                    {selectedFile.name}
                  </span>

                  <span className="file-size">
                    {formatFileSize(selectedFile.size)}
                  </span>

                  <button
                    type="button"
                    className="remove-file-button"
                    onClick={() => {
                      setSelectedFile(null);

                      if (fileInputRef.current) {
                        fileInputRef.current.value = "";
                      }
                    }}
                    title="Remove file"
                  >
                    ×
                  </button>

                  <button
                    type="button"
                    className="upload-inline-button"
                    onClick={handleUpload}
                    disabled={uploading}
                  >
                    {uploading ? "Uploading..." : "Upload"}
                  </button>
                </div>
              )}

              <textarea
                value={question}
                onChange={(event) =>
                  setQuestion(event.target.value)
                }
                onKeyDown={handleKeyDown}
                placeholder={
                  dataset
                    ? "Ask anything about your data..."
                    : "Upload a dataset to start analyzing..."
                }
                disabled={!dataset || asking}
                rows={1}
              />

              <div className="composer-footer">
                <span className="composer-hint">
                  {dataset
                    ? "Press Enter to send"
                    : "CSV and Excel files supported"}
                </span>

                <button
                  type="button"
                  className="send-button"
                  onClick={handleAskQuestion}
                  disabled={
                    !dataset ||
                    !question.trim() ||
                    asking
                  }
                  title="Send"
                >
                  ↑
                </button>
              </div>
            </div>
          </div>

          <div className="disclaimer">
            AI Data Analyst can make mistakes.
            Verify important results.
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
