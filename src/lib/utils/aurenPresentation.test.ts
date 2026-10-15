import { describe, it, expect } from 'vitest';
import { aurenStatuses, aurenFiles, imageProgress, aurenActivity } from './aurenPresentation';
describe('Auren response presentation', () => {
 it('hides model and mode details by default and preserves actual queue values', () => {
  const raw=[{action:'task',description:'Tarefa detectada: Image · Modelo secreto'},{action:'fallback',description:'Tentando modelo'}, {action:'image_generation',state:'queued',description:'Deliberate · Horde · fila',queue_position:3,wait_time:20}, {action:'auren_details',hidden:true,description:'Modo · Modelo'}];
  const visible=aurenStatuses(raw,false);
  expect(visible).toHaveLength(1);expect(visible[0].description).toBe('Tempo decorrido: 0 s · Posição na fila: 3 · Estimativa do provedor: 20 s');expect(visible[0].queue_position).toBe(3);expect(visible[0].wait_time).toBe(20);
  expect(aurenStatuses(raw,true).at(-1)?.hidden).toBe(false);expect(raw.at(-1)?.hidden).toBe(true);
  expect(aurenStatuses(raw,false,true)).toEqual([]);
 });
 it('uses actual elapsed time and provider values without inventing a wait estimate', () => {
  expect(imageProgress({},65)).toBe('Tempo decorrido: 1 min 05 s');
  expect(imageProgress({queue_position:0,wait_time:0,eligible_workers:0},12)).toBe('Tempo decorrido: 12 s · Posição na fila: 0 · Estimativa do provedor: 0 s · Nenhum trabalhador elegível no momento');
  expect(imageProgress({queue_position:-1,wait_time:Infinity,eligible_workers:null},2)).toBe('Tempo decorrido: 2 s');
 });
 it('shows generated images only after completion and preserves other files and historical images', () => {
  const files=[{type:'image',url:'result'},{type:'audio',url:'voice'},{type:'file',url:'document'}];
  expect(aurenFiles(files,true,false)).toEqual(files.slice(1));expect(aurenFiles(files,true,true)).toEqual(files);expect(aurenFiles(files,true,undefined)).toEqual(files);expect(aurenFiles(files,false,false)).toEqual(files);
 });
 it('follows current search steps and preserves query and source access in the single indicator', () => {
  const queries={action:'web_search_queries_generated',queries:['pergunta sintética']};
  const searching={action:'web_search',description:'Consultando fontes públicas',done:false};
  const sources={action:'web_search',description:'Pesquisa concluída',urls:['https://example.org'],done:true};
  expect(aurenActivity([queries]).status).toBe(queries);
  expect(aurenActivity([queries,searching])).toMatchObject({phase:'searching',status:searching});
  const result=aurenActivity([queries,searching,sources]);
  expect(result.phase).toBe('organizing');expect(result.status.urls).toEqual(sources.urls);
  expect(result.status.description).toContain('Organizando');expect(sources.description).toBe('Pesquisa concluída');
  expect(aurenActivity([sources,searching]).phase).toBe('searching');
  expect(aurenActivity([sources],true)).toEqual({phase:'streaming',description:'',status:null});
 });
 it('combines image stage and actual queue metrics without a second status', () => {
  const result=aurenActivity([{action:'image_generation',state:'queued',queue_position:2}],false,9);
  expect(result).toEqual({phase:'image',status:null,description:'Aguardando a geração… · Tempo decorrido: 9 s · Posição na fila: 2'});
  expect(result.description).not.toContain('Estimativa');
  expect(aurenActivity([{action:'image_generation',done:true}]).description).toBe('Finalizando a imagem…');
 });
 it('uses the ordinary waiting animation when there is no visible progress', () => {
  expect(aurenActivity([{hidden:true,action:'auren_details'}])).toEqual({phase:'waiting',description:'',status:null});
 });
});
