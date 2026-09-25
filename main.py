import sys # Import system-specific parameters and functions
from system import CampusPlacementSystem # Import the main system logic class
from utils import IncorrectUserInput, StudentNotEligible, Utils # Import custom exceptions and utility functions

def main(): # Define the main entry point of the application
    cps = CampusPlacementSystem() # Initialize the placement management system object
    cps.load_data() # Load existing data from storage files upon startup
    
    while True: # Start an infinite loop for the command-line interface
        print("\n" + "="*40) # Print a visual separator line
        print(" Campus Placement Management System ") # Print the system title
        print("="*40) # Print another visual separator line
        print("1. Student Management") # Option 1: Manage student records
        print("2. Company Management") # Option 2: Manage company records
        print("3. Placement Drive Management") # Option 3: Manage recruitment drives
        print("4. Eligibility Checking") # Option 4: Check if a student can apply for a company
        print("5. Interview Management") # Option 5: Schedule and track interviews
        print("6. Job Offer Management") # Option 6: Issue and track job offers
        print("7. Placement Statistics") # Option 7: View overall placement performance
        print("8. Report Generation") # Option 8: Generate text-based reports
        print("9. Save Data") # Option 9: Manually save current state to files
        print("10. Load Data") # Option 10: Manually reload data from files
        print("11. Exit") # Option 11: Close the application
        print("="*40) # Print a visual separator line
        
        choice = input("Enter your choice: ") # Prompt user for their menu selection
        
        try: # Start error handling block for user operations
            if choice == '1': # If user chooses Student Management
                print("\n--- Student Management ---") # Print sub-menu header
                print("1. Register Student") # Sub-option to add a new student
                print("2. View Students (Sorted by CGPA)") # Sub-option to list students by performance
                print("3. Search Student (Recursive)") # Sub-option to find a student using recursion
                sub_choice = input("Choice: ") # Get the sub-menu selection
                if sub_choice == '1': # Logic for registering a new student
                    person_id = input("Person ID: ") # Input unique personal identifier
                    name = input("Name: ") # Input student's full name
                    email = input("Email: ") # Input student's email address
                    phone = input("Phone: ") # Input student's contact number
                    student_id = input("Student ID: ") # Input unique academic student ID
                    branch = input("Branch: ") # Input academic department/branch
                    cgpa = input("CGPA: ") # Input current CGPA
                    skills = input("Skills (comma separated): ").split(",") # Input skills and convert to list
                    
                    data = { # Create a dictionary to hold student data
                        "person_id": person_id, "name": name, "email": email,
                        "contact_number": phone, "student_id": student_id,
                        "branch": branch, "cgpa": cgpa, "skills": [s.strip() for s in skills]
                    } # Clean whitespace from skills list
                    cps.register_student(data) # Call system method to save the student
                elif sub_choice == '2': # Logic for viewing sorted students
                    students = cps.get_students_sorted_by_cgpa() # Retrieve list of students sorted by CGPA
                    if not students: # Check if the list is empty
                        print("No students registered.") # Inform user if no data exists
                    for s in students: # Iterate through each student object
                        s.display_details() # Call the student's method to print their info
                elif sub_choice == '3': # Logic for searching a student
                    target_id = input("Enter Student ID to search: ") # Get the ID to look for
                    student_ids = list(cps.students.keys()) # Get a list of all registered student IDs
                    student = cps.search_student_recursive(student_ids, target_id) # Perform recursive search
                    if student: # If student was found
                        student.display_details() # Show found student's details
                    else: # If student was not found
                        print("Student not found.") # Inform the user
                        
            elif choice == '2': # If user chooses Company Management
                print("\n--- Company Management ---") # Print sub-menu header
                print("1. Register Company") # Sub-option to add a new company
                print("2. View Companies (Sorted by Package)") # Sub-option to list companies by salary
                sub_choice = input("Choice: ") # Get the sub-menu selection
                if sub_choice == '1': # Logic for registering a company
                    company_id = input("Company ID: ") # Input unique company identifier
                    name = input("Name: ") # Input company name
                    package = input("Package (LPA): ") # Input salary package offered
                    eligibility_cgpa = input("Eligibility CGPA: ") # Input minimum CGPA required
                    job_role = input("Job Role: ") # Input the designation offered
                    
                    data = { # Create a dictionary to hold company data
                        "company_id": company_id, "company_name": name, "package": package,
                        "eligibility_cgpa": eligibility_cgpa, "job_role": job_role
                    }
                    cps.register_company(data) # Call system method to save the company
                elif sub_choice == '2': # Logic for viewing sorted companies
                    companies = cps.get_companies_sorted_by_package() # Retrieve companies sorted by package
                    if not companies: # Check if the list is empty
                        print("No companies registered.") # Inform user if no data exists
                    for c in companies: # Iterate through each company object
                        c.display_details() # Call the company's method to print their info
                        
            elif choice == '3': # If user chooses Placement Drive Management
                print("\n--- Placement Drive Management ---") # Print section header
                drive_id = input("Drive ID: ") # Input unique drive identifier
                company_id = input("Company ID: ") # Input ID of the participating company
                date = input("Date (YYYY-MM-DD): ") # Input the scheduled date
                
                cps.create_drive({"drive_id": drive_id, "company": company_id, "drive_date": date}) # Create drive record
                
            elif choice == '4': # If user chooses Eligibility Checking
                print("\n--- Eligibility Checking ---") # Print section header
                student_id = input("Student ID: ") # Input ID of student to check
                company_id = input("Company ID: ") # Input ID of company to check against
                try: # Try to check eligibility
                    if cps.check_eligibility(student_id, company_id): # Call system eligibility logic
                        print("Student is eligible.") # Inform user if criteria met
                except StudentNotEligible as e: # Catch specific eligibility exception
                    print(e) # Print the reason for ineligibility
                    
            elif choice == '5': # If user chooses Interview Management
                print("\n--- Interview Management ---") # Print section header
                interview_id = input("Interview ID: ") # Input unique interview identifier
                student_id = input("Student ID: ") # Input ID of the candidate
                company_id = input("Company ID: ") # Input ID of the interviewing company
                date = input("Date (YYYY-MM-DD): ") # Input interview date
                
                cps.schedule_interviews({ # Call system method to record interview
                    "interview_id": interview_id, "student": student_id,
                    "company": company_id, "interview_date": date
                })
                
            elif choice == '6': # If user chooses Job Offer Management
                print("\n--- Job Offer Management ---") # Print section header
                offer_id = input("Offer ID: ") # Input unique offer identifier
                student_id = input("Student ID: ") # Input ID of the selected student
                company_id = input("Company ID: ") # Input ID of the hiring company
                package = input("Package Offered (LPA): ") # Input final package amount
                
                cps.generate_offer({ # Call system method to record the job offer
                    "offer_id": offer_id, "student": student_id,
                    "company": company_id, "package": package
                })
                
            elif choice == '7': # If user chooses Placement Statistics
                print("\n--- Placement Statistics ---") # Print section header
                print(cps.generate_institution_wide_stats()) # Print general stats from system
                
                # Calculate the number of students who have secured a job
                placed = len([s for s in cps.students.values() if s.placement_status == "Placed"]) # Count 'Placed' students
                total = len(cps.students) # Get total number of registered students
                # Calculate and display the placement percentage if students exist
                if total > 0: # Avoid division by zero
                    print(f"Placement Percentage: {(placed/total)*100:.2f}%") # Print formatted percentage
                else: # If no students are in the system
                    print("No students available to calculate percentage.") # Inform user
                
                if cps.offers: # Check if any offers have been generated
                    highest_package = max(o.package for o in cps.offers) # Find the maximum package value
                    avg_package = Utils.calculate_average_package([o.package for o in cps.offers]) # Calculate mean package
                    print(f"Highest Package: {highest_package} LPA") # Print highest package
                    print(f"Average Package: {avg_package:.2f} LPA") # Print average package
                else: # If no offers exist
                    print("No job offers available yet to calculate package statistics.") # Inform user
                    
            elif choice == '8': # If user chooses Report Generation
                print("\n--- Report Generation ---") # Print section header
                cps.generate_reports() # Call system method to export reports to files
                
            elif choice == '9': # If user chooses Save Data
                cps.save_data() # Manually trigger data persistence
                
            elif choice == '10': # If user chooses Load Data
                cps.load_data() # Manually trigger data reload from files
                
            elif choice == '11': # If user chooses Exit
                print("Exiting system. Saving data before exit...") # Inform user of shutdown process
                cps.save_data() # Ensure data is saved before closing
                print("Goodbye!") # Print exit message
                break # Break the while loop to end program
                
            else: # If input doesn't match any menu number
                raise IncorrectUserInput("Invalid choice. Please enter a number between 1 and 11.") # Raise custom error
                
        except Exception as e: # Catch-all for any errors during execution
            print(f"Error: {e}") # Print the error message to the user

if __name__ == "__main__": # Check if script is run directly
    main() # Execute the main function
