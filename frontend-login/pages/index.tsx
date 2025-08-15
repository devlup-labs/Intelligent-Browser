import Link from "next/link";

export default function home(){
    return(
        <div className="h-screen w-screen bg-[url('/bg.jpg')] bg-cover bg-center flex items-center justify-center">
            <div className="bg-black bg-opacity-40 p-10 rounded-2xl shadow-lg w-full max-w-md h-[500px] text-center flex flex-col items-center justify-center">
                <div className="flex flex-col items-center justify-center space-y-6">
                    <h1 className="text-white text-4xl font-bold ">Welcome!</h1>

                <div className="flex flex-col space-y-4 w-full items-center">
                    <Link href="/login">
                    <button className="w-32 px-8 py-3 bg-blue-800 bg-opacity-20 hover:bg-blue-900 text-white text-lg rounded-lg transition focus:outline-none focus:ring-2 focus:ring-blue-500 "aria-label= "Navigate to login page">Login</button>
                    </Link>
                    <Link href="/signup">
                    <button className="w-32 px-8 py-3 bg-blue-800 bg-opacity-30 hover:bg-blue-900 text-white text-lg rounded-lg transition focus:outline-none focus:ring-2 focus:ring-blue-500 "aria-label= "Navigate to login page">Sign Up</button>

                    </Link>

                </div>

                </div>
                
            </div>
            
            
        </div>
    );

}