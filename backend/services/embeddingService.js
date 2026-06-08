const volc=require('../providers/volcengineProvider'); const mock=require('./mockProvider'); const {route}=require('./modelRouter'); const {all}=require('../db');
function localVector(text){ const v=Array(16).fill(0); [...String(text)].forEach((c,i)=>v[i%16]+=c.charCodeAt(0)/1000); return v; }
async function createTextEmbedding(text){ try{ const r=await volc.callEmbeddingModel({model:route('embedding'),text}); return {embedding:JSON.parse(r.output_text),model:r.model,real:true}; }catch(e){ return {embedding:localVector(text),model:'local-hash-embedding',real:false,warning:e.message}; } }
async function createImageEmbedding(frame_url){ return createTextEmbedding(`Image frame summary for ${frame_url}`); }
function cosine(a,b){ let dot=0,aa=0,bb=0; for(let i=0;i<Math.min(a.length,b.length);i++){dot+=a[i]*b[i]; aa+=a[i]*a[i]; bb+=b[i]*b[i];} return dot/(Math.sqrt(aa)*Math.sqrt(bb)||1); }
function searchSimilarMemory(project_id, embedding, top_k=5){ return all('SELECT * FROM memory_anchors WHERE project_id=?',[project_id]).map(a=>{ let e=[]; try{e=JSON.parse(a.embedding_json||'[]')}catch{} return {...a,score:cosine(embedding,e)}; }).sort((a,b)=>b.score-a.score).slice(0,top_k); }
module.exports={createTextEmbedding,createImageEmbedding,searchSimilarMemory};
