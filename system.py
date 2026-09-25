import json # Import json module for data serialization
import csv # Import csv module for report generation
import os # Import os module for file path operations
from models import Student, Company, PlacementDrive, Interview, JobOffer, Admin # Import data models
from utils import * # Import custom exceptions, decorators, and utilities

class CampusPlacementSystem: # Main class to manage the placement system
    # Class Attribute
    total_placements_institution_wide = 0 # Track total placements across the institution

    def __init__(self): # Constructor to initialize the system state
        self.students = {} # Dictionary to store student objects with student_id as key
        self.companies = {} # Dictionary to store company objects with company_id as key
        self.admins = {} # Dictionary to store admin objects with admin_id as key
        self.drives = [] # List to store all placement drive records
        self.interviews = [] # List to store all scheduled interview objects
        self.interview_schedules = [] # List of tuples to store fixed schedules
        self.offers = [] # List to store job offer objects
        self.reports = [] # List to store generated report metadata
        
        # Define paths relative to this script directory for deployment environments
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_file = os.path.join(self.base_dir, 'data.json')
        self.report_file = os.path.join(self.base_dir, 'student_report.csv')

    @log_action("Student Registration") # Decorator to log the registration process
    def register_student(self, student_data): # Method to add a new student
        student_id = student_data.get("student_id") # Extract student ID from data
        if student_id in self.students: # Check for existing registration
            raise DuplicateRegistration(f"Student ID {student_id} already exists.") # Raise error if duplicate
        
        try: # Validate CGPA input
            cgpa = float(student_data.get("cgpa", 0.0)) # Convert CGPA to float
            if cgpa < 0 or cgpa > 10.0: # Check valid range
                raise InvalidCGPAEntry("CGPA must be between 0 and 10.") # Raise error for out of range
        except ValueError: # Handle non-numeric CGPA
            raise InvalidCGPAEntry("Invalid CGPA format.") # Raise error for bad format

        student = Student(**student_data) # Instantiate Student object using unpacked dictionary
        self.students[student_id] = student # Store student in the dictionary
        print(f"Successfully registered student: {student.name}") # Confirm registration

    def register_company(self, company_data): # Method to add a new company
        company_id = company_data.get("company_id") # Extract company ID
        if company_id in self.companies: # Check for existing registration
            raise DuplicateRegistration(f"Company ID {company_id} already exists.") # Raise error if duplicate
        
        company = Company(**company_data) # Instantiate Company object
        self.companies[company_id] = company # Store company in the dictionary
        print(f"Successfully registered company: {company.company_name}") # Confirm registration

    def update_company(self, company_id, company_data):
        if company_id not in self.companies:
            raise InvalidCompanyID(f"Company ID {company_id} not found.")
        company = self.companies[company_id]
        company.update_company(
            company_name=company_data.get('company_name', company.company_name),
            package=float(company_data.get('package', company.package)),
            eligibility_cgpa=float(company_data.get('eligibility_cgpa', company.eligibility_cgpa)),
            job_role=company_data.get('job_role', company.job_role),
        )

    @log_action("Admin Registration")
    def register_admin(self, admin_data):
        admin_id = admin_data.get("admin_id")
        username = admin_data.get("username")
        if admin_id in self.admins:
            raise DuplicateRegistration(f"Admin ID {admin_id} already exists.")
        if any(admin.username == username for admin in self.admins.values()):
            raise DuplicateRegistration(f"Username '{username}' already exists.")

        admin = Admin(**admin_data)
        self.admins[admin_id] = admin
        print(f"Successfully registered admin: {admin.name}")

    @log_action("Drive Creation") # Decorator to log drive creation
    def create_drive(self, drive_data): # Method to initiate a placement drive
        company_id = drive_data.get("company") # Extract company ID associated with drive
        if company_id not in self.companies: # Validate company existence
            raise InvalidCompanyID(f"Company ID {company_id} not found.") # Raise error if missing
        
        drive = PlacementDrive(**drive_data) # Instantiate PlacementDrive object
        self.drives.append(drive) # Add drive to the system list
        print(f"Successfully created drive for {self.companies[company_id].company_name}") # Confirm creation

    def apply_for_drive(self, student_id, drive_id):
        if student_id not in self.students:
            raise InvalidStudentID(f"Student ID {student_id} not found.")
        drive = next((item for item in self.drives if item.drive_id == drive_id), None)
        if drive is None:
            raise ValueError(f"Drive ID {drive_id} not found.")
        self.check_eligibility(student_id, drive.company)
        drive.register_students(student_id)

    def apply_for_placement(self, student_id, company_id):
        if student_id not in self.students:
            raise InvalidStudentID(f"Student ID {student_id} not found.")
        if company_id not in self.companies:
            raise InvalidCompanyID(f"Company ID {company_id} not found.")
        self.check_eligibility(student_id, company_id)
        student = self.students[student_id]
        if company_id not in student.applied_companies:
            student.applied_companies.append(company_id)
        student.application_statuses.setdefault(company_id, "Applied")

    def update_company_application(self, student_id, company_id, status):
        if student_id not in self.students:
            raise InvalidStudentID(f"Student ID {student_id} not found.")
        if company_id not in self.companies:
            raise InvalidCompanyID(f"Company ID {company_id} not found.")
        if company_id not in self.students[student_id].applied_companies:
            raise ValueError("This student has not applied to the company.")
        self.students[student_id].application_statuses[company_id] = status

    def update_drive_application(self, drive_id, student_id, status):
        if student_id not in self.students:
            raise InvalidStudentID(f"Student ID {student_id} not found.")
        drive = next((item for item in self.drives if item.drive_id == drive_id), None)
        if drive is None:
            raise ValueError(f"Drive ID {drive_id} not found.")
        if student_id not in drive.eligible_students:
            raise ValueError("This student has not applied to the drive.")
        drive.update_application_status(student_id, status)

    def check_eligibility(self, student_id, company_id): # Method to verify student eligibility
        if student_id not in self.students: # Validate student existence
            raise InvalidStudentID(f"Student ID {student_id} not found.") # Raise error if missing
        if company_id not in self.companies: # Validate company existence
            raise InvalidCompanyID(f"Company ID {company_id} not found.") # Raise error if missing
            
        student = self.students[student_id] # Retrieve student object
        company = self.companies[company_id] # Retrieve company object
        
        if Utils.check_eligibility(student.cgpa, company.eligibility_cgpa): # Use utility to compare CGPA
            return True # Return True if eligible
        else: # If criteria not met
            raise StudentNotEligible(f"Student {student.name} is not eligible for {company.company_name} (Requires {company.eligibility_cgpa} CGPA, has {student.cgpa})") # Raise eligibility error

    def schedule_interviews(self, interview_data): # Method to record an interview session
        student_id = interview_data.get("student") # Extract student ID
        company_id = interview_data.get("company") # Extract company ID
        
        if student_id not in self.students: # Validate student
            raise InvalidStudentID(f"Student ID {student_id} not found.") # Raise error if missing
        if company_id not in self.companies: # Validate company
            raise InvalidCompanyID(f"Company ID {company_id} not found.") # Raise error if missing
            
        interview = Interview(**interview_data) # Instantiate Interview object
        self.interviews.append(interview) # Add to system interviews list
        print(f"Scheduled interview for Student {student_id} with Company {company_id}") # Confirm scheduling

    def update_interview(self, interview_id, interview_data):
        interview = next((item for item in self.interviews if item.interview_id == interview_id), None)
        if interview is None:
            raise ValueError(f"Interview ID {interview_id} not found.")
        student_id = interview_data.get('student', interview.student)
        company_id = interview_data.get('company', interview.company)
        if student_id not in self.students:
            raise InvalidStudentID(f"Student ID {student_id} not found.")
        if company_id not in self.companies:
            raise InvalidCompanyID(f"Company ID {company_id} not found.")
        interview.student = student_id
        interview.company = company_id
        interview.interview_date = interview_data.get('interview_date', interview.interview_date)
        interview.status = interview_data.get('status', interview.status)

    def delete_interview(self, interview_id):
        original_count = len(self.interviews)
        self.interviews = [item for item in self.interviews if item.interview_id != interview_id]
        if len(self.interviews) == original_count:
            raise ValueError(f"Interview ID {interview_id} not found.")

    @log_action("Offer Generation") # Decorator to log offer generation
    def generate_offer(self, offer_data): # Method to issue a job offer
        student_id = offer_data.get("student") # Extract student ID
        company_id = offer_data.get("company") # Extract company ID
        
        if student_id not in self.students: # Validate student
            raise InvalidStudentID(f"Student ID {student_id} not found.") # Raise error if missing
        if company_id not in self.companies: # Validate company
            raise InvalidCompanyID(f"Company ID {company_id} not found.") # Raise error if missing
            
        offer = JobOffer(**offer_data) # Instantiate JobOffer object
        self.offers.append(offer) # Add to system offers list
        
        self.students[student_id].placement_status = "Placed" # Update student's status to Placed
        CampusPlacementSystem.increment_placements() # Increment the global placement counter
            
        print(f"Generated offer for Student {student_id}") # Confirm offer generation

    @classmethod # Class method to modify class-level attribute
    def increment_placements(cls): # Method to increase placement count
        cls.total_placements_institution_wide += 1 # Increment the static counter

    @classmethod # Class method to access class-level attribute
    def generate_institution_wide_stats(cls): # Method to get total placement count
        return f"Total Institutional Placements: {cls.total_placements_institution_wide}" # Return formatted string

    @log_action("Report Generation") # Decorator to log report generation
    def generate_reports(self): # Method to export student data to CSV
        def report_generator(): # Inner generator function for memory efficiency
            for student in self.students.values(): # Iterate through all students
                yield student.to_dict() # Yield student data as dictionary
                
        with open(self.report_file, 'w', newline='') as csvfile: # Open CSV file for writing
            fieldnames = ['student_id', 'name', 'branch', 'cgpa', 'placement_status'] # Define CSV columns
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore') # Initialize CSV writer
            writer.writeheader() # Write the column headers
            for record in report_generator(): # Iterate through the generator
                writer.writerow(record) # Write each student record to CSV
        print(f"Generated {self.report_file}") # Notify user of successful CSV export

    def save_data(self): # Method to persist all system data to a JSON file
        data = { # Create a dictionary structure to hold all system objects
            "students": {k: v.to_dict() for k, v in self.students.items()}, # Convert student objects to dictionaries
            "companies": {k: v.to_dict() for k, v in self.companies.items()}, # Convert company objects to dictionaries
            "admins": {k: v.to_dict() for k, v in self.admins.items()},
            "drives": [d.to_dict() for d in self.drives], # Convert drive objects to list of dicts
            "interviews": [i.to_dict() for i in self.interviews], # Convert interview objects to list of dicts
            "offers": [o.to_dict() for o in self.offers] # Convert offer objects to list of dicts
        }
        with open(self.data_file, 'w') as f: # Open JSON file for writing
            json.dump(data, f, indent=4) # Write serialized data with indentation
        print(f"Data saved successfully to {self.data_file}.") # Confirm data save

    def load_data(self): # Method to load system data from JSON file
        if not os.path.exists(self.data_file): # Check if data file exists
            print("No saved data found.") # Inform user if file is missing
            return # Exit method
            
        try: # Start error handling for file reading
            with open(self.data_file, 'r') as f: # Open JSON file for reading
                data = json.load(f) # Parse JSON data into dictionary
                
            self.students = {k: Student.from_dict(v) for k, v in data.get("students", {}).items()} # Reconstruct student objects
            self.companies = {k: Company.from_dict(v) for k, v in data.get("companies", {}).items()} # Reconstruct company objects
            self.admins = {k: Admin.from_dict(v) for k, v in data.get("admins", {}).items()}
            self.drives = [PlacementDrive.from_dict(v) for v in data.get("drives", [])] # Reconstruct drive objects
            self.interviews = [Interview.from_dict(v) for v in data.get("interviews", [])] # Reconstruct interview objects
            self.offers = [JobOffer.from_dict(v) for v in data.get("offers", [])] # Reconstruct offer objects
            
            CampusPlacementSystem.total_placements_institution_wide = sum(1 for s in self.students.values() if s.placement_status == "Placed") # Recalculate global placement count
            print(f"Data loaded successfully from {self.data_file}.") # Confirm data load
        except Exception as e: # Catch any errors during loading
            print(f"Error loading data: {e}") # Print error message

    def search_student_recursive(self, student_ids, target_id, index=0): # Recursive function to find a student by ID
        if index >= len(student_ids): # Base case: index out of bounds
            return None # Student not found
        if student_ids[index] == target_id: # Base case: ID matches
            return self.students[target_id] # Return the student object
        return self.search_student_recursive(student_ids, target_id, index + 1) # Recursive call with next index
        
    def get_students_sorted_by_cgpa(self): # Method to get students sorted by performance
        return sorted(self.students.values(), key=lambda s: s.cgpa, reverse=True) # Return list sorted by CGPA descending

    def get_admins(self):
        return sorted(self.admins.values(), key=lambda a: a.name.lower())
        
    def get_companies_sorted_by_package(self): # Method to get companies sorted by salary
        return sorted(self.companies.values(), key=lambda c: c.package, reverse=True) # Return list sorted by package descending
        
    def get_eligible_students(self, min_cgpa): # Method to filter students by CGPA
        return [s for s in self.students.values() if s.cgpa >= min_cgpa] # Return list of students meeting criteria using list comprehension
