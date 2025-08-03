"use client";

import { useState } from "react";
import axios from "axios";
import { useRouter } from "next/router";


export default function signuppage() {

    const router= useRouter();
    const [form, setForm]= useState({
        username:"",
        email: "",
        password: "",
    });
    
    const handleChange= (e: React.ChangeEvent<HTMLInputElement>) => {
        setForm({...form, [e.target.name]: e.target.value});
    };

    const handleSubmit= async (e: React.FormEvent) => {
        e.preventDefault();

        try{


            const response= await axios.post("http://localhost:8000/auth/signup", form, {
  headers: {
    "Content-Type": "application/json"
  }
});
            if (response.status ===200){
                alert("Signup successful");
                router.push("/login");
            }
        }
        catch (err) {
            console.error(err);
            alert("Signup failed!");
        }
    };

    return(
        <div className="h-screen flex items-center justify-center bg-gradient-to-r from-gray-800 to-gray-900 text-white">
            <div className="bg-black bg-opacity-40 p-10 rounded-xl shadow-lg max-w-md w-full space-y-6">
                <h1 className="text-3xl font-bold text-center"> Create an Account
                </h1>
                <form onSubmit={handleSubmit} className="flex flex-col space-y-4">

                    <input type="text" name="username" placeholder="Username" value={form.username} onChange={handleChange} className="w-full p-3 rounded bg-gray-700 focus:outline-none focus:ring-blue-500" />
                <input type="email" placeholder="Email" name="email" value={form.email} onChange={handleChange} className="w-full p-3 rounded bg-gray-700 focus:outline-none focus:ring-blue-500" />
                <input type="password" placeholder="Password" name="password" value={form.password} onChange={handleChange} className="w-full p-3 rounded bg-gray-700 focus:outline-none focus:ring-blue-500" />
                <button type="submit" className="w-full px-8 py-3 bg-blue-800 bg-opacity-20 hover:bg-blue-900 text-white text-lg rounded-lg transition">Continue</button>
            </form>
            </div>
        </div>

    );
}