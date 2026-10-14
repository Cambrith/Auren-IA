import { describe, it, expect } from 'vitest';
import { changeTask, restoreAurenTask, newAurenChatParams, singleAurenModel, type AurenOptions } from './aurenTask';
const chat: AurenOptions = {
	mode_id: 'insight',
	web_search: true,
	billing_confirmed: true,
	image_generation: false
};
describe('task persistence and restoration', () => {
	it('migrates an old image-only selection without overriding an explicit task', () => {
		expect(restoreAurenTask({}, true)).toBe('image');
		expect(restoreAurenTask({auren_task:'chat'}, true)).toBe('chat');
		expect(restoreAurenTask({lunvri_image_generation:true}, false)).toBe('image');
	});
	it('restores bulk selections to automatic and preserves one valid manual model', () => {
		expect(singleAurenModel(['a','b'], ['a','b','cavren:auto'])).toEqual(['cavren:auto']);
		expect(singleAurenModel(['b'], ['a','b','cavren:auto'])).toEqual(['b']);
	});
	it('defaults old chats to automatic images and remembers the conversation', () => {
		const switched = changeTask(chat, 'cavren:gemini:chat', true);
		expect(switched.model).toBe('cavren:auto');
		expect(switched.options.conversation_model).toBe('cavren:gemini:chat');
		expect(switched.options.billing_confirmed).toBe(false);
	});
	it('restores both models after a serialized reload', () => {
		const image = changeTask(chat, 'chat-choice', true);
		const reloaded = JSON.parse(JSON.stringify({ ...image.options, image_profile: 'detailed' }));
		const restored = changeTask(reloaded, 'image-choice', false);
		expect(restored.model).toBe('chat-choice');
		expect(restored.options.mode_id).toBe('insight');
		expect(restored.options.web_search).toBe(true);
		expect(changeTask(restored.options, restored.model, true).model).toBe('image-choice');
		expect(restored.options.image_profile).toBe('detailed');
	});
	it('leaves an already active task intact', () => {
		expect(changeTask(chat, 'manual', false)).toEqual({ options: chat, model: 'manual' });
	});
});

import { changeAurenTask } from './aurenTask';
it('stores the image profile but disables manual override in the automatic task', () => {
 const image={...chat,task_id:'image',image_generation:true,image_profile:'detailed',image_profile_manual:true};
 const automatic=changeAurenTask(image,'image-model','auto');
 const saved=JSON.parse(JSON.stringify(automatic.options));
 expect(saved.image_profile).toBe('detailed');expect(saved.image_profile_manual).toBe(false);
 const restored=changeAurenTask(saved,'cavren:auto','image');expect(restored.options.image_profile_manual).toBe(true);
});
it('remembers per-task mode and model and restores conversation after reload', () => {
 const initial={...chat, mode_manual:true};
 const code=changeAurenTask(initial,'chat-model','code');
 expect(code.options.mode_id).toBe('arquiteto');
 const codeManual={...code.options,mode_id:'insight',mode_manual:true};
 const back=changeAurenTask(JSON.parse(JSON.stringify(codeManual)),'code-model','chat');
 expect(back.model).toBe('chat-model');expect(back.options.mode_id).toBe('insight');
 const again=changeAurenTask(back.options,back.model,'code');
 expect(again.model).toBe('code-model');expect(again.options.mode_id).toBe('insight');
});

it('starts fresh conversations automatically without migrating historical chat intent', () => {
 expect(newAurenChatParams()).toEqual({auren_task:'auto',auren_mode_manual:false,cavren_mode_id:'ether'});
 expect(restoreAurenTask({},false)).toBe('chat');
 expect(restoreAurenTask({auren_task:'code'},false)).toBe('code');
});
it('requires automatic mode when returning to automatic task', () => {
 const selected=changeAurenTask({...chat,task_id:'chat',mode_manual:true},'manual-model','auto');
 expect(selected.options.mode_id).toBe('ether');expect(selected.options.mode_manual).toBe(false);
 expect(changeAurenTask(selected.options,'cavren:auto','chat').options.mode_id).toBe('insight');
});

import { normalizeAurenOptions } from './aurenTask';
it('migrates historical automatic task overrides without changing a manual task', () => {
 expect(normalizeAurenOptions({...chat,task_id:'auto',mode_manual:true,image_profile_manual:true})).toMatchObject({mode_id:'ether',mode_manual:false,image_profile_manual:false});
 expect(normalizeAurenOptions({...chat,task_id:'chat',mode_manual:true}).mode_manual).toBe(true);
});
