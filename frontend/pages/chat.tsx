  'use client'
  import axios, { formToJSON } from 'axios';
  import { useState, useRef, useEffect, useContext } from 'react';

  import { AuthContext } from './api/authcontext';
  import { useRouter } from 'next/router';
  import { error } from 'console';
  // === SVG ICON COMPONENTS ===



  export default function Home() {
    const [message, setMessage] = useState("");
    const [userMessages, setUserMessages] = useState<string[]>([]);
    const [crewResponse,setCrewResponse]=useState<string[]>([])
    const [i, setI] = useState(1);
    const messagesEndRef = useRef<HTMLDivElement | null>(null);
    const [active, setActive] = useState('new');
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [loading, setLoading] = useState(true);
    const [imgURL,setImgURL]=useState(null);
    const [data,setData]=useState([]);
    const navItems = [
      { id: 'new', label: 'New Chat', icon: PlusIcon },
      { id: 'previous', label: 'Previous Chats', icon: ChatsIcon },
      { id: 'settings', label: 'Settings', icon: SettingsIcon },
    ];
    
    useEffect(() => {
  const gettingChats = async () => {
    const token = localStorage.getItem("token");
    try {
      const res = await axios.get("http://localhost:8000/gettingChats", {
        headers: { Authorization: `Bearer ${token}` }
      });
      setData(res.data);
      setCrewResponse(data)//start editing from here
    } catch (error) {
      console.log("Error fetching chats:", error);
    }
  };
  gettingChats();
}, []);


    async function clickEvent() {

      const request_data = {
        "user_request": message
      }


      if (message.trim() !== "") {
        try {
          const token = localStorage.getItem("token")
          const response = await axios.post("http://localhost:8000/chat", request_data,
            {
              headers: {
                Authorization: `Bearer ${token}`, //  Send token in header
                'Content-Type': 'application/json',
              },
            }
          );
          console.log(response);
          setI(i + 1);
          setUserMessages(prev => [...prev, message.trim()]);
          setCrewResponse(prev=>[...prev,response.data]);
          setMessage("");
        }
        catch (error) {
          console.log("Error in getting Resposne from backend!!", error);
        }

      }
      else {
        alert("Kindly enter some text!!");
      }






    }

    useEffect(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [userMessages]);
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
    }, [isLoggedIn, loading])
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

                  {/* userMessages container */}
                  <div className="px-4 space-y-3 py-2 flex flex-col mb-16">
                    {data.map((val, i) => (
                      <div key={i}>
                      <div
                        className={`text-white px-4 py-2 rounded-xl w-fit max-w-[75%] break-words bg-[#42a742] self-end`}
                       
                        >{val.user_request}</div>
                        <div
                        className={`text-white px-4 py-2 rounded-xl w-fit max-w-[75%] break-words bg-[#283039] self-start`}
                        dangerouslySetInnerHTML={{ __html: val.crew_response }} // render HTML instead of plain text
                        >{val.crew_response}</div>
                        </div>
                    ))}
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
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter') clickEvent(); }}
                          />
                          <div className="flex bg-[#283039] items-center justify-center pr-4 rounded-r-xl">
                            <button
                              className="min-w-[84px] h-8 px-4 bg-[#0a65c1] text-white text-sm font-medium rounded-full hidden md:block"
                              onClick={clickEvent}>
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
