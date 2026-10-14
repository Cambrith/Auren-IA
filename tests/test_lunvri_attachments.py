import base64
from io import BytesIO
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
import zipfile
import os
import tempfile
from pathlib import Path

_data = tempfile.TemporaryDirectory()
os.environ['DATA_DIR'] = _data.name
os.environ['STATIC_DIR'] = str(Path(_data.name) / 'static')
os.environ['WEBUI_SECRET_KEY'] = 'lunvri-test-only-not-a-production-secret'
os.environ['OFFLINE_MODE'] = 'True'

from fastapi import HTTPException
from open_webui.utils.lunvri_attachments import extract_document, prepare_attachments


class AttachmentTests(unittest.IsolatedAsyncioTestCase):
    def test_text_and_word_are_extracted_without_embeddings(self):
        self.assertEqual(extract_document(b'Conteudo local', 'teste.txt', 'text/plain'), 'Conteudo local')
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr(
                'word/document.xml',
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Documento Word</w:t></w:r></w:p></w:document>',
            )
        self.assertIn('Documento Word', extract_document(buffer.getvalue(), 'teste.docx', 'application/octet-stream'))

    async def test_video_is_prepared_before_the_bridge_selects_a_compatible_model(self):
        file = {
            'lunvri_native': True,
            'url': 'data:video/mp4;base64,' + base64.b64encode(b'video').decode(),
            'name': 'teste.mp4',
        }
        form = {
            'model': 'cavren:gemini:test',
            'messages': [{'role': 'user', 'content': 'Analise', 'files': [file]}],
            'files': [file],
        }
        model = {'cavren': {'provider': 'gemini', 'capabilities': {'video': False}}}
        await prepare_attachments(form, model, SimpleNamespace(id='user'))
        self.assertEqual(form['messages'][0]['content'][-1]['type'], 'input_video')
        self.assertEqual(form['files'], [])

    async def test_pdf_is_kept_native_even_when_selected_model_is_text_only(self):
        file={'lunvri_native':True,'url':'data:application/pdf;base64,'+base64.b64encode(b'%PDF-synthetic').decode(),'name':'scan.pdf'}
        form={'model':'cavren:groq:openai/gpt-oss-120b','messages':[{'role':'user','content':'Leia','files':[file]}]}
        await prepare_attachments(form, {'cavren':{'capabilities':{}}}, SimpleNamespace(id='user'))
        self.assertEqual(form['messages'][0]['content'][-1]['type'],'input_file')
        self.assertEqual(base64.b64decode(form['messages'][0]['content'][-1]['input_file']['data']),b'%PDF-synthetic')

    async def test_owned_image_and_audio_are_not_blocked_by_selected_text_model(self):
        for mime,name,kind in [('image/png','diagram.png','image_url'),('audio/mpeg','recording.mp3','input_audio')]:
            file={'lunvri_native':True,'url':f'data:{mime};base64,'+base64.b64encode(b'synthetic').decode(),'name':name}
            form={'model':'cavren:groq:openai/gpt-oss-20b','messages':[{'role':'user','content':'Analise','files':[file]}]}
            await prepare_attachments(form, {'cavren':{'capabilities':{}}}, SimpleNamespace(id='user'))
            self.assertEqual(form['messages'][0]['content'][-1]['type'],kind)

    def test_presentation_open_document_and_code_are_extracted_as_untrusted_text(self):
        samples=[('slides.pptx','ppt/slides/slide1.xml','<a:p xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:r><a:t>ALFA-837</a:t></a:r></a:p>'),
                 ('notes.odt','content.xml','<text:p xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">ALFA-837</text:p>')]
        for name,entry,xml in samples:
            buffer=BytesIO()
            with zipfile.ZipFile(buffer,'w') as archive:archive.writestr(entry,xml)
            extracted=extract_document(buffer.getvalue(),name,'application/octet-stream')
            self.assertIn('ALFA-837',extracted);self.assertIn('layout',extracted)
        self.assertEqual(extract_document(b'SELECT 7;', 'query.sql','application/octet-stream'),'SELECT 7;')

    async def test_foreign_file_is_not_read(self):
        file = {'id': 'foreign', 'url': 'foreign', 'lunvri_native': True, 'name': 'secret.txt'}
        form = {'model': 'cavren:auto', 'messages': [{'role': 'user', 'content': 'Analise', 'files': [file]}]}
        with patch(
            'open_webui.utils.lunvri_attachments.Files.get_file_by_id',
            new=AsyncMock(return_value=SimpleNamespace(user_id='other', path='/private')),
        ):
            with self.assertRaises(HTTPException) as error:
                await prepare_attachments(form, {}, SimpleNamespace(id='user'))
        self.assertEqual(error.exception.status_code, 403)


if __name__ == '__main__':
    unittest.main()
