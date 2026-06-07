const express=require('../utils/miniExpress'); const {requireAuth}=require('../utils/security'); const ah=require('../utils/asyncHandler'); const projects=require('../services/projectService'); const queue=require('../services/projectQueueService'); const resume=require('../services/projectResumeService'); const {get}=require('../db'); const r=express.Router();
r.get('/',requireAuth,(req,res)=>res.json(projects.listProjects(req.user.sub)));
r.post('/',requireAuth,ah(async(req,res)=>{ const user=get('SELECT * FROM users WHERE id=?',[req.user.sub]); res.json(await projects.createProject(user,req.body)); }));
r.post('/:id/plan',requireAuth,ah(async(req,res)=>res.json(await projects.planProject(req.params.id))));
r.post('/:id/run',requireAuth,ah(async(req,res)=>res.json(await queue.runProject(req.params.id,{maxShots:req.body.maxShots||10}))));
r.post('/:id/process-next',requireAuth,ah(async(req,res)=>res.json(await queue.processNextShot(req.params.id))));
r.post('/:id/resume',requireAuth,ah(async(req,res)=>{ const p=projects.detail(req.params.id).project; const rp=resume.createResumePoint(req.params.id,p.latest_memory_snapshot_id); res.json({resume_point:rp,resumed:projects.autoResumePausedProjects(req.user.sub)}); }));
r.get('/:id',requireAuth,(req,res)=>res.json(projects.detail(req.params.id)));
module.exports=r;
