import "../styles/globals.css";
import { AuthProvider } from "./api/authcontext";

export default function App({ Component, pageProps }) {
  return (
    <AuthProvider>
      <Component {...pageProps} />
    </AuthProvider>
  );
}
