'use strict';
/* Match recorded caption transitions to scene audio. Browser video capture can
 * start seconds after the wall clock; wall timestamps must not become PTS. */
const {execFileSync}=require('node:child_process');
function alignCapturedScenes(ffmpeg,video,scenes){
 const fps=25,width=360,height=18,frameSize=width*height;
 const raw=execFileSync(ffmpeg,['-hide_banner','-v','error','-i',video,'-vf','crop=1440:70:0:930,scale=360:18,format=gray','-r',String(fps),'-an','-f','rawvideo','pipe:1'],{maxBuffer:100*1024*1024,timeout:120000});
 const count=raw.length/frameSize;
 if(!Number.isInteger(count)||count<2)throw new Error('Could not measure captured scene frames.');
 const changes=[];
 for(let frame=1;frame<count;frame++){
  let sum=0;const start=frame*frameSize,previous=start-frameSize;
  for(let pixel=0;pixel<frameSize;pixel++)sum+=Math.abs(raw[start+pixel]-raw[previous+pixel]);
  const strength=sum/frameSize;
  if(strength>3){
   const event={timeMs:frame/fps*1000,strength};const last=changes.at(-1);
   if(last&&event.timeMs-last.timeMs<100){if(strength>last.strength)changes[changes.length-1]=event;}
   else changes.push(event);
  }
 }
 const wallTimes=scenes.map(s=>s.wallStartMs??s.startMs);let best;
 for(const wall of wallTimes)for(const event of changes){
  const offset=wall-event.timeMs;if(offset< -1000||offset>20000)continue;
  let matches=0,error=0;const events=[];
  for(const stamp of wallTimes){const expected=stamp-offset;let nearest;
   for(const item of changes)if(!nearest||Math.abs(item.timeMs-expected)<Math.abs(nearest.timeMs-expected))nearest=item;
   const difference=Math.abs(nearest.timeMs-expected);if(difference<=180)matches++;error+=difference;events.push(nearest);
  }
  if(!best||matches>best.matches||(matches===best.matches&&error<best.error))best={matches,error,offset,events};
 }
 if(!best||best.matches!==scenes.length||new Set(best.events.map(e=>e.timeMs)).size!==scenes.length)throw new Error('Scene captions could not be aligned reliably; refusing a mistimed export.');
 const aligned=scenes.map((scene,i)=>({...scene,wallStartMs:wallTimes[i],startMs:Math.round(best.events[i].timeMs)}));
 for(let i=1;i<aligned.length;i++)if(aligned[i].startMs<aligned[i-1].startMs+aligned[i-1].durationMs)throw new Error('Aligned scene narration overlaps the next caption.');
 const endMs=Math.max(...aligned.map(s=>s.startMs+s.durationMs));
 const videoDurationMs=count/fps*1000;
 return {scenes:aligned,videoDurationMs,padSeconds:Math.max(0,(endMs+500-videoDurationMs)/1000),alignment:{method:'measured_caption_frame_transitions',fps,mean_wall_clock_offset_ms:Math.round(wallTimes.reduce((sum,time,i)=>sum+time-aligned[i].startMs,0)/aligned.length),scene_count:aligned.length,max_fit_error_ms:Math.max(...best.events.map((e,i)=>Math.abs(e.timeMs-(wallTimes[i]-best.offset))))}};
}
module.exports={alignCapturedScenes};
