import {describe,it,expect} from 'vitest';
import {taskProfiles,modelCardWidth} from './aurenProfiles';
describe('task-owned profiles and card sizing',()=>{
 it('automatic task offers exactly one automatic profile',()=>{expect(taskProfiles('auto').profiles.map(p=>p.id)).toEqual(['auto']);});
 it('each task owns creative names and a meaningful caption',()=>{
  for(const task of ['chat','image','code','documents','research','speech','transcribe']){
   expect(taskProfiles(task).caption).toBeTruthy();expect(taskProfiles(task).profiles.length).toBeGreaterThan(0);
   expect(new Set(taskProfiles(task).profiles.map(p=>p.id)).size).toBe(taskProfiles(task).profiles.length);
  }
  expect(taskProfiles('code').profiles.find(p=>p.id==='arquiteto')?.name).toBe('Forja');
  expect(taskProfiles('image').profiles.map(p=>p.name)).toEqual(['Centelha','Aurora','Prisma']);
 });
 it('keeps automatic equal to peers and only moderately enlarges long manual names',()=>{
  expect(modelCardWidth('irrelevant',true)).toBe(176);expect(modelCardWidth('Tiny Aya Water',false)).toBeLessThanOrEqual(224);
  expect(modelCardWidth('x'.repeat(100),false)).toBe(224);expect(modelCardWidth('A',false)).toBe(176);
 });
});
