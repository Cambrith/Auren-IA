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

    async def test_video_requires_model_support(self):
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
        with self.assertRaises(HTTPException):
            await prepare_attachments(form, model, SimpleNamespace(id='user'))
        model['cavren']['capabilities']['video'] = True
        await prepare_attachments(form, model, SimpleNamespace(id='user'))
        self.assertEqual(form['messages'][0]['content'][-1]['type'], 'input_video')
        self.assertEqual(form['files'], [])

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
