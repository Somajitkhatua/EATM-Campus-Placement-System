"""
==============================================
  Flask REST API - Campus Placement System
==============================================
This file creates a web server that connects 
the frontend (HTML/CSS/JS) to the existing 
Python backend (system.py, models.py, utils.py).

Each API endpoint maps to a CampusPlacementSystem method.
"""

from functools import wraps
from io import BytesIO
from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from pypdf import PdfReader
from system import CampusPlacementSystem
from utils import (
    InvalidStudentID, InvalidCompanyID,
    StudentNotEligible, DuplicateRegistration,
    InvalidCGPAEntry, Utils
)

# ── Initialize Flask App ──────────────────────
app = Flask(__name__)
app.secret_key = 'niet-placement-system-local-secret'

APPLICATION_STATUSES = ('Applied', 'Screening', 'Interview', 'Selected', 'Rejected', 'Withdrawn')
MAX_RESUME_BYTES = 5 * 1024 * 1024

# Create a single instance of the placement system
# This is shared across all API requests
cps = CampusPlacementSystem()
cps.load_data()  # Load any previously saved data on startup


def current_role():
    return session.get('role')


def auth_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_role():
            return jsonify({"success": False, "message": "Please log in first."}), 401
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_role() != 'admin':
            return jsonify({"success": False, "message": "Admin access required."}), 403
        return view(*args, **kwargs)
    return wrapped


def student_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_role() != 'student':
            return jsonify({"success": False, "message": "Student access required."}), 403
        return view(*args, **kwargs)
    return wrapped


def student_or_admin(view):
    return auth_required(view)


def public_student(student):
    data = student.to_dict()
    data.pop('password', None)
    data['suggested_companies'] = suggest_companies_for_student(student)
    return data


def public_admin(admin):
    data = admin.to_dict()
    data.pop('password', None)
    return data


def public_drive(drive, include_applicants=False, student_id=None):
    data = drive.to_dict()
    if include_applicants:
        data['applicants'] = [
            {
                **public_student(cps.students[applicant_id]),
                'status': drive.application_statuses.get(applicant_id, 'Applied'),
            }
            for applicant_id in drive.eligible_students
            if applicant_id in cps.students
        ]
    else:
        data.pop('eligible_students', None)
        data.pop('application_statuses', None)
        data['has_applied'] = student_id in drive.eligible_students
        data['application_status'] = drive.application_statuses.get(student_id) if data['has_applied'] else None
    return data


def password_matches(stored_password, supplied_password):
    if not stored_password:
        return False
    if stored_password.startswith(('scrypt:', 'pbkdf2:')):
        return check_password_hash(stored_password, supplied_password)
    return stored_password == supplied_password


def normalize_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(',') if item.strip()]
    if isinstance(value, (list, set, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def extract_resume_text(uploaded_file):
    filename = secure_filename(uploaded_file.filename or '')
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if extension not in ('pdf', 'txt'):
        raise ValueError('Upload a PDF or TXT resume.')

    content = uploaded_file.read(MAX_RESUME_BYTES + 1)
    if len(content) > MAX_RESUME_BYTES:
        raise ValueError('Resume must be 5 MB or smaller.')

    if extension == 'txt':
        resume_text = content.decode('utf-8-sig', errors='replace')
    else:
        try:
            reader = PdfReader(BytesIO(content), strict=False)
            if reader.is_encrypted and not reader.decrypt(''):
                raise ValueError('This PDF is password-protected.')
            resume_text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        except ValueError:
            raise
        except Exception as error:
            raise ValueError('Unable to read this PDF. Upload a text-based PDF or TXT resume.') from error
        if not resume_text.strip():
            raise ValueError('No readable text was found in this PDF. Upload a text-based PDF or TXT resume.')

    if not resume_text.strip():
        raise ValueError('The resume file is empty.')
    return filename, resume_text[:100_000]


def suggest_companies_for_student(student):
    keywords = set()
    keywords.update(normalize_list(student.skills))
    keywords.update(normalize_list(student.languages))
    if getattr(student, 'resume_text', ''):
        keywords.update({word.lower() for word in str(student.resume_text).replace(',', ' ').replace('.', ' ').split() if len(word) > 3})
    keywords = {k.lower() for k in keywords}

    suggestions = []
    for company in cps.companies.values():
        text = f"{company.company_name} {company.job_role}".lower()
        if not keywords or any(keyword in text for keyword in keywords):
            suggestions.append({
                "company_id": company.company_id,
                "company_name": company.company_name,
                "job_role": company.job_role,
                "package": company.package,
                "eligibility_cgpa": company.eligibility_cgpa,
                "eligible": student.cgpa >= company.eligibility_cgpa,
                "has_applied": company.company_id in student.applied_companies,
                "application_status": student.application_statuses.get(company.company_id),
            })
    return suggestions[:5]


@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    role = current_role()
    if role == 'admin':
        admin = cps.admins.get(session.get('user_id'))
        return jsonify({"authenticated": True, "role": role, "user": public_admin(admin) if admin else None})
    if role == 'student':
        student = cps.students.get(session.get('user_id'))
        return jsonify({"authenticated": True, "role": role, "user": public_student(student) if student else None})
    return jsonify({"authenticated": False})


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    role = data.get('role')
    password = data.get('password', '')
    if role == 'admin':
        username = data.get('username', '').strip()
        account = next((a for a in cps.admins.values() if a.username == username), None)
        if not account or not password_matches(account.password, password):
            return jsonify({"success": False, "message": "Invalid admin username or password."}), 401
        session.clear()
        session.update(role='admin', user_id=account.admin_id)
        return jsonify({"success": True, "role": role, "user": public_admin(account)})
    if role == 'student':
        student_id = data.get('student_id', '').strip()
        account = cps.students.get(student_id)
        if not account or not password_matches(account.password, password):
            return jsonify({"success": False, "message": "Invalid student ID or password."}), 401
        session.clear()
        session.update(role='student', user_id=account.student_id)
        return jsonify({"success": True, "role": role, "user": public_student(account)})
    return jsonify({"success": False, "message": "Choose an account type."}), 400


@app.route('/api/auth/register/admin', methods=['POST'])
def auth_register_admin():
    data = request.get_json() or {}
    required = ['person_id', 'name', 'email', 'contact_number', 'admin_id', 'username', 'password']
    if any(not data.get(field) for field in required):
        return jsonify({"success": False, "message": "Complete all admin registration fields."}), 400
    data['password'] = generate_password_hash(data.get('password', ''))
    try:
        cps.register_admin(data)
        cps.save_data()
        return jsonify({"success": True, "message": "Admin account created. You can now log in."})
    except DuplicateRegistration as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/auth/register/student', methods=['POST'])
def auth_register_student():
    data = request.get_json() or {}
    required = ['person_id', 'name', 'email', 'contact_number', 'student_id', 'branch', 'cgpa', 'password']
    if any(not data.get(field) for field in required):
        return jsonify({"success": False, "message": "Complete all student registration fields."}), 400
    data['password'] = generate_password_hash(data.get('password', ''))
    data['skills'] = normalize_list(data.get('skills'))
    data['languages'] = normalize_list(data.get('languages'))
    data['resume_name'] = data.get('resume_name', '')
    data['resume_text'] = data.get('resume_text', '')
    try:
        cps.register_student(data)
        cps.save_data()
        return jsonify({"success": True, "message": "Student account created. You can now log in."})
    except (DuplicateRegistration, InvalidCGPAEntry) as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})


# ══════════════════════════════════════════════
#  PAGE ROUTE - Serves the frontend
# ══════════════════════════════════════════════

@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('index.html')


# ══════════════════════════════════════════════
#  STUDENT API ENDPOINTS
# ══════════════════════════════════════════════

@app.route('/api/students', methods=['GET'])
@student_or_admin
def get_students():
    """Get all students sorted by CGPA (highest first)"""
    students = cps.get_students_sorted_by_cgpa()
    if current_role() == 'student':
        students = [student for student in students if student.student_id == session.get('user_id')]
    response = []
    for student in students:
        data = public_student(student)
        if current_role() == 'admin':
            data['applied_drives'] = [
                {
                    'drive_id': drive.drive_id,
                    'status': drive.application_statuses.get(student.student_id, 'Applied'),
                }
                for drive in cps.drives
                if student.student_id in drive.eligible_students
            ]
            data['applied_placements'] = [
                {
                    'company_id': company_id,
                    'company_name': cps.companies[company_id].company_name,
                    'status': student.application_statuses.get(company_id, 'Applied'),
                }
                for company_id in student.applied_companies
                if company_id in cps.companies
            ]
        response.append(data)
    return jsonify(response)


@app.route('/api/admins', methods=['GET'])
@admin_required
def get_admins():
    """Get all registered admins"""
    admins = cps.get_admins()
    return jsonify([public_admin(a) for a in admins])


@app.route('/api/admins', methods=['POST'])
@admin_required
def register_admin():
    """Register a new admin/placement coordinator"""
    try:
        data = request.get_json()
        cps.register_admin(data)
        cps.save_data()
        return jsonify({"success": True, "message": f"Admin '{data.get('name')}' registered!"})
    except (DuplicateRegistration,) as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/students', methods=['POST'])
@admin_required
def register_student():
    """Register a new student from JSON request body"""
    try:
        data = request.get_json()
        # Split comma-separated skills into a list
        if isinstance(data.get('skills'), str):
            data['skills'] = [s.strip() for s in data['skills'].split(',')]
        cps.register_student(data)
        cps.save_data()
        return jsonify({"success": True, "message": f"Student '{data.get('name')}' registered!"})
    except (DuplicateRegistration, InvalidCGPAEntry) as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/students/search/<student_id>', methods=['GET'])
@admin_required
def search_student(student_id):
    """Search for a student using recursive search algorithm"""
    student_ids = list(cps.students.keys())
    student = cps.search_student_recursive(student_ids, student_id)
    if student:
        return jsonify({"success": True, "student": student.to_dict()})
    return jsonify({"success": False, "message": "Student not found"}), 404


@app.route('/api/students/profile', methods=['POST'])
@student_required
def update_student_profile():
    data = request.form if request.mimetype == 'multipart/form-data' else (request.get_json(silent=True) or {})
    resume_file = request.files.get('resume') if request.mimetype == 'multipart/form-data' else None
    student = cps.students.get(session.get('user_id'))
    if not student:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    try:
        resume_name, resume_text = extract_resume_text(resume_file) if resume_file and resume_file.filename else (None, None)
    except ValueError as error:
        return jsonify({"success": False, "message": str(error)}), 400

    student.skills = set(normalize_list(data.get('skills', list(student.skills))))
    student.languages = set(normalize_list(data.get('languages', list(student.languages))))
    if resume_name is not None:
        student.resume_name = resume_name
        student.resume_text = resume_text
    elif data.get('resume_name') is not None:
        student.resume_name = str(data.get('resume_name', student.resume_name))
        student.resume_text = str(data.get('resume_text', student.resume_text))

    cps.save_data()
    return jsonify({
        "success": True,
        "message": "Profile and resume updated successfully.",
        "suggested_companies": suggest_companies_for_student(student),
        "student": public_student(student)
    })


# ══════════════════════════════════════
#  COMPANY API ENDPOINTS
# ══════════════════════════════════════════════

@app.route('/api/companies', methods=['GET'])
@student_or_admin
def get_companies():
    """Get all companies sorted by package (highest first)"""
    companies = cps.get_companies_sorted_by_package()
    response = []
    for company in companies:
        data = dict(company.to_dict())
        if current_role() == 'student':
            data['has_applied'] = company.company_id in cps.students[session.get('user_id')].applied_companies
        else:
            data['applicants'] = [
                {
                    **public_student(student),
                    'status': student.application_statuses.get(company.company_id, 'Applied'),
                }
                for student in cps.students.values()
                if company.company_id in student.applied_companies
            ]
        response.append(data)
    return jsonify(response)


@app.route('/api/companies', methods=['POST'])
@admin_required
def register_company():
    """Register a new recruiting company"""
    try:
        data = request.get_json()
        cps.register_company(data)
        cps.save_data()
        return jsonify({"success": True, "message": f"Company '{data.get('company_name')}' registered!"})
    except DuplicateRegistration as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/companies/<company_id>', methods=['PATCH'])
@admin_required
def edit_company(company_id):
    try:
        cps.update_company(company_id, request.get_json() or {})
        cps.save_data()
        return jsonify({"success": True, "message": "Company profile updated."})
    except (InvalidCompanyID, ValueError) as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/companies/<company_id>/apply', methods=['POST'])
@student_required
def apply_for_placement(company_id):
    try:
        cps.apply_for_placement(session.get('user_id'), company_id)
        cps.save_data()
        return jsonify({"success": True, "message": "Placement application submitted successfully."})
    except StudentNotEligible as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except (InvalidStudentID, InvalidCompanyID) as e:
        return jsonify({"success": False, "message": str(e)}), 404


@app.route('/api/companies/<company_id>/applications/<student_id>', methods=['PATCH'])
@admin_required
def update_company_application(company_id, student_id):
    status = (request.get_json() or {}).get('status')
    if status not in APPLICATION_STATUSES:
        return jsonify({"success": False, "message": "Invalid application status."}), 400
    try:
        cps.update_company_application(student_id, company_id, status)
        cps.save_data()
        return jsonify({"success": True, "message": "Company application status updated."})
    except (InvalidStudentID, InvalidCompanyID, ValueError) as e:
        return jsonify({"success": False, "message": str(e)}), 404


# ══════════════════════════════════════════════
#  PLACEMENT DRIVE API ENDPOINTS
# ══════════════════════════════════════════════

@app.route('/api/drives', methods=['GET'])
@student_or_admin
def get_drives():
    """Get all placement drives"""
    if current_role() == 'admin':
        return jsonify([public_drive(drive, include_applicants=True) for drive in cps.drives])
    return jsonify([public_drive(drive, student_id=session.get('user_id')) for drive in cps.drives])


@app.route('/api/drives', methods=['POST'])
@admin_required
def create_drive():
    """Create a new placement drive for a company"""
    try:
        data = request.get_json()
        cps.create_drive(data)
        cps.save_data()
        return jsonify({"success": True, "message": "Drive created successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/drives/<drive_id>/apply', methods=['POST'])
@student_required
def apply_for_drive(drive_id):
    try:
        cps.apply_for_drive(session.get('user_id'), drive_id)
        cps.save_data()
        return jsonify({"success": True, "message": "Application submitted successfully."})
    except (InvalidStudentID, ValueError) as e:
        return jsonify({"success": False, "message": str(e)}), 404


@app.route('/api/drives/<drive_id>/applications/<student_id>', methods=['PATCH'])
@admin_required
def update_drive_application(drive_id, student_id):
    status = (request.get_json() or {}).get('status')
    if status not in APPLICATION_STATUSES:
        return jsonify({"success": False, "message": "Invalid application status."}), 400
    try:
        cps.update_drive_application(drive_id, student_id, status)
        cps.save_data()
        return jsonify({"success": True, "message": "Drive application status updated."})
    except (InvalidStudentID, ValueError) as e:
        return jsonify({"success": False, "message": str(e)}), 404


# ══════════════════════════════════════════════
#  ELIGIBILITY CHECK API
# ══════════════════════════════════════════════

@app.route('/api/eligibility', methods=['POST'])
@student_or_admin
def check_eligibility():
    """Check if a student meets a company's CGPA requirement"""
    data = request.get_json(silent=True) or {}
    student_id = session.get('user_id') if current_role() == 'student' else data.get('student_id')
    company_id = data.get('company_id')
    if not student_id or not company_id:
        return jsonify({"eligible": False, "message": "Select a student and company to check eligibility."}), 400

    try:
        cps.check_eligibility(student_id, company_id)
        return jsonify({"eligible": True, "message": "Student is eligible!"})
    except StudentNotEligible as e:
        return jsonify({"eligible": False, "message": str(e)})
    except (InvalidStudentID, InvalidCompanyID) as e:
        return jsonify({"eligible": False, "message": str(e)}), 404


# ══════════════════════════════════════════════
#  INTERVIEW API ENDPOINTS
# ══════════════════════════════════════════════

@app.route('/api/interviews', methods=['GET'])
@student_or_admin
def get_interviews():
    """Get all scheduled interviews"""
    interviews = cps.interviews
    if current_role() == 'student':
        interviews = [i for i in interviews if i.student == session.get('user_id')]
    response = []
    for interview in interviews:
        data = interview.to_dict()
        data['student_name'] = cps.students.get(interview.student).name if interview.student in cps.students else interview.student
        data['company_name'] = cps.companies.get(interview.company).company_name if interview.company in cps.companies else interview.company
        response.append(data)
    return jsonify(response)


@app.route('/api/interviews', methods=['POST'])
@admin_required
def schedule_interview():
    """Schedule a new interview between student and company"""
    try:
        data = request.get_json(silent=True) or {}
        cps.schedule_interviews(data)
        cps.save_data()
        return jsonify({"success": True, "message": "Interview scheduled!"})
    except (InvalidStudentID, InvalidCompanyID) as e:
        return jsonify({"success": False, "message": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/interviews/<interview_id>', methods=['PATCH'])
@admin_required
def edit_interview(interview_id):
    try:
        cps.update_interview(interview_id, request.get_json() or {})
        cps.save_data()
        return jsonify({"success": True, "message": "Interview updated."})
    except (InvalidStudentID, InvalidCompanyID, ValueError) as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/interviews/<interview_id>', methods=['DELETE'])
@admin_required
def remove_interview(interview_id):
    try:
        cps.delete_interview(interview_id)
        cps.save_data()
        return jsonify({"success": True, "message": "Interview deleted."})
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 404


# ══════════════════════════════════════════════
#  JOB OFFER API ENDPOINTS
# ══════════════════════════════════════════════

@app.route('/api/offers', methods=['GET'])
@student_or_admin
def get_offers():
    """Get all job offers"""
    offers = cps.offers
    if current_role() == 'student':
        offers = [offer for offer in offers if offer.student == session.get('user_id')]
    return jsonify([o.to_dict() for o in offers])


@app.route('/api/offers', methods=['POST'])
@admin_required
def generate_offer():
    """Generate a job offer for a student"""
    try:
        data = request.get_json()
        cps.generate_offer(data)
        cps.save_data()
        return jsonify({"success": True, "message": "Job offer generated!"})
    except (InvalidStudentID, InvalidCompanyID) as e:
        return jsonify({"success": False, "message": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ══════════════════════════════════════════════
#  STATISTICS API
# ══════════════════════════════════════════════

@app.route('/api/stats', methods=['GET'])
@student_or_admin
def get_stats():
    """Calculate and return all placement statistics"""
    total_students = len(cps.students)
    total_companies = len(cps.companies)
    placed = len([s for s in cps.students.values() if s.placement_status == "Placed"])
    packages = [o.package for o in cps.offers]

    return jsonify({
        "total_students": total_students,
        "total_companies": total_companies,
        "placed_students": placed,
        "not_placed": total_students - placed,
        "placement_pct": round((placed / total_students * 100) if total_students > 0 else 0, 2),
        "total_drives": len(cps.drives),
        "total_interviews": len(cps.interviews),
        "total_offers": len(cps.offers),
        "highest_package": max(packages, default=0),
        "avg_package": round(Utils.calculate_average_package(packages), 2)
    })


# ══════════════════════════════════════════════
#  REPORT & DATA MANAGEMENT API
# ══════════════════════════════════════════════

@app.route('/api/reports', methods=['POST'])
@admin_required
def generate_report():
    """Generate a CSV report of all student data"""
    try:
        cps.generate_reports()
        return jsonify({"success": True, "message": "Report saved to student_report.csv"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/data/save', methods=['POST'])
@admin_required
def save_data():
    """Save all system data to data.json"""
    try:
        cps.save_data()
        return jsonify({"success": True, "message": "Data saved!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/data/load', methods=['POST'])
@admin_required
def load_data():
    """Reload data from data.json"""
    try:
        cps.load_data()
        return jsonify({"success": True, "message": "Data loaded!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ══════════════════════════════════════════════
#  START THE SERVER
# ══════════════════════════════════════════════

if __name__ == '__main__':
    print("\n=== Campus Placement Management System ===")
    print("    Open http://localhost:5000 in your browser\n")
    app.run(debug=True, port=5000)
