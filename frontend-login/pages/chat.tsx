export default function ChatPage() {
  return (
    <div className="min-h-screen w-full bg-gray-600 p-4">
      <div className="h-full w-full rounded-2xl bg-gray-500 p-4 flex flex-col">
        {/* Chat Container - Centered */}
        <div className="flex-1 flex flex-col justify-center items-center">
          {/* Chat History Area - Currently empty/hidden */}
          <div className="flex-1 w-full overflow-y-auto mb-4">
            {/* Chat messages would go here */}
          </div>

          {/* Input Bar - Bottom Center */}
          <div className="w-4/5 h-10 bg-gray-400 rounded-lg flex items-center justify-between px-2">
            <input
              type="text"
              placeholder="Type your message..."
              className="flex-1 border-none bg-transparent text-white text-base outline-none placeholder-gray-300"
            />
            <button className="w-8 h-8 rounded-full bg-white text-black flex items-center justify-center ml-2 hover:bg-gray-100 transition-colors">
              →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
