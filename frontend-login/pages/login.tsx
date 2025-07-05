import Link from "next/link";
import { useState } from "react";
import axios from "axios";
import { useRouter } from "next/router";



export default function loginpage() {

    const router= useRouter();
    const [email, setEmail]= useState("");
    const [password, setPassword]= useState("");

    const forlogin= async () => {
        try{
            const response= await axios.post("http://localhost:8000/login", {
                email,
                password,
            });

            const {token} = response.data;
            localStorage.setItem("token", token);
            router.push("/dashboard");
        } catch (err: any) {
            alert("Login failed: "+ err.response?.data?.detail || err.message);
        }

    };


    return (
        <div className="h-screen flex items-center justify-center bg-gradient-to-r from-gray-800 to-gray-900 text-white">
            <div className="bg-black bg-opacity-40 p-10 rounded-xl shadow-lg max-w-md w-full space-y-6">
                <h1 className="text-3xl font-bold text-center"> Login
                </h1>
                <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full p-3 rounded bg-gray-700 focus:outline-none focus:ring-blue-500" />
                <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full p-3 rounded bg-gray-700 focus:outline-none focus:ring-blue-500" />
                <button onClick={forlogin} className="w-full px-8 py-3 bg-blue-850 bg-opacity-20 hover:bg-blue-900 text-white text-lg rounded-lg transition">Continue</button>
            </div>
        </div>
    );

}