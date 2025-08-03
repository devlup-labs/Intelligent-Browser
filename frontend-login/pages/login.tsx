import Link from "next/link";
import { useState } from "react";
import axios from "axios";
import { useRouter } from "next/router";
import { useContext } from "react";
import {AuthContext} from "./api/authcontext"

export default function loginpage() {
    const { login, logout }=useContext(AuthContext);
    const router= useRouter();
    const [email, setEmail]= useState("");
    const [password, setPassword]= useState("");

    const forlogin= async () => {
        try{


            const formData = new URLSearchParams();
            formData.append("username", email);
            formData.append("password", password);

            const response = await axios.post("http://localhost:8000/auth/login", formData, {
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
            },
});


            const {access_token} = response.data;
            login();
            localStorage.setItem("token", access_token);
            router.push("/chat");
        } catch (err: any) {
            alert("Login failed: "+ err.response?.data?.detail || err.message);
            logout();
        }

    };


    return (
        <div className="h-screen flex items-center justify-center bg-gradient-to-r from-gray-800 to-gray-900 text-white">
            <div className="bg-black bg-opacity-40 p-10 rounded-xl shadow-lg max-w-md w-full space-y-6">
                <h1 className="text-3xl font-bold text-center"> Login
                </h1>
                <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full p-3 rounded bg-gray-700 focus:outline-none focus:ring-blue-500" />
                <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full p-3 rounded bg-gray-700 focus:outline-none focus:ring-blue-500" />

                <button onClick={forlogin} className="w-full px-8 py-3 bg-blue-800 bg-opacity-20 hover:bg-blue-900 text-white text-lg rounded-lg transition">Continue</button>
            </div>
        </div>
    );

}