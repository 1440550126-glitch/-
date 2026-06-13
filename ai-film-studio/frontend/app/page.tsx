'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Project } from '@/types/studio';
import { StatusBadge } from '@/components/StatusBadge';
export default function Dashboard() { const [projects,setProjects]=useState<Project[]>([]); const [err,setErr]=useState(''); useEffect(()=>{api.projects().then(setProjects).catch(e=>setErr(e.message));},[]); return <div className="space-y-6"><div className="card"><h1 className="text-3xl font-bold">Dashboard</h1><p className="mt-2 text-slate-300">管理 AI 电影、动漫、短剧、广告片制作项目，状态全量写入数据库。</p><Link className="btn mt-4 inline-block" href="/create">创建新项目</Link></div>{err&&<p className="text-red-300">{err}</p>}<div className="grid gap-4 md:grid-cols-2">{projects.map(p=><Link href={`/projects/${p.id}/story`} className="card hover:border-cyan-400" key={p.id}><div className="flex justify-between"><h2 className="text-xl font-bold">{p.title}</h2><StatusBadge status={p.status}/></div><p className="mt-3 text-slate-300">{p.type} · {p.duration_seconds}s · {p.aspect_ratio} · {p.visual_style}</p><p className="text-slate-400">导演性格：{p.director_personality} / 观众：{p.target_audience}</p></Link>)}</div></div>; }
