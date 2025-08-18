
"use client";

import Link from "next/link";



export default function Dashboard() {
  return (
    <div className="h-screen w-screen bg-[url('/bg.jpg')] bg-cover bg-center flex items-center justify-center">
      <div className="bg-black bg-opacity-60 p-10 rounded-2xl shadow-lg w-full max-w-xl text-center">
        <h1 className="text-white text-4xl font-bold mb-6">Welcome to Your Dashboard</h1>
        <p className="text-white text-lg mb-6">You are now logged in.</p>

        <div className="flex justify-center space-x-4">
          <Link href="/">
            <button className="px-6 py-2 bg-blue-700 text-white rounded-md hover:bg-blue-800 transition">
              Go Home
            </button>
          </Link>
          <Link href="/login">
            <button className="px-6 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition">
              Logout
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
}
