import Link from 'next/link';
const tabs = [['story','大局观'],['script','剧本'],['casting','选角'],['assets','美术资产'],['shots','分镜'],['generation','生成'],['memory','记忆挂点'],['review','质检'],['export','导出']];
export function ProjectNav({ id }: { id:number }) { return <div className="mb-6 flex flex-wrap gap-2">{tabs.map(([p,l]) => <Link className="rounded-lg border border-slate-700 px-3 py-2 text-sm hover:border-cyan-400" key={p} href={`/projects/${id}/${p}`}>{l}</Link>)}</div>; }
