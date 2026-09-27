import "./globals.css";

export const metadata = {
  title: "DeepResearch Agent — Multi-Agent AI Research System",
  description:
    "An autonomous multi-agent research system that takes any research question, runs parallel web searches, fact-checks claims, and produces a fully cited Markdown report.",
  keywords: ["AI research", "multi-agent", "LangGraph", "Claude", "Tavily", "fact checking"],
  openGraph: {
    title: "DeepResearch Agent",
    description: "Autonomous multi-agent research with Claude + Tavily",
    type: "website",
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>{children}</body>
    </html>
  );
}
