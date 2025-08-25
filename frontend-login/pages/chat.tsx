'use client'

import { useState, useRef, useEffect } from 'react';
import { useRouter } from "next/router";
import axios from 'axios';

export default function Home() {
  const [userMessage, setUserMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const messagesEndRef = useRef(null);
  const [active, setActive] = useState('new');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const socket = useRef(null);
  const router = useRouter();

  const navItems = [
    { id: 'new', label: 'New Chat', icon: PlusIcon },
    { id: 'previous', label: 'Previous Chats', icon: ChatsIcon },
    { id: 'settings', label: 'Settings', icon: SettingsIcon },
  ];

  useEffect(() => {
    socket.current = new WebSocket("ws://localhost:8000/websocket");

    socket.current.onopen = () => {
      console.log("✅ Connected to WebSocket");
    };

    socket.current.onmessage = ((event) => {
      const systemMessage = {
        text: event.data,
        type: "system"
      }
      setMessages((prevMessages) => [...prevMessages, systemMessage]);
    })

    return () => {
      socket.current.close();
    };
  }, [])

  const sendMessage = () => {
    if (!userMessage.trim()) return;
    
    const userMessageFinal = {
      text: userMessage,
      type: "user"
    }
    setMessages((previous) => [...previous, userMessageFinal])
    socket.current.send(userMessage);
    setUserMessage('');
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const verifyToken = async () => {
      const token = localStorage.getItem("token");
      setLoading(true);
      try {
        const res = await axios.get("http://localhost:8000/auth/verify_jwt", {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        console.log(res.data);
        setIsLoggedIn(true);
      } catch (err) {
        console.log("Invalid Token: Please log in again");
        localStorage.removeItem("token");
        setIsLoggedIn(false);
      } finally {
        setLoading(false);
      }
    };
    verifyToken();
  }, []);

  useEffect(() => {
    if (!isLoggedIn && !loading) router.push("/login");
  }, [isLoggedIn, loading])

  return (
    isLoggedIn ? (
      <div className="h-screen bg-gray-900 text-gray-100 flex overflow-hidden">
        {/* Sidebar */}
        <div className={`bg-gray-900 border-r border-gray-700 transition-all duration-300 ${
          sidebarOpen ? 'w-64' : 'w-0'
        } overflow-hidden flex flex-col`}>
          {/* Sidebar Header */}
          <div className="p-4 border-b border-gray-700">
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-semibold text-white">Intellibrowse</h1>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex-1 p-4">
            <div className="space-y-2">
              {navItems.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActive(id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    active === id 
                      ? 'bg-gray-700 text-white' 
                      : 'text-gray-400 hover:text-white hover:bg-gray-750'
                  }`}
                >
                  <Icon />
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* User Section */}
          <div className="p-4 border-t border-gray-700">
            <div className="flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white">User</p>
                <p className="text-xs text-gray-400">Online</p>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <header className="bg-gray-900 p-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-2 rounded-lg hover:bg-gray-700 transition-colors"
              >
                <MenuIcon />
              </button>
              <div>
                <h2 className="text-xl font-medium text-white">Chat Assistant</h2>
              </div>
            </div>
          </header>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-4xl mx-auto px-4 py-6">
              {messages.length === 0 ? (
                <div className="text-center py-16">
                  <h3 className="text-2xl font-normal text-white mb-4 font-sans">Welcome to Intellibrowse</h3>
                  <p className="text-gray-400 text-base font-sans leading-relaxed max-w-2xl mx-auto">
                    I'm your AI assistant ready to help you with any questions or tasks you might have. 
                    Start a conversation by typing a message below.
                  </p>
                </div>
              ) : (
                <div className="space-y-6">
                  {messages.map(({ text, type }, i) => (
                    <div key={i} className={`flex ${type === "user" ? 'justify-end' : 'justify-start'}`}>
                      <div className={`flex gap-3 max-w-3xl`}>
                        {/* Message */}
                        <div className={`px-3 py-2 rounded-2xl ${
                          type === "user" 
                            ? 'bg-gray-700 text-gray-100 rounded-br-md border border-gray-600' 
                            : 'bg-gray-800 text-gray-100 rounded-bl-md border border-gray-700'
                        }`}>
                          <p className="text-base leading-relaxed whitespace-pre-wrap font-sans">{text}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>
          </div>

          {/* Input Area */}
          <div className="bg-gray-900 border-t border-gray-700 p-4">
            <div className="max-w-4xl mx-auto">
              <div className="relative">
                <textarea
                  value={userMessage}
                  onChange={(e) => setUserMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      sendMessage();
                    }
                  }}
                  placeholder="Type your message here..."
                  className="w-full bg-gray-800 border border-gray-600 rounded-xl px-4 py-3 pr-12 text-gray-100 placeholder-gray-400 focus:outline-none focus:border-gray-500 focus:ring-1 focus:ring-gray-500 resize-none"
                  rows={1}
                  style={{
                    minHeight: '44px',
                    maxHeight: '120px',
                    resize: 'none',
                    overflowY: userMessage.split('\n').length > 2 ? 'auto' : 'hidden'
                  }}
                />
                <button
                  onClick={sendMessage}
                  disabled={!userMessage.trim()}
                  className="absolute right-2 top-1/2 transform -translate-y-1/2 p-2 rounded-lg bg-gray-600 hover:bg-gray-500 disabled:bg-gray-700 disabled:cursor-not-allowed transition-colors"
                >
                  <SendIcon />
                </button>
              </div>
              <div className="text-xs text-gray-400">
                <span>Press Enter to send, Shift+Enter for new line</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    ) : <></>
  );
}

// Icon Components
function PlusIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="12" y1="5" x2="12" y2="19"></line>
      <line x1="5" y1="12" x2="19" y2="12"></line>
    </svg>
  );
}

function ChatsIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8z"></path>
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3"></circle>
      <path d="M12 1v6M12 17v6M4.22 4.22l4.24 4.24M15.54 15.54l4.24 4.24M1 12h6M17 12h6M4.22 19.78l4.24-4.24M15.54 8.46l4.24-4.24"></path>
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="3" y1="6" x2="21" y2="6"></line>
      <line x1="3" y1="12" x2="21" y2="12"></line>
      <line x1="3" y1="18" x2="21" y2="18"></line>
    </svg>
  );
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="22" y1="2" x2="11" y2="13"></line>
      <polygon points="22,2 15,22 11,13 2,9 22,2"></polygon>
    </svg>
  );
}