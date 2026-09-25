import functools # Import functools to use wraps for preserving metadata in decorators

# Custom Exceptions
class InvalidStudentID(Exception): # Exception raised when a student ID is not found in the system
    pass

class InvalidCompanyID(Exception): # Exception raised when a company ID is not found in the system
    pass

class StudentNotEligible(Exception): # Exception raised when a student does not meet company criteria
    pass

class DuplicateRegistration(Exception): # Exception raised when trying to register an existing ID
    pass

class InvalidCGPAEntry(Exception): # Exception raised for out-of-range or non-numeric CGPA values
    pass

class FileNotFoundError(Exception): # Exception raised when a required data file is missing
    pass

class IncorrectUserInput(Exception): # Exception raised for invalid menu choices or inputs
    pass


# Decorators
def log_action(action_name): # Higher-order function that takes the name of the action to log
    def decorator(func): # The actual decorator function
        @functools.wraps(func) # Preserves the original function's name and docstring
        def wrapper(*args, **kwargs): # Wrapper function that adds logging behavior
            print(f"[LOG] Action '{action_name}' started.") # Log the start of the operation
            result = func(*args, **kwargs) # Execute the original function
            print(f"[LOG] Action '{action_name}' completed.") # Log the completion of the operation
            return result # Return the result of the original function
        return wrapper # Return the wrapper to replace the original function
    return decorator # Return the decorator


# Utilities
class Utils: # Utility class containing helper methods
    @staticmethod # Static method as it doesn't require access to class or instance state
    def check_eligibility(student_cgpa, company_cgpa): # Compares student CGPA against requirement
        return float(student_cgpa) >= float(company_cgpa) # Returns True if eligible, else False
        
    @staticmethod # Static method for mathematical calculation
    def calculate_average_package(packages): # Calculates the mean of a list of salary packages
        if not packages: # Check if the list is empty to avoid division by zero
            return 0.0 # Return zero if no packages exist
        return sum(packages) / len(packages) # Return the average value
