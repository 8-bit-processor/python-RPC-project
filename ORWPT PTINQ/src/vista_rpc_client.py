# -*- coding: utf-8 -*-
# This module provides a client for interacting with a VistA EMR system
# via the M-language RPC (Remote Procedure Call) broker.

# Import necessary standard Python libraries
import sys
import os
import datetime  # Used for generating timestamps, not strictly required for patient lookup but good practice.

# To handle running this script directly and ensure modules are found,
# we dynamically adjust the Python path.
# os.path.abspath(__file__) gets the absolute path to this file.
# os.path.dirname(...) gets the directory containing this file ('.../src').
# We get the parent of 'src' to find the project root ('.../patient_dfn_lookup').
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# We add this project root to Python's system path.
sys.path.append(project_root)

from vavista.rpc import connect, PLiteral  # Core components from the vavista library for RPC communication.

class VistaRpcClient:
    """
    Manages the connection to a VistA RPC Broker and provides methods
    for invoking RPCs relevant to patient lookups.

    This class is a simplified version tailored for the patient DFN lookup app.
    It handles the complexities of establishing a connection, logging in,
    and calling specific RPCs required to find a patient.
    """
    def __init__(self):
        """
        Initializes the VistaRpcClient.
        This special method is called when a new instance of the class is created.
        It sets up the initial state of the object.
        """
        # self.connection stores the active connection object returned by the vavista library.
        # It is initialized to None, indicating no connection has been made yet.
        self.connection = None

        # self.host stores the IP address or hostname of the VistA server.
        self.host = None

        # self.port stores the port number for the VistA RPC Broker service.
        self.port = None

        # self.access_code stores the user's VistA access code for authentication.
        self.access_code = None

        # self.verify_code stores the user's VistA verify code for authentication.
        self.verify_code = None

        # self.context stores the application context required by VistA to know
        # what kind of application is connecting. 'OR CPRS GUI CHART' is a
        # standard context that grants access to a wide range of clinical RPCs.
        self.context = None

    def connect_to_vista(self, host, port, access, verify, context="OR CPRS GUI CHART"):
        """
        Stores the connection parameters and attempts to log in to the VistA server.
        This is the main entry point for establishing a session.

        Args:
            host (str): The IP address or hostname of the VistA server (e.g., "127.0.0.1").
            port (int): The port number of the VistA RPC Broker (e.g., 9297).
            access (str): The user's VistA access code.
            verify (str): The user's VistA verify code.
            context (str): The application context for the VistA session.
                           Defaults to 'OR CPRS GUI CHART', which is standard for clinical applications.

        Returns:
            bool: True if the connection and login are successful, False otherwise.
        """
        # Store the provided connection details as attributes of the object.
        # This allows other methods in the class to access them without needing them passed as arguments again.
        self.host = host
        self.port = port
        self.access_code = access
        self.verify_code = verify
        self.context = context
        
        # Call the internal login method to perform the actual connection attempt.
        return self.login()

    def login(self):
        """
        Establishes a network connection and authenticates with the VistA server
        using the stored connection details.

        This method checks if a connection already exists. If not, it uses the
        `vavista.rpc.connect` function to create and authenticate a new one.

        Returns:
            bool: True if already connected or if a new connection is successful.

        Raises:
            Exception: Re-raises any exception that occurs during the connection
                       attempt, allowing the calling code to handle it (e.g., show an error message).
        """
        # Check if a connection object already exists. If it does, we don't need to do anything.
        if not self.connection:
            # If no connection exists, first ensure all necessary details have been provided.
            if not all([self.host, self.port, self.access_code, self.verify_code, self.context]):
                # If any detail is missing, print an error and return False.
                print("[ERROR] Connection details are not fully set.")
                return False
            
            # The 'try...except' block is used for error handling.
            # Code that might cause an error is placed in the 'try' block.
            try:
                # Print a message to indicate that a connection is being attempted.
                print(f"Connecting to {self.host}:{self.port}...")
                
                # This is the core call to the vavista library.
                # It opens a TCP socket to the host and port, sends the access/verify codes,
                # and sets the application context. If successful, it returns a connection object.
                # If it fails (e.g., wrong address, bad credentials), it raises an exception.
                self.connection = connect(
                    self.host, int(self.port), self.access_code, self.verify_code, self.context
                )
                
                # If the 'connect' call succeeds without raising an exception, print a success message.
                print("Connection successful.")
                
                # Return True to indicate success.
                return True
            
            # If any exception occurs in the 'try' block, the 'except' block is executed.
            except Exception as e:
                # Print the error for debugging purposes.
                print(f"Connection failed: {e}")
                
                # Reset the connection object to None, as the attempt failed.
                self.connection = None
                
                # Re-raise the exception. This passes the error up to the code that called login(),
                # which is responsible for handling it (e.g., showing a popup to the user).
                raise e
        
        # If self.connection was not None at the start, it means we are already connected, so just return True.
        return True

    def invoke_rpc(self, rpc_name, *params):
        """
        Invokes a specified VistA RPC with the given parameters.
        This is a general-purpose method for executing any RPC.

        Args:
            rpc_name (str): The exact name of the RPC to be called on the VistA server.
            *params: A variable number of arguments that will be passed as parameters to the RPC.
                     Each parameter should be an object from the vavista library (e.g., PLiteral).

        Returns:
            str: The raw string response returned by the VistA server for the RPC.
                 The format of this string varies depending on the RPC called.

        Raises:
            ConnectionError: If the client is not connected to VistA.
        """
        # First, ensure a connection is active by calling the login() method.
        # login() will return True if connected, or attempt to connect if not.
        if not self.login():
            # If login() fails, raise a ConnectionError to signal that the RPC cannot be invoked.
            raise ConnectionError("Not connected to VistA.")
        
        # This is the core call to the underlying vavista connection object.
        # The 'invoke' method sends the RPC name and its parameters to the VistA server
        # and waits for a response.
        raw_reply = self.connection.invoke(rpc_name, *params)

        # Return the raw text response from the server.
        return raw_reply

    def search_patient(self, search_term):
        """
        Searches for patients in VistA using a name or partial name.
        This method calls the 'ORWPT LIST ALL' RPC.

        Args:
            search_term (str): The patient name (e.g., "SMITH,JOHN" or "SMITH,J") to search for.
                               The VistA RPC typically performs a "starts with" search.

        Returns:
            list: A list of dictionaries. Each dictionary represents a patient and contains:
                  {'DFN': '12345', 'Name': 'SMITH,JOHN'}.
                  Returns an empty list if no patients are found.
        """
        # Call the invoke_rpc method with the specific RPC for patient lookups.
        # 'ORWPT LIST ALL' is a standard CPRS RPC for finding patients.
        # It takes two literal parameters: the search term and a flag (typically "1").
        # PLiteral is used to wrap the string parameters, marking them as literal values for the RPC.
        raw_list = self.invoke_rpc("ORWPT LIST ALL", PLiteral(search_term), PLiteral("1")).splitlines()
        
        # Initialize an empty list to store the parsed patient data.
        patients = []
        
        # The RPC returns data as a series of lines, so we loop through each line.
        for item in raw_list:
            # Check if the line is not empty.
            if item:
                # Each line is typically a '^'-delimited string (e.g., "12345^SMITH,JOHN").
                # We split the string by the '^' character to separate the pieces of data.
                parts = item.split('^')
                
                # A valid line should have at least two parts: the DFN and the Name.
                if len(parts) >= 2:
                    # Create a dictionary for the patient.
                    patient_data = {
                        "DFN": parts[0],  # The first part is the patient's DFN (internal ID).
                        "Name": parts[1] # The second part is the patient's name.
                    }
                    # Add the dictionary to our list of patients.
                    patients.append(patient_data)
        
        # Return the final list of found patients.
        return patients

    def select_patient(self, dfn):
        """
        Retrieves basic demographic information for a single patient using their DFN.
        This method calls the 'ORWPT SELECT' RPC.

        Args:
            dfn (str): The DFN (internal ID) of the patient to select.

        Returns:
            dict: A dictionary containing the patient's demographic details, such as:
                  {'Name': 'SMITH,JOHN', 'Sex': 'M', 'DOB': '2590101'}.
                  The DOB is in VistA's FileMan date format.
        """
        # Invoke the 'ORWPT SELECT' RPC. This RPC takes the patient's DFN as a single parameter.
        # It returns a single line of text with fields separated by '^'.
        raw_reply = self.invoke_rpc("ORWPT SELECT", PLiteral(dfn))
        
        # Split the response string into parts.
        parts = raw_reply.split('^')
        
        # Create a dictionary from the parts.
        # We check if each part exists before accessing it to avoid index errors if the
        # response is incomplete or malformed.
        patient_demographics = {
            "Name": parts[0] if len(parts) > 0 else None,   # First part is the Name.
            "Sex": parts[1] if len(parts) > 1 else None,    # Second part is the Sex.
            "DOB": parts[2] if len(parts) > 2 else None     # Third part is the Date of Birth (in FileMan format).
        }
        
        # Return the dictionary of demographic data.
        return patient_demographics

    def get_patient_inquiry(self, dfn):
        """
        Retrieves detailed patient information using the 'ORWPT PTINQ' RPC.

        Args:
            dfn (str): The DFN (internal ID) of the patient.

        Returns:
            str: The raw string response from the VistA server containing patient inquiry data.
        """
        # Invoke the 'ORWPT PTINQ' RPC. This RPC takes the patient's DFN as a single parameter.
        raw_reply = self.invoke_rpc("ORWPT PTINQ", PLiteral(dfn))
        return raw_reply

    def search_patients_with_demographics(self, search_term):
        """
        A high-level method that combines searching and demographic retrieval.
        First, it searches for patients by name, then for each result, it fetches
        the detailed demographic data.

        Args:
            search_term (str): The patient name or partial name to search for.

        Returns:
            list: A list of patient dictionaries. Each dictionary is enhanced with
                  full demographic info (Name, DFN, Sex, DOB).
                  Example: [{'DFN': '12345', 'Name': 'SMITH,JOHN', 'Sex': 'M', 'DOB': '2590101'}]
        """
        # Step 1: Get a list of potential patients who match the search term.
        # This calls the search_patient method defined above.
        print(f"Searching for patients matching '{search_term}'...")
        potential_patients = self.search_patient(search_term)
        
        # Initialize an empty list to hold the final, detailed patient information.
        detailed_patients = []
        
        # Step 2: Loop through each patient found in the initial search.
        print(f"Found {len(potential_patients)} potential patient(s). Now fetching details...")
        for patient in potential_patients:
            # Get the DFN for the current patient.
            dfn = patient.get("DFN")
            
            # If for some reason the DFN is missing, skip to the next patient.
            if not dfn:
                continue
            
            # Step 3: Fetch the detailed demographics for the current patient using their DFN.
            # This calls the select_patient method defined above.
            demographics = self.select_patient(dfn)
            
            # Step 4: Combine the initial info (DFN, Name) with the new demographic details.
            # We start with a copy of the initial patient dictionary.
            patient_details = patient.copy()
            # The update() method merges the demographics dictionary into our patient_details dictionary.
            patient_details.update(demographics)
            
            # Step 5: Add the combined, detailed dictionary to our final list.
            detailed_patients.append(patient_details)
            
        # After the loop, print how many detailed patient records were compiled.
        print(f"Returning {len(detailed_patients)} patient(s) with full demographics.")
        
        # Return the complete list.
        return detailed_patients
