import unittest
from io import BytesIO
from unittest.mock import patch

from app import app, cps
from models import Company, Student


def make_text_pdf(text):
    stream = f"BT /F1 12 Tf 72 72 Td ({text}) Tj ET".encode('ascii')
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
    ]
    document = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_id, content in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{object_id} 0 obj\n".encode() + content + b"\nendobj\n")

    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode())
    document.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    )
    return bytes(document)


class StudentProfileWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.original_students = cps.students
        self.original_companies = cps.companies
        self.original_interviews = cps.interviews
        self.student = Student(
            person_id='P-1', name='Test Student', email='student@example.com',
            contact_number='1234567890', student_id='S-1', branch='CSE', cgpa=8.0,
        )
        self.company = Company('C-1', 'DataWorks', 8.0, 6.0, 'Python Developer')
        self.java_company = Company('C-2', 'CodeCraft', 9.0, 6.0, 'Java Developer')
        self.spanish_company = Company('C-3', 'LangBridge', 6.0, 6.0, 'Spanish Language Specialist')
        cps.students = {'S-1': self.student}
        cps.companies = {
            'C-1': self.company,
            'C-2': self.java_company,
            'C-3': self.spanish_company,
        }
        cps.interviews = []
        self.addCleanup(setattr, cps, 'students', self.original_students)
        self.addCleanup(setattr, cps, 'companies', self.original_companies)
        self.addCleanup(setattr, cps, 'interviews', self.original_interviews)
        save_patch = patch.object(cps, 'save_data')
        save_patch.start()
        self.addCleanup(save_patch.stop)

        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session.update(role='student', user_id='S-1')

    def test_pdf_resume_suggests_company_and_student_can_apply(self):
        response = self.client.post(
            '/api/students/profile',
            data={
                'skills': 'SQL',
                'languages': 'English, Odia',
                'resume': (BytesIO(make_text_pdf('Python backend engineer')), 'resume.pdf'),
            },
            content_type='multipart/form-data',
        )

        self.assertEqual(response.status_code, 200)
        profile = response.get_json()['student']
        self.assertIn('Python', profile['resume_text'])
        self.assertEqual(set(profile['languages']), {'English', 'Odia'})
        self.assertEqual(profile['suggested_companies'][0]['company_id'], 'C-1')

        application = self.client.post('/api/companies/C-1/apply', json={})
        self.assertEqual(application.status_code, 200)
        refreshed_profile = self.client.get('/api/auth/me').get_json()['user']
        self.assertTrue(refreshed_profile['suggested_companies'][0]['has_applied'])

        update = self.client.post('/api/students/profile', json={
            'skills': 'Java',
            'languages': 'Spanish',
        })
        self.assertEqual(update.status_code, 200)
        updated_profile = update.get_json()['student']
        self.assertEqual(updated_profile['skills'], ['Java'])
        self.assertEqual(updated_profile['languages'], ['Spanish'])
        self.assertEqual(
            {item['company_id'] for item in updated_profile['suggested_companies']},
            {'C-1', 'C-2', 'C-3'},
        )
        saved_profile = self.client.get('/api/auth/me').get_json()['user']
        self.assertEqual(saved_profile['skills'], ['Java'])
        self.assertEqual(saved_profile['resume_name'], 'resume.pdf')

        resume_update = self.client.post(
            '/api/students/profile',
            data={
                'skills': 'Java',
                'languages': 'Spanish',
                'resume': (BytesIO(make_text_pdf('Java')), 'updated.pdf'),
            },
            content_type='multipart/form-data',
        )
        self.assertEqual(resume_update.status_code, 200)
        replaced_profile = resume_update.get_json()['student']
        self.assertEqual(
            {item['company_id'] for item in replaced_profile['suggested_companies']},
            {'C-2', 'C-3'},
        )
        self.assertEqual(replaced_profile['resume_name'], 'updated.pdf')
        self.assertNotIn('Python', replaced_profile['resume_text'])

    def test_student_eligibility_uses_logged_in_student(self):
        eligible = self.client.post('/api/eligibility', json={'company_id': 'C-1'})
        self.assertEqual(eligible.status_code, 200)
        self.assertTrue(eligible.get_json()['eligible'])

        self.student.cgpa = 5.99
        ineligible = self.client.post('/api/eligibility', json={'company_id': 'C-1'})
        self.assertEqual(ineligible.status_code, 200)
        self.assertFalse(ineligible.get_json()['eligible'])
        self.assertIn('Requires 6.0 CGPA', ineligible.get_json()['message'])

        self.student.cgpa = 8.0
        with self.client.session_transaction() as session:
            session['role'] = 'admin'
        admin_check = self.client.post('/api/eligibility', json={
            'student_id': 'S-1',
            'company_id': 'C-1',
        })
        self.assertEqual(admin_check.status_code, 200)
        self.assertTrue(admin_check.get_json()['eligible'])

    def test_interview_saves_team_member_and_displays_resolved_names(self):
        with self.client.session_transaction() as session:
            session['role'] = 'admin'

        scheduled = self.client.post('/api/interviews', json={
            'interview_id': 'I-1',
            'student': 'S-1',
            'company': 'C-1',
            'interview_date': '2026-10-01',
            'team_member_name': 'Placement Team Member',
        })
        self.assertEqual(scheduled.status_code, 200)

        interviews = self.client.get('/api/interviews').get_json()
        self.assertEqual(interviews[0]['student_name'], 'Test Student')
        self.assertEqual(interviews[0]['company_name'], 'DataWorks')
        self.assertEqual(interviews[0]['team_member_name'], 'Placement Team Member')

    def test_rejects_unsupported_resume_file(self):
        response = self.client.post(
            '/api/students/profile',
            data={'resume': (BytesIO(b'not a supported resume'), 'resume.docx')},
            content_type='multipart/form-data',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('PDF or TXT', response.get_json()['message'])


if __name__ == '__main__':
    unittest.main()