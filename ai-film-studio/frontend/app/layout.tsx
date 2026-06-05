import './globals.css';
import Link from 'next/link';
export const metadata = { title: 'AI影视制作 Studio', description: 'AI Film Studio MVP' };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="zh-CN"><body><header className="border-b border-slate-800 bg-slate-950/90"><nav className="mx-auto flex max-w-7xl items-center justify-between p-4"><Link href="/" className="text-xl font-bold text-cyan-300">AI影视制作 Studio</Link><Link className="btn" href="/create">创建项目</Link></nav></header><main className="mx-auto max-w-7xl p-6">{children}</main></body></html>;
}
