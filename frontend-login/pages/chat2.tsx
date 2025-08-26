'use client'

import { useState, useRef, useEffect } from 'react';
import { useRouter } from "next/router";
import axios from 'axios';

interface Step {
  step_id: number;
  task_name: string;
  status: string;
}

interface WorkflowState {
  isActive: boolean;
  overallTaskName: string;
  masterThought: string;
  estimatedSteps: number;
  steps: Step[];
  currentTaskName: string;
  progressAnalysis: string;
  isCompleted: boolean;
}

interface Message {
  text: string;
  type: 'user' | 'system' | 'workflow';
  workflowData?: any;
}

export default function Home() {
  const [userMessage, setUserMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [workflowState, setWorkflowState] = useState<WorkflowState>({
    isActive: false,
    overallTaskName: '',
    masterThought: '',
    estimatedSteps: 0,
    steps: [],
    currentTaskName: '',
    progressAnalysis: '',
    isCompleted: false
  });
  
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const [active, setActive] = useState('new');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loading, setLoading] = useState(true);
  const socket = useRef<WebSocket | null>(null);
  
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
      const messageData = event.data;
      
      // Try to parse if it's JSON (structured data)
      try {
        const parsedData = JSON.parse(messageData);
        if (parsedData.session_type) {
          handleWorkflowMessage(parsedData);
          return;
        }
      } catch (e) {
        // Not JSON, treat as regular message
      }
      
      // Handle regular system messages
      const systemMessage: Message = {
        text: messageData,
        type: "system"
      };
      setMessages((prevMessages) => [...prevMessages, systemMessage]);
    });

    return () => {
      socket.current?.close();
    };
  }, []);

  const handleWorkflowMessage = (data: any) => {
    const { session_type } = data;
    
    if (session_type === "INITIAL_PLANNING") {
      setWorkflowState({
        isActive: true,
        overallTaskName: data.overall_task_name || '',
        masterThought: data.master_thought || '',
        estimatedSteps: data.estimated_steps || 0,
        steps: data.steps || [],
        currentTaskName: data.current_task?.task_name || '',
        progressAnalysis: '',
        isCompleted: false
      });
      
      const workflowMessage: Message = {
        text: `Starting workflow: ${data.overall_task_name}`,
        type: "workflow",
        workflowData: data
      };
      setMessages((prev) => [...prev, workflowMessage]);
      
    } else if (session_type === "ITERATIVE_PLANNING") {
      setWorkflowState(prev => ({
        ...prev,
        steps: data.steps || prev.steps,
        currentTaskName: data.current_task?.task_name || prev.currentTaskName,
        progressAnalysis: data.progress_analysis || '',
        isCompleted: data.task_is_final || false
      }));
      
      if (data.task_is_final) {
        const completionMessage: Message = {
          text: "🎉 All tasks completed successfully!",
          type: "system"
        };
        setMessages((prev) => [...prev, completionMessage]);
      }
    }
  };

  const sendMessage = () => {
    const userMessageFinal: Message = {
      text: userMessage,
      type: "user"
    };
    setMessages((previos) => [...previos, userMessageFinal]);
    socket.current?.send(userMessage);
    setUserMessage('');
    
    // Reset workflow state for new conversations
    setWorkflowState({
      isActive: false,
      overallTaskName: '',
      masterThought: '',
      estimatedSteps: 0,
      steps: [],
      currentTaskName: '',
      progressAnalysis: '',
      isCompleted: false
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'success':
      case 'completed':
        return '✅';
      case 'pending':
      case 'waiting':
        return '⏳';
      case 'in_progress':
      case 'running':
        return '🔄';
      case 'failed':
      case 'error':
        return '❌';
      default:
        return '📋';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'success':
      case 'completed':
        return 'text-green-400';
      case 'pending':
      case 'waiting':
        return 'text-yellow-400';
      case 'in_progress':
      case 'running':
        return 'text-blue-400';
      case 'failed':
      case 'error':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, workflowState]);

  const router = useRouter();
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
  }, [isLoggedIn, loading]);

  return (
    isLoggedIn ? (
      <div className="relative flex min-h-screen flex-col bg-[#111418] overflow-x-hidden" style={{ fontFamily: 'Manrope, Noto Sans, sans-serif' }}>
        <div className="layout-container flex h-full grow flex-col">
          <div className="flex flex-1 w-full px-6 py-5 gap-4">

            <div className="layout-content-container flex flex-col w-80">
              <div className="flex h-full min-h-[700px] flex-col justify-between bg-[#111418] p-4">
                <div className="flex flex-col gap-4">
                  <h1 className="text-white text-base font-medium leading-normal">Options</h1>
                  <div className="flex flex-col gap-2">
                    {navItems.map(({ id, label, icon: Icon }) => (
                      <div
                        key={id}
                        onClick={() => setActive(id)}
                        className={`flex items-center gap-3 px-3 py-2 rounded-full cursor-pointer transition-colors duration-150 ${active === id ? 'bg-[#283039]' : 'hover:bg-[#899bb6]'
                          }`}
                      >
                        <div className="text-white">
                          <Icon />
                        </div>
                        <p className="text-white text-sm font-medium leading-normal">{label}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
            
            {/* Chat Area */}
            <div className="flex flex-1 justify-center">
              <div className="layout-content-container flex flex-col max-w-[960px] w-full mx-auto">

                {/* Header */}
                <div className="py-5 border-b border-[#2a2f34]">
                  <h2 className="text-white text-[28px] font-bold leading-tight px-4 text-center pb-1">
                    Welcome to Intellibrowse!
                  </h2>
                  <p className="text-white text-base font-normal leading-normal px-4 text-center">
                    Ask me anything, and I'll do my best to do that task.
                  </p>
                </div>

                {/* Messages container */}
                <div className="px-4 space-y-4 py-4 flex flex-col mb-16">
                  {messages.map(({ text, type }, i) => (
                    <div
                      key={i}
                      className={`text-white px-4 py-3 rounded-xl w-fit max-w-[75%] break-words ${type === "user"
                        ? 'bg-[#42a742] self-end'   // User message → right side
                        : 'bg-[#283039] self-start' // Bot message → left side
                        }`}
                    >
                      {text}
                    </div>
                  ))}

                  {/* Workflow Visualization */}
                  {workflowState.isActive && (
                    <div className="bg-[#1a1f24] border border-[#2a2f34] rounded-xl p-6 w-full">
                      <div className="space-y-4">
                        
                        {/* Task Header */}
                        <div className="border-b border-[#2a2f34] pb-4">
                          <h3 className="text-white text-lg font-semibold mb-2">
                            🎯 {workflowState.overallTaskName}
                          </h3>
                          {workflowState.estimatedSteps > 0 && (
                            <p className="text-[#9cabba] text-sm">
                              Estimated steps: {workflowState.estimatedSteps}
                            </p>
                          )}
                        </div>

                        {/* Thinking Phase */}
                        {workflowState.masterThought && (
                          <div className="bg-[#283039] rounded-lg p-4">
                            <div className="flex items-start gap-3">
                              <div className="text-yellow-400 text-xl">🤔</div>
                              <div>
                                <h4 className="text-white font-medium mb-2">Thinking...</h4>
                                <p className="text-[#9cabba] text-sm leading-relaxed">
                                  {workflowState.masterThought}
                                </p>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Progress Analysis */}
                        {workflowState.progressAnalysis && (
                          <div className="bg-[#283039] rounded-lg p-4">
                            <div className="flex items-start gap-3">
                              <div className="text-blue-400 text-xl">📊</div>
                              <div>
                                <h4 className="text-white font-medium mb-2">Progress Update</h4>
                                <p className="text-[#9cabba] text-sm leading-relaxed">
                                  {workflowState.progressAnalysis}
                                </p>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Todo List */}
                        {workflowState.steps.length > 0 && (
                          <div>
                            <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                              <span>📋</span>
                              Task Progress
                            </h4>
                            <div className="space-y-2">
                              {workflowState.steps.map((step) => (
                                <div
                                  key={step.step_id}
                                  className={`flex items-start gap-3 p-3 rounded-lg transition-all duration-300 ${
                                    step.task_name === workflowState.currentTaskName
                                      ? 'bg-[#42a742] bg-opacity-20 border border-[#42a742] border-opacity-30'
                                      : 'bg-[#283039]'
                                  }`}
                                >
                                  <div className="text-lg flex-shrink-0 pt-0.5">
                                    {getStatusIcon(step.status)}
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                      <span className="text-[#9cabba] text-xs font-medium">
                                        Step {step.step_id}
                                      </span>
                                      <span className={`text-xs font-medium ${getStatusColor(step.status)}`}>
                                        {step.status.toUpperCase()}
                                      </span>
                                    </div>
                                    <p className={`text-sm leading-relaxed ${
                                      step.task_name === workflowState.currentTaskName
                                        ? 'text-white font-medium'
                                        : 'text-[#9cabba]'
                                    }`}>
                                      {step.task_name}
                                    </p>
                                    {step.task_name === workflowState.currentTaskName && (
                                      <div className="flex items-center gap-2 mt-2">
                                        <div className="w-2 h-2 bg-[#42a742] rounded-full animate-pulse"></div>
                                        <span className="text-[#42a742] text-xs font-medium">
                                          Currently executing...
                                        </span>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Completion Status */}
                        {workflowState.isCompleted && (
                          <div className="bg-green-500 bg-opacity-10 border border-green-500 border-opacity-30 rounded-lg p-4">
                            <div className="flex items-center gap-3">
                              <div className="text-green-400 text-2xl">🎉</div>
                              <div>
                                <h4 className="text-green-400 font-medium">Task Completed!</h4>
                                <p className="text-green-300 text-sm mt-1">
                                  All steps have been executed successfully.
                                </p>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>

                {/* Fixed Input Box */}
                <div className="fixed bottom-12 left-0 w-full px-4 ml-40">
                  <div className="max-w-[960px] mx-auto">
                    <label className="flex h-12 w-full">
                      <div className="flex w-full items-stretch rounded-xl h-full">
                        <input
                          placeholder="Type your message here..."
                          className="form-input w-full flex-1 rounded-l-xl text-white focus:outline-0 focus:ring-0 border-none bg-[#283039] h-full placeholder:text-[#9cabba] px-4 text-base font-normal"
                          value={userMessage}
                          onChange={(e) => {
                            setUserMessage(e.target.value);
                          }}
                          onKeyDown={(e) => { if (e.key === 'Enter') sendMessage(); }}
                        />
                        <div className="flex bg-[#283039] items-center justify-center pr-4 rounded-r-xl">
                          <button
                            className="min-w-[84px] h-8 px-4 bg-[#0a65c1] text-white text-sm font-medium rounded-full hidden md:block"
                            onClick={sendMessage}>
                            Send
                          </button>
                        </div>
                      </div>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    ) : <></>)
}

function PlusIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" viewBox="0 0 256 256">
      <path d="M208,32H48A16,16,0,0,0,32,48V208a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V48A16,16,0,0,0,208,32ZM184,136H136v48a8,8,0,0,1-16,0V136H72a8,8,0,0,1,0-16h48V72a8,8,0,0,1,16,0v48h48a8,8,0,0,1,0,16Z" />
    </svg>
  );
}

function ChatsIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" viewBox="0 0 256 256">
      <path d="M216,80H184V48a16,16,0,0,0-16-16H40A16,16,0,0,0,24,48V176a8,8,0,0,0,13,6.22L72,154V184a16,16,0,0,0,16,16h93.59L219,230.22a8,8,0,0,0,5,1.78,8,8,0,0,0,8-8V96A16,16,0,0,0,216,80Z" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" viewBox="0 0 256 256">
      <path d="M128,80a48,48,0,1,0,48,48A48.05,48.05,0,0,0,128,80Zm0,80a32,32,0,1,1,32-32A32,32,0,0,1,128,160Z" />
    </svg>
  );
}