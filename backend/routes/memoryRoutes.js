const express=require('../utils/miniExpress'); const {requireAuth}=require('../utils/security'); const {all,get}=require('../db'); const r=express.Router();
r.get('/projects/:projectId/anchors',requireAuth,(req,res)=>res.json(all('SELECT * FROM memory_anchors WHERE project_id=? ORDER BY importance_score DESC',[req.params.projectId])));
r.get('/projects/:projectId/frames',requireAuth,(req,res)=>res.json(all('SELECT * FROM memory_frames WHERE project_id=? ORDER BY created_at DESC',[req.params.projectId])));
r.get('/projects/:projectId/snapshots',requireAuth,(req,res)=>res.json(all('SELECT * FROM project_memory_snapshots WHERE project_id=? ORDER BY snapshot_no DESC',[req.params.projectId])));
r.get('/anchors/:id',requireAuth,(req,res)=>res.json(get('SELECT * FROM memory_anchors WHERE id=?',[req.params.id])));
module.exports=r;
