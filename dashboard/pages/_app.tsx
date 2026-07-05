import "@/styles/globals.css";
import type { AppProps } from "next/app";
import Head from "next/head";
import { Sidebar, MobileTopBar } from "../components/sidebar";

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <Head>
        <title>TidoQuant — Autonomous Trading System</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#0a0c10" />
      </Head>
      <div className="min-h-screen flex">
        <Sidebar />
        <div className="flex-1 min-w-0 flex flex-col">
          <MobileTopBar />
          <Component {...pageProps} />
        </div>
      </div>
    </>
  );
}
