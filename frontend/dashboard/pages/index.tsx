import Head from "next/head";
import React, { useState } from "react";

export default function Home() {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <>
      <Head>
        <title>Scout.io | Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />

      </Head>

      <div className="app-container">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="logo-section">
            <div className="logo-icon"></div>
            <h1>Scout.io</h1>
          </div>
          <nav className="nav-menu">
            <button
              onClick={() => setActiveTab("overview")}
              className={`nav-item ${activeTab === "overview" ? "active" : ""}`}
            >
              <span className="icon">📊</span> Overview
            </button>
            <button
              onClick={() => setActiveTab("chatbots")}
              className={`nav-item ${activeTab === "chatbots" ? "active" : ""}`}
            >
              <span className="icon">🤖</span> Chatbots
            </button>
            <button
              onClick={() => setActiveTab("sources")}
              className={`nav-item ${activeTab === "sources" ? "active" : ""}`}
            >
              <span className="icon">📂</span> Knowledge Sources
            </button>
            <button
              onClick={() => setActiveTab("policies")}
              className={`nav-item ${activeTab === "policies" ? "active" : ""}`}
            >
              <span className="icon">🛡️</span> Policies
            </button>
            <button
              onClick={() => setActiveTab("analytics")}
              className={`nav-item ${activeTab === "analytics" ? "active" : ""}`}
            >
              <span className="icon">📈</span> Analytics
            </button>
            <button
              onClick={() => setActiveTab("settings")}
              className={`nav-item ${activeTab === "settings" ? "active" : ""}`}
            >
              <span className="icon">⚙️</span> Settings
            </button>
          </nav>
          <div className="sidebar-footer">
            <div className="user-profile">
              <div className="user-avatar">VK</div>
              <div className="user-info">
                <span className="user-name">Vinay Vangala</span>
                <span className="user-role">Platform Admin</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="main-content">
          <header className="content-header">
            <div className="header-title">
              <h2>Organization Dashboard</h2>
              <p>Manage chatbots, knowledge bases, and compliance policies.</p>
            </div>
            <div className="header-actions">
              <span className="status-badge online">
                <span className="indicator"></span> Core Service Connected
              </span>
            </div>
          </header>

          {/* Tab content conditional rendering */}
          {activeTab === "overview" && (
            <div className="tab-pane fade-in">
              {/* Quick Metrics */}
              <div className="metrics-grid">
                <div className="metric-card">
                  <div className="metric-header">
                    <span className="metric-label">Total Chatbots</span>
                    <span className="metric-icon">🤖</span>
                  </div>
                  <div className="metric-value">4</div>
                  <div className="metric-trend up">
                    <span className="trend-arrow">↑</span> +1 this week
                  </div>
                </div>

                <div className="metric-card">
                  <div className="metric-header">
                    <span className="metric-label">Total Sessions</span>
                    <span className="metric-icon">💬</span>
                  </div>
                  <div className="metric-value">12,482</div>
                  <div className="metric-trend up">
                    <span className="trend-arrow">↑</span> +18.4% monthly
                  </div>
                </div>

                <div className="metric-card">
                  <div className="metric-header">
                    <span className="metric-label">Knowledge Synced</span>
                    <span className="metric-icon">📂</span>
                  </div>
                  <div className="metric-value">148 MB</div>
                  <div className="metric-trend status-good">
                    <span className="trend-arrow">✔</span> All synced
                  </div>
                </div>

                <div className="metric-card">
                  <div className="metric-header">
                    <span className="metric-label">Policy Violations</span>
                    <span className="metric-icon">🛡️</span>
                  </div>
                  <div className="metric-value">0</div>
                  <div className="metric-trend status-perfect">
                    <span className="trend-arrow">✔</span> Compliant
                  </div>
                </div>
              </div>

              {/* Chatbots Section */}
              <div className="section-header">
                <h3>Active Chatbots</h3>
                <button
                  className="btn btn-primary"
                  onClick={() => setActiveTab("chatbots")}
                >
                  + Create Chatbot
                </button>
              </div>

              <div className="chatbots-list">
                <div className="chatbot-card">
                  <div className="chatbot-status active"></div>
                  <div className="chatbot-info">
                    <h4>Customer Support Agent</h4>
                    <p>
                      Handles FAQS, billing, and returns. Integrated with
                      website widget.
                    </p>
                  </div>
                  <div className="chatbot-meta">
                    <span className="meta-tag">GPT-4 Fallback</span>
                    <span className="meta-tag">12 sources</span>
                  </div>
                </div>
                <div className="chatbot-card">
                  <div className="chatbot-status active"></div>
                  <div className="chatbot-info">
                    <h4>Internal Tech Support</h4>
                    <p>
                      Handles onboarding, IT service requests, and hardware
                      issues.
                    </p>
                  </div>
                  <div className="chatbot-meta">
                    <span className="meta-tag">Gemma 2 Open</span>
                    <span className="meta-tag">5 sources</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab !== "overview" && (
            <div className="placeholder-pane fade-in">
              <div className="placeholder-icon">🛠️</div>
              <h3>Tab: {activeTab.toUpperCase()}</h3>
              <p>
                Detailed module component implementation is in progress. The
                infrastructure is fully ready.
              </p>
              <button
                className="btn btn-secondary"
                onClick={() => setActiveTab("overview")}
              >
                Return to Overview
              </button>
            </div>
          )}
        </main>
      </div>

      <style jsx global>{`
        :root {
          --bg-dark: #090a0f;
          --bg-card: rgba(18, 20, 32, 0.7);
          --border-color: rgba(255, 255, 255, 0.08);
          --accent-purple: #9d4edd;
          --accent-cyan: #06d6a0;
          --accent-blue: #3a86ff;
          --text-primary: #f8f9fa;
          --text-secondary: #adb5bd;
          --font-family: "Plus Jakarta Sans", sans-serif;
          --font-display: "Outfit", sans-serif;
        }

        * {
          box-sizing: border-box;
          margin: 0;
          padding: 0;
        }

        body {
          background-color: var(--bg-dark);
          color: var(--text-primary);
          font-family: var(--font-family);
          overflow-x: hidden;
          background-image:
            radial-gradient(
              circle at 10% 20%,
              rgba(157, 78, 221, 0.08) 0%,
              transparent 40%
            ),
            radial-gradient(
              circle at 90% 80%,
              rgba(58, 134, 255, 0.08) 0%,
              transparent 45%
            );
          background-attachment: fixed;
        }

        .app-container {
          display: flex;
          min-height: 100vh;
        }

        /* Sidebar Styling */
        .sidebar {
          width: 280px;
          background: rgba(13, 15, 24, 0.95);
          border-right: 1px solid var(--border-color);
          display: flex;
          flex-direction: column;
          padding: 30px 20px;
          backdrop-filter: blur(10px);
        }

        .logo-section {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 40px;
        }

        .logo-icon {
          width: 32px;
          height: 32px;
          border-radius: 8px;
          background: linear-gradient(
            135deg,
            var(--accent-purple),
            var(--accent-blue)
          );
          box-shadow: 0 0 15px rgba(157, 78, 221, 0.4);
        }

        .logo-section h1 {
          font-family: var(--font-display);
          font-size: 1.4rem;
          font-weight: 800;
          letter-spacing: 0.5px;
          background: linear-gradient(to right, #fff, #a2a2a2);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .nav-menu {
          display: flex;
          flex-direction: column;
          gap: 8px;
          flex: 1;
        }

        .nav-item {
          display: flex;
          align-items: center;
          gap: 12px;
          background: transparent;
          border: none;
          color: var(--text-secondary);
          padding: 12px 16px;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.95rem;
          text-align: left;
          transition: all 0.25s ease;
        }

        .nav-item:hover {
          background: rgba(255, 255, 255, 0.04);
          color: var(--text-primary);
        }

        .nav-item.active {
          background: rgba(157, 78, 221, 0.12);
          color: var(--text-primary);
          border-left: 3px solid var(--accent-purple);
        }

        .sidebar-footer {
          margin-top: auto;
          padding-top: 20px;
          border-top: 1px solid var(--border-color);
        }

        .user-profile {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .user-avatar {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: var(--accent-purple);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          font-size: 0.9rem;
          box-shadow: 0 0 10px rgba(157, 78, 221, 0.3);
        }

        .user-info {
          display: flex;
          flex-direction: column;
        }

        .user-name {
          font-size: 0.9rem;
          font-weight: 600;
        }

        .user-role {
          font-size: 0.75rem;
          color: var(--text-secondary);
        }

        /* Main Content Styling */
        .main-content {
          flex: 1;
          padding: 40px;
          overflow-y: auto;
        }

        .content-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 40px;
        }

        .header-title h2 {
          font-family: var(--font-display);
          font-size: 1.8rem;
          font-weight: 600;
          margin-bottom: 6px;
        }

        .header-title p {
          color: var(--text-secondary);
          font-size: 0.95rem;
        }

        .status-badge {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: rgba(6, 214, 160, 0.1);
          color: var(--accent-cyan);
          padding: 6px 12px;
          border-radius: 20px;
          font-size: 0.8rem;
          font-weight: 600;
          border: 1px solid rgba(6, 214, 160, 0.15);
        }

        .status-badge .indicator {
          width: 6px;
          height: 6px;
          background-color: var(--accent-cyan);
          border-radius: 50%;
          box-shadow: 0 0 8px var(--accent-cyan);
        }

        /* Metrics Grid */
        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 20px;
          margin-bottom: 40px;
        }

        .metric-card {
          background: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: 12px;
          padding: 24px;
          backdrop-filter: blur(10px);
          transition:
            transform 0.3s ease,
            border-color 0.3s ease;
        }

        .metric-card:hover {
          transform: translateY(-4px);
          border-color: rgba(157, 78, 221, 0.3);
        }

        .metric-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .metric-label {
          color: var(--text-secondary);
          font-size: 0.9rem;
          font-weight: 500;
        }

        .metric-icon {
          font-size: 1.2rem;
        }

        .metric-value {
          font-family: var(--font-display);
          font-size: 2.2rem;
          font-weight: 800;
          margin-bottom: 8px;
        }

        .metric-trend {
          font-size: 0.8rem;
          font-weight: 600;
        }

        .metric-trend.up {
          color: var(--accent-cyan);
        }

        .metric-trend.status-good {
          color: var(--accent-blue);
        }

        .metric-trend.status-perfect {
          color: var(--accent-cyan);
        }

        /* Section Layouts */
        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .section-header h3 {
          font-family: var(--font-display);
          font-size: 1.2rem;
          font-weight: 600;
        }

        .chatbots-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .chatbot-card {
          background: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: 12px;
          padding: 20px;
          display: flex;
          align-items: center;
          gap: 20px;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .chatbot-card:hover {
          border-color: rgba(58, 134, 255, 0.3);
          background: rgba(18, 20, 32, 0.95);
        }

        .chatbot-status {
          width: 10px;
          height: 10px;
          border-radius: 50%;
        }

        .chatbot-status.active {
          background-color: var(--accent-cyan);
          box-shadow: 0 0 8px var(--accent-cyan);
        }

        .chatbot-info {
          flex: 1;
        }

        .chatbot-info h4 {
          font-size: 1rem;
          font-weight: 600;
          margin-bottom: 4px;
        }

        .chatbot-info p {
          font-size: 0.85rem;
          color: var(--text-secondary);
        }

        .chatbot-meta {
          display: flex;
          gap: 8px;
        }

        .meta-tag {
          font-size: 0.75rem;
          background: rgba(255, 255, 255, 0.05);
          padding: 4px 10px;
          border-radius: 12px;
          border: 1px solid var(--border-color);
          color: var(--text-secondary);
        }

        /* Buttons */
        .btn {
          padding: 10px 20px;
          border-radius: 8px;
          font-size: 0.9rem;
          font-weight: 600;
          cursor: pointer;
          border: none;
          transition: all 0.25s ease;
        }

        .btn-primary {
          background: linear-gradient(
            135deg,
            var(--accent-purple),
            var(--accent-blue)
          );
          color: #fff;
          box-shadow: 0 4px 15px rgba(157, 78, 221, 0.3);
        }

        .btn-primary:hover {
          opacity: 0.95;
          transform: translateY(-1px);
        }

        .btn-secondary {
          background: rgba(255, 255, 255, 0.05);
          color: var(--text-primary);
          border: 1px solid var(--border-color);
        }

        .btn-secondary:hover {
          background: rgba(255, 255, 255, 0.1);
        }

        /* Placeholder Content */
        .placeholder-pane {
          background: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: 12px;
          padding: 60px;
          text-align: center;
          backdrop-filter: blur(10px);
        }

        .placeholder-icon {
          font-size: 3rem;
          margin-bottom: 20px;
        }

        .placeholder-pane h3 {
          margin-bottom: 10px;
        }

        .placeholder-pane p {
          color: var(--text-secondary);
          margin-bottom: 24px;
        }

        /* Animation */
        .fade-in {
          animation: fadeIn 0.4s ease-out;
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </>
  );
}
