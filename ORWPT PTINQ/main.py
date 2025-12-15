# -*- coding: utf-8 -*-
# This is the main application file for the Patient DFN Lookup GUI.
# Its purpose is to provide a user-friendly interface to search for a patient's
# Internal Entry Number (DFN) in a VistA Electronic Medical Record (EMR) system.
# The search can be performed using various combinations of Last Name, First Name,
# and Date of Birth.

# Import necessary Python standard libraries for GUI and system operations.
import tkinter as tk  # Tkinter is Python's standard GUI (Graphical User Interface) library.
from tkinter import ttk, scrolledtext, messagebox  # ttk provides themed widgets, scrolledtext for scrollable text, messagebox for pop-up messages.
import sys  # sys module provides access to system-specific parameters and functions.
import os  # os module provides a way of using operating system dependent functionality.

# Dynamically add the 'src' directory and the project root to the Python path.
# This ensures that our custom modules (like vista_rpc_client) and the vavista
# library can be imported correctly, regardless of where the script is run from.
# os.path.dirname(__file__) gets the directory of the current script.
# os.path.join constructs a path in an OS-independent way.
sys.path.append(os.path.dirname(__file__))  # Adds the current directory (project root)
sys.path.append(os.path.join(os.path.dirname(__file__), 'src')) # Adds the 'src' subdirectory

# Import our custom VistA RPC client module.
# This client handles all communication with the VistA server.
from vista_rpc_client import VistaRpcClient

class GUILogger:
    """
    A simple logging utility designed to direct log messages to a GUI component.
    This helps in debugging and understanding the application's flow without
    cluttering the console.
    """
    def __init__(self, log_func):
        """
        Initializes the GUILogger with a function to display messages.

        Args:
            log_func (callable): A function (e.g., a method of a ScrolledText widget)
                                 that accepts a string message and appends it to a display area.
        """
        self.log_func = log_func  # Store the provided function for later use.

    def logInfo(self, tag, msg):
        """
        Logs an informational message to the GUI's log display.

        Args:
            tag (str): A string tag to categorize the message (e.g., "INFO", "GUI").
            msg (str): The actual message content to be displayed.
        """
        # Format the message with a tag and append it to the GUI log.
        self.log_func(f"{tag}: {msg}")

    def logError(self, tag, msg):
        """
        Logs an error message to the GUI's log display.

        Args:
            tag (str): A string tag to categorize the error (e.g., "ERROR", "RPC").
            msg (str): The actual error message content to be displayed.
        """
        # Format the error message with an "ERROR" prefix and tag, then append to GUI log.
        self.log_func(f"ERROR - {tag}: {msg}")

class LogWindow(tk.Toplevel):
    """
    A secondary Tkinter window dedicated to displaying application logs.
    This window uses a ScrolledText widget to provide a scrollable and
    read-only view of log messages.
    """
    def __init__(self, master):
        """
        Initializes the LogWindow.

        Args:
            master (tk.Tk or tk.Toplevel): The parent Tkinter window.
        """
        super().__init__(master)  # Call the constructor of the parent class (tk.Toplevel).
        self.title("Application Log")  # Set the title of the log window.
        self.geometry("600x400")  # Set the initial size of the log window.

        # Create a ScrolledText widget. This widget combines a Text widget with scrollbars.
        # wrap=tk.WORD ensures that lines break at word boundaries instead of mid-word.
        self.log_text = scrolledtext.ScrolledText(self, wrap=tk.WORD)
        # pack() is a geometry manager that organizes widgets in blocks.
        # fill=tk.BOTH makes the widget expand both horizontally and vertically.
        # expand=True makes it take up any extra space allocated to its parent.
        self.log_text.pack(fill=tk.BOTH, expand=True)
        # Configure the text widget to be read-only, preventing user input.
        self.log_text.config(state=tk.DISABLED)

    def log(self, message):
        """
        Appends a new message to the log window.

        Args:
            message (str): The string message to append to the log.
        """
        # Before inserting text, temporarily enable the widget.
        self.log_text.config(state=tk.NORMAL)
        # Insert the message at the end of the current text.
        self.log_text.insert(tk.END, message + "\n")
        # Scroll the view to the end so the latest message is always visible.
        self.log_text.see(tk.END)
        # After inserting, disable the widget again to keep it read-only.
        self.log_text.config(state=tk.DISABLED)

class ReportWindow(tk.Toplevel):
    """
    A secondary Tkinter window dedicated to displaying a patient report.
    """
    def __init__(self, master):
        """
        Initializes the ReportWindow.
        """
        super().__init__(master)
        self.title("Patient Inquiry Report")
        self.geometry("700x800")

        self.report_text = scrolledtext.ScrolledText(self, wrap=tk.WORD)
        self.report_text.pack(fill=tk.BOTH, expand=True)
        self.report_text.config(state=tk.DISABLED)

    def display_report(self, report_data):
        """
        Displays the report data in the window.
        """
        self.report_text.config(state=tk.NORMAL)
        self.report_text.delete('1.0', tk.END)
        self.report_text.insert(tk.END, report_data)
        self.report_text.config(state=tk.DISABLED)
        # Bring the window to the front
        self.deiconify()
        self.lift()
        self.focus_force()

class PatientDFNLookupApp(tk.Tk):
    """
    The main application class for the Patient DFN Lookup GUI.
    It inherits from tk.Tk, making it the root window of our application.
    """
    def __init__(self):
        """
        Initializes the main application window and its components.
        """
        super().__init__()  # Call the constructor of the parent class (tk.Tk).
        self.title("Patient DFN Lookup")  # Set the title of the main application window.
        self.geometry("800x600")  # Set the initial size of the window.

        # Initialize the LogWindow. This will be a separate window for logging.
        self.log_window = LogWindow(self)
        self.report_window = ReportWindow(self)
        self.report_window.withdraw()  # Hide the report window initially

        # Create an instance of our GUILogger, passing the log method of the LogWindow.
        # This means all log messages from the GUI will go to our LogWindow.
        gui_logger = GUILogger(self.log_window.log)

        # Instantiate our VistA RPC client, passing the GUI logger for internal logging.
        self.vista_client = VistaRpcClient()
        # Note: The `VistaRpcClient` in this simplified app does not need a `comm_logger`
        # as it's not exposing the RPC communication details to a separate window.
        # However, for advanced debugging, one might add it back.

        # Initialize attributes to store current patient DFN and details.
        self.current_dfn = None
        self.current_patient_info = None

        # Build the graphical user interface elements.
        self._create_widgets()

    def _create_widgets(self):
        """
        Constructs and lays out all the GUI widgets in the main application window.
        This includes connection input fields, patient search fields, and result display areas.
        """
        # Configure the main window's grid layout to be responsive.
        # The column with index 0 will expand horizontally.
        self.columnconfigure(0, weight=1)
        # The row with index 1 (where the notebook sits) will expand vertically.
        self.rowconfigure(1, weight=1)

        # --- Connection Frame ---
        # This frame holds inputs for connecting to the VistA server.
        conn_frame = ttk.LabelFrame(self, text="VistA Connection", padding="10")
        conn_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        # Configure columns within the connection frame to expand.
        conn_frame.columnconfigure(1, weight=1)
        conn_frame.columnconfigure(3, weight=1)

        # Host input field.
        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.host_entry = ttk.Entry(conn_frame)
        self.host_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        self.host_entry.insert(0, "127.0.0.1")  # Default host for local VistA instance.

        # Port input field.
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.port_entry = ttk.Entry(conn_frame)
        self.port_entry.grid(row=0, column=3, padx=5, pady=2, sticky="ew")
        self.port_entry.insert(0, "9297")  # Default port for VistA RPC Broker.

        # Access Code input field (masked for security).
        ttk.Label(conn_frame, text="Access Code:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.access_entry = ttk.Entry(conn_frame, show="*")  # show="*" hides input characters.
        self.access_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.access_entry.insert(0, "DOCTOR1") # Default access code for demo.

        # Verify Code input field (masked for security).
        ttk.Label(conn_frame, text="Verify Code:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.verify_entry = ttk.Entry(conn_frame, show="*")
        self.verify_entry.grid(row=1, column=3, padx=5, pady=2, sticky="ew")
        self.verify_entry.insert(0, "DOCTOR1.") # Default verify code for demo.

        # Connect button.
        self.connect_button = ttk.Button(conn_frame, text="Connect", command=self._connect_to_vista)
        self.connect_button.grid(row=0, column=4, rowspan=2, padx=10, pady=5, sticky="ns")

        # --- Patient Search Frame ---
        # This frame holds inputs for searching patients.
        search_frame = ttk.LabelFrame(self, text="Patient Search", padding="10")
        search_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        search_frame.columnconfigure(1, weight=1) # Allow name input fields to expand.
        search_frame.columnconfigure(3, weight=1) # Allow name input fields to expand.

        # Last Name input field.
        ttk.Label(search_frame, text="Last Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.search_last_name_entry = ttk.Entry(search_frame)
        self.search_last_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # First Name input field.
        ttk.Label(search_frame, text="First Name:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.search_first_name_entry = ttk.Entry(search_frame)
        self.search_first_name_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        # Date of Birth input fields (Year, Month, Day).
        dob_frame = ttk.Frame(search_frame)
        dob_frame.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        
        ttk.Label(dob_frame, text="DOB:").pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(dob_frame, text="Year:").pack(side=tk.LEFT)
        self.search_dob_year_entry = ttk.Entry(dob_frame, width=6)
        self.search_dob_year_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(dob_frame, text="Month:").pack(side=tk.LEFT)
        self.search_dob_month_entry = ttk.Entry(dob_frame, width=4)
        self.search_dob_month_entry.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(dob_frame, text="Day:").pack(side=tk.LEFT)
        self.search_dob_day_entry = ttk.Entry(dob_frame, width=4)
        self.search_dob_day_entry.pack(side=tk.LEFT)
        
        # Search button. It's disabled initially until a VistA connection is established.
        self.search_button = ttk.Button(search_frame, text="Search", command=self._search_patient, state=tk.DISABLED)
        self.search_button.grid(row=0, column=4, rowspan=2, padx=10, pady=5, sticky="ns")

        # Clear button. This will reset all input fields and result labels.
        self.clear_button = ttk.Button(search_frame, text="Clear", command=self._clear_fields)
        self.clear_button.grid(row=2, column=4, padx=10, pady=5, sticky="ns")
        
        # --- Results Display Frame ---
        # This frame will display the DFN and other demographic details of the found patient.
        results_frame = ttk.LabelFrame(self, text="Patient DFN & Details", padding="10")
        results_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        results_frame.columnconfigure(1, weight=1) # Allow the value labels to expand.
        # Label to display the patient's DFN.
        ttk.Label(results_frame, text="DFN:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.dfn_result_label = ttk.Label(results_frame, text="N/A", font=("TkDefaultFont", 10, "bold"))
        self.dfn_result_label.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        # Label to display the patient's Full Name.
        ttk.Label(results_frame, text="Name:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.name_result_label = ttk.Label(results_frame, text="N/A")
        self.name_result_label.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        # Label to display the patient's Sex.
        ttk.Label(results_frame, text="Sex:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.sex_result_label = ttk.Label(results_frame, text="N/A")
        self.sex_result_label.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        # Label to display the patient's Date of Birth.
        ttk.Label(results_frame, text="DOB:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.dob_result_label = ttk.Label(results_frame, text="N/A")
        self.dob_result_label.grid(row=3, column=1, padx=5, pady=2, sticky="ew")

        # Button to get patient inquiry details.
        self.patient_inquiry_button = ttk.Button(results_frame, text="Get Patient Inquiry", command=self._get_patient_inquiry, state=tk.DISABLED)
        self.patient_inquiry_button.grid(row=4, column=0, columnspan=2, padx=5, pady=10)

        # --- Patient Selection Window (for multiple matches) ---
        # This function defines a pop-up window that appears if multiple patients
        # match the search criteria, allowing the user to select the correct one.
    def _open_patient_selection_window(self, patients_data):
        """
        Opens a modal Toplevel window for the user to select a patient from a list.
        This is used when multiple patients match the search criteria.

        Args:
            patients_data (list): A list of dictionaries, where each dictionary
                                  represents a patient with 'DFN', 'Name', and 'DOB'.
        """
        # Create a new top-level window.
        selection_window = tk.Toplevel(self)
        selection_window.title("Select Patient")  # Set the title of the selection window.
        selection_window.geometry("500x300")  # Set its initial size.
        selection_window.transient(self)  # Make it appear on top of the main window.
        selection_window.grab_set()  # Make it modal, blocking interaction with other windows.

        # Create a Treeview widget to display patient data in a table format.
        # columns defines the identifiers for each column.
        # show="headings" means only the column headers will be visible, not the default tree column.
        tree = ttk.Treeview(selection_window, columns=("DFN", "Name", "DOB"), show="headings")
        # Define the text for each column heading.
        tree.heading("DFN", text="DFN")
        tree.heading("Name", text="Name")
        tree.heading("DOB", text="DOB")
        # Set the width for each column.
        tree.column("DFN", width=100)
        tree.column("Name", width=250)
        tree.column("DOB", width=100)
        # Pack the treeview to fill and expand within its parent window.
        tree.pack(fill=tk.BOTH, expand=True)

        # Populate the treeview with data from the patients_data list.
        for patient in patients_data:
            # Insert each patient's data as a new row.
            # The values tuple corresponds to the columns defined above.
            tree.insert("", "end", values=(patient.get("DFN"), patient.get("Name"), patient.get("DOB", "")))

        def on_double_click(event):
            """
            Event handler for a double-click on a row in the Treeview.
            When a patient is double-clicked, their DFN is selected, and the window closes.
            """
            # Get the currently selected item(s).
            selected_item = tree.selection()
            if not selected_item:
                return  # If nothing is selected, do nothing.
            
            # Retrieve the DFN from the selected item's values.
            # tree.item(selected_item[0], "values") returns a tuple of all column values for the first selected item.
            dfn = tree.item(selected_item[0], "values")[0]
            
            # Log the selection and update the main application's display with the selected DFN.
            print(f"Patient selected via double-click: DFN {dfn}")
            self._display_patient_details(dfn) # Call to display in main window.
            
            selection_window.destroy()  # Close the selection window.

        # Bind the <Double-1> event (double-click with mouse button 1) to our handler.
        tree.bind("<Double-1>", on_double_click)

    def _connect_to_vista(self):
        """
        Handles the "Connect" button click.
        Attempts to establish a connection to the VistA server using the provided credentials.
        Updates the UI state based on connection success or failure.
        """
        # Retrieve values from the connection input fields.
        host = self.host_entry.get()
        port = self.port_entry.get()
        access = self.access_entry.get()
        verify = self.verify_entry.get()
        
        # Check if all required fields have been filled.
        if not all([host, port, access, verify]):
            messagebox.showerror("Connection Error", "All connection fields are required.")
            return

        # Log the connection attempt.
        self.log_window.log(f"INFO: Attempting to connect to VistA at {host}:{port}...")
        try:
            # Call the VistaRpcClient's connect_to_vista method.
            # We explicitly pass "OR CPRS GUI CHART" as the context for this application.
            success = self.vista_client.connect_to_vista(host, int(port), access, verify, "OR CPRS GUI CHART")
            if success:
                # If connection is successful, show a success message.
                messagebox.showinfo("Success", "Successfully connected to VistA.")
                # Enable the search button, as it requires an active connection.
                self.search_button.config(state=tk.NORMAL)
                self.log_window.log("INFO: VistA connection established. Search function enabled.")
            else:
                # If connect_to_vista returns False (shouldn't happen with exception handling, but as a safeguard).
                messagebox.showerror("Connection Error", "Connection failed for unknown reasons.")
                self.log_window.log("ERROR: VistA connection failed without specific exception.")
        except Exception as e:
            # Catch any exception during connection and display an error message.
            messagebox.showerror("Connection Error", f"Failed to connect to VistA: {e}")
            self.log_window.log(f"ERROR: Exception during VistA connection: {e}")

    def _clear_fields(self):
        """
        Clears all input fields and resets the result display labels to their default state.
        """
        self.search_last_name_entry.delete(0, tk.END)
        self.search_first_name_entry.delete(0, tk.END)
        self.search_dob_year_entry.delete(0, tk.END)
        self.search_dob_month_entry.delete(0, tk.END)
        self.search_dob_day_entry.delete(0, tk.END)

        self.dfn_result_label.config(text="N/A")
        self.name_result_label.config(text="N/A")
        self.sex_result_label.config(text="N/A")
        self.dob_result_label.config(text="N/A")
        
        self.current_dfn = None
        self.current_patient_info = None
        self.patient_inquiry_button.config(state=tk.DISABLED)
        self.log_window.log("INFO: All search fields and results cleared.")

    def _get_patient_inquiry(self):
        """
        Handles the 'Get Patient Inquiry' button click.
        Calls the ORWPT PTINQ RPC and logs the raw output.
        """
        if not self.current_dfn:
            messagebox.showwarning("Inquiry Error", "No patient selected.")
            return

        self.log_window.log(f"INFO: Calling ORWPT PTINQ for DFN: {self.current_dfn}")
        try:
            inquiry_data = self.vista_client.get_patient_inquiry(self.current_dfn)
            self.report_window.display_report(inquiry_data)
            self.log_window.log("--- PATIENT INQUIRY START ---")
            self.log_window.log(inquiry_data)
            self.log_window.log("--- PATIENT INQUIRY END ---")
        except Exception as e:
            messagebox.showerror("Inquiry Error", f"Failed to get patient inquiry: {e}")
            self.log_window.log(f"ERROR: Exception during patient inquiry: {e}")

    def _display_patient_details(self, dfn):
        """
        Fetches and displays the full demographic details for a given DFN in the results frame.

        Args:
            dfn (str): The DFN of the patient whose details are to be displayed.
        """
        # Store the currently selected DFN.
        self.current_dfn = dfn
        self.log_window.log(f"INFO: Fetching details for selected patient DFN: {dfn}")
        try:
            # Use the RPC client to get the patient's full demographics.
            patient_info = self.vista_client.select_patient(dfn)
            self.current_patient_info = patient_info # Store for potential future use.

            # Update the result labels in the GUI.
            self.dfn_result_label.config(text=patient_info.get("DFN", "N/A"))
            self.name_result_label.config(text=patient_info.get("Name", "N/A"))
            self.sex_result_label.config(text=patient_info.get("Sex", "N/A"))
            # Display DOB, converting from FileMan format to a more readable format for the UI.
            # Example: 2350407 -> 04/07/1935
            fileman_dob = patient_info.get("DOB", "N/A")
            if fileman_dob != "N/A" and len(fileman_dob) == 7 and fileman_dob.isdigit():
                # Extract year, month, day components from FileMan format.
                year_part = int(fileman_dob[0:3]) + 1700
                month_part = fileman_dob[3:5]
                day_part = fileman_dob[5:7]
                display_dob = f"{month_part}/{day_part}/{year_part}"
                self.dob_result_label.config(text=display_dob)
            else:
                self.dob_result_label.config(text=fileman_dob) # Display as is if not a recognized format.

            self.log_window.log(f"INFO: Displayed details for {patient_info.get('Name')}.")
            self.patient_inquiry_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Display Error", f"Failed to fetch and display patient details: {e}")
            self.log_window.log(f"ERROR: Exception displaying patient details: {e}")

    def _search_patient(self):
        """
        Handles the "Search" button click.
        Initiates a patient search based on the Last Name, First Name, and DOB input fields.
        Applies strict matching and displays results or selection window.
        """
        # Retrieve user input from the GUI fields.
        last_name = self.search_last_name_entry.get().strip()
        first_name = self.search_first_name_entry.get().strip()
        year_str = self.search_dob_year_entry.get().strip()
        month_str = self.search_dob_month_entry.get().strip()
        day_str = self.search_dob_day_entry.get().strip()

        # Validate that at least a last name is provided.
        if not last_name:
            messagebox.showwarning("Search Error", "Please enter at least a last name to search.")
            return

        # Construct the search term for VistA.
        # VistA's ORWPT LIST ALL RPC often works best with `LAST,F` (first initial) or `LAST` in all caps.
        search_term = last_name.upper()
        if first_name:
            # Append only the first initial if a first name is provided.
            search_term += "," + first_name[0].upper()

        # Prepare DOB for comparison if all date fields are filled.
        dob_for_comparison = ""
        is_dob_search = all([year_str, month_str, day_str])
        if is_dob_search:
            try:
                # Map various month inputs (name, abbr, number) to a two-digit number.
                month_map = {
                    'january': '01', 'jan': '01', '1': '01', '01': '01',
                    'february': '02', 'feb': '02', '2': '02', '02': '02',
                    'march': '03', 'mar': '03', '3': '03', '03': '03',
                    'april': '04', 'apr': '04', '4': '04', '04': '04',
                    'may': '05', '5': '05', '05': '05',
                    'june': '06', 'jun': '06', '6': '06', '06': '06',
                    'july': '07', 'jul': '07', '7': '07', '07': '07',
                    'august': '08', 'aug': '08', '8': '08', '08': '08',
                    'september': '09', 'sep': '09', '9': '09', '09': '09',
                    'october': '10', 'oct': '10', '10': '10',
                    'november': '11', 'nov': '11', '11': '11',
                    'december': '12', 'dec': '12', '12': '12'
                }
                month_num = month_map.get(month_str.lower())
                if not month_num:
                    raise ValueError("Month is invalid. Use name (Jan), abbr (Jan), or number (1).")

                # Convert Gregorian year to VistA's FileMan year format (years since 1700).
                vista_year = int(year_str) - 1700
                # Construct the full FileMan date string (YYYMMDD).
                dob_for_comparison = f"{vista_year}{month_num}{day_str.zfill(2)}"
                
                # Basic validation for year format.
                if len(year_str) != 4:
                    raise ValueError("Year must be 4 digits.")
            except (ValueError, KeyError) as e:
                # Catch any errors during date parsing and show a user-friendly message.
                messagebox.showwarning(
                    "Invalid Date",
                    f"Please ensure the date is entered correctly (e.g., Year: 1980, Month: Jan or 1, Day: 15). Details: {e}"
                )
                return

        try:
            # Log the search term being sent to VistA.
            self.log_window.log(f"INFO: Initiating patient search for: '{search_term}'")
            # Call the VistaRpcClient to search for patients and get their demographics.
            patients = self.vista_client.search_patients_with_demographics(search_term)

            # If no patients are found by the name search, inform the user.
            if not patients:
                messagebox.showinfo("Search Results", "No patients found matching that name.")
                self.log_window.log(f"INFO: No patients found for search term: '{search_term}'.")
                # Clear previous results display.
                self.dfn_result_label.config(text="N/A")
                self.name_result_label.config(text="N/A")
                self.sex_result_label.config(text="N/A")
                self.dob_result_label.config(text="N/A")
                return
            
            # --- Debugging Step for DOB format ---
            # This logs the full details of the first patient found, useful for verifying VistA DOB format.
            self.log_window.log(f"DEBUG: First patient (raw from VistA) in list: {patients[0]}")
            # --- End Debugging Step ---

            # If DOB was provided, apply strict filtering.
            if is_dob_search:
                self.log_window.log(f"INFO: Applying strict DOB filter for FileMan DOB: '{dob_for_comparison}'")
                # Filter the list to find only patients with an exact DOB match.
                matched_patients = [p for p in patients if p.get("DOB") == dob_for_comparison]

                # If no patients match the DOB after filtering.
                if not matched_patients:
                    messagebox.showinfo(
                        "Search Results",
                        f"A patient with name matching '{search_term}' was found, but no exact match for DOB '{year_str}-{month_str}-{day_str}'."
                    )
                    self.log_window.log(f"INFO: No patient found matching both name and exact DOB: '{dob_for_comparison}'.")
                    # Clear previous results display.
                    self.dfn_result_label.config(text="N/A")
                    self.name_result_label.config(text="N/A")
                    self.sex_result_label.config(text="N/A")
                    self.dob_result_label.config(text="N/A")
                    return
                
                # If exactly one patient matches both name and DOB, display their details directly.
                if len(matched_patients) == 1:
                    self.log_window.log(f"INFO: Found exact unique match. Displaying patient DFN: {matched_patients[0]['DFN']}.")
                    self._display_patient_details(matched_patients[0]["DFN"])
                else:
                    # If multiple patients match (e.g., twins with same name/DOB), open the selection window.
                    self.log_window.log(f"INFO: Found multiple exact matches. Opening selection window.")
                    self._open_patient_selection_window(matched_patients)
            
            # If no DOB was provided, show all patients found by the name search in a selection window.
            else:
                self.log_window.log("INFO: No DOB entered. Displaying all patients found by name in selection window.")
                self._open_patient_selection_window(patients)

        except Exception as e:
            # Catch and log any unexpected errors during the search process.
            self.log_window.log(f"ERROR: Exception during patient search: {e}")
            # Use traceback to get a detailed error report for debugging.
            import traceback
            self.log_window.log(traceback.format_exc())
            messagebox.showerror("Search Error", f"An unexpected error occurred during search: {e}")

# This block ensures that the code inside it only runs when the script is executed directly,
# not when it's imported as a module into another script.
if __name__ == "__main__":
    # Print a message to the console indicating the application is starting.
    print("Starting Patient DFN Lookup application...")
    # Create an instance of our main application class.
    app = PatientDFNLookupApp()
    # Start the Tkinter event loop. This makes the GUI responsive to user interactions
    # and keeps the application running until the window is closed.
    app.mainloop()
    print("Patient DFN Lookup application closed.")
