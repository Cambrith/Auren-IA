import definitions from './aurenProfiles.json';
export type TaskProfile = { id: string; name: string; description: string };
export function taskProfiles(task: string) {
 return (definitions as Record<string, {caption:string; profiles:TaskProfile[]}>)[task] ?? definitions.chat;
}
export function modelCardWidth(label: string, automatic: boolean) {
 return automatic ? 176 : Math.min(224, Math.max(176, 112 + label.length * 6));
}
