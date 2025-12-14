import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import sys
import os
import json

# Add the directory containing the vavista package to the Python path
# This ensures that the 'vavista' package can be imported correctly,
# allowing access to its RPC client functionalities.


# Add the src directory to the Python path
# This makes modules within the 'src' directory importable,
# such as the VistA RPC client, configuration loader, and controllers.
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import core components of the application
from vista_rpc_client import VistaRpcClient  # Handles direct communication with VistA via RPCs
from rpc_config_loader import RPCConfigLoader  # Loads RPC configurations and documentation
from order_entry import OrderEntry          # Manages order-related RPC calls and logic
from lab_order_controller import LabOrderController # Manages specific lab order interactions and UI


class GUILogger:
    """
    A simple logger class to direct log messages to a GUI component.
    This decouples the logging mechanism from the GUI's log display,
    making it easier to swap out logging destinations if needed.
    """
    def __init__(self, log_func):
        """
        Initializes the GUILogger.
        Args:
            log_func: A callable function (e.g., a method of a scrolled text widget)
                      that accepts a string message and displays it.
        """
        self.log_func = log_func

    def logInfo(self, tag, msg):
        """
        Logs an informational message.
        Args:
            tag (str): A tag to categorize the log message (e.g., "INFO", "GUI").
            msg (str): The actual message content.
        """
        self.log_func(f"{tag}: {msg}")

    def logError(self, tag, msg):
        """
        Logs an error message.
        Args:
            tag (str): A tag to categorize the log message (e.g., "ERROR", "RPC").
            msg (str): The actual message content.
        """
        self.log_func(f"ERROR - {tag}: {msg}")


class LogWindow(tk.Toplevel):
    """
    A Toplevel (child) window for displaying general application logs.
    It uses a ScrolledText widget to allow viewing of extensive log output.
    """
    def __init__(self, master):
        """
        Initializes the LogWindow.
        Args:
            master: The parent Tkinter window.
        """
        super().__init__(master)
        self.title("Log")
        self.geometry("600x800") # Sets initial size of the log window
        # ScrolledText widget for displaying log messages with a scrollbar
        self.log_text = scrolledtext.ScrolledText(self, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED) # Make the text area read-only

    def log(self, message):
        """
        Appends a message to the log window.
        Args:
            message (str): The message to append.
        """
        # Check if the window still exists before attempting to log
        if not self.log_text.winfo_exists():
            return
        self.log_text.config(state=tk.NORMAL) # Enable editing to insert text
        self.log_text.insert(tk.END, message + "\n") # Insert message at the end
        self.log_text.see(tk.END) # Scroll to the end to show the latest message
        self.log_text.config(state=tk.DISABLED) # Disable editing again


class RPCCommWindow(tk.Toplevel):
    """
    A Toplevel window specifically for logging raw RPC communication.
    This helps in debugging and understanding the exact data exchanged with VistA.
    """
    def __init__(self, master):
        """
        Initializes the RPCCommWindow.
        Args:
            master: The parent Tkinter window.
        """
        super().__init__(master)
        self.title("RPC Communication Log")
        self.geometry("800x600") # Sets initial size of the RPC communication log window
        # ScrolledText widget for displaying RPC communication logs
        self.log_text = scrolledtext.ScrolledText(self, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED) # Make the text area read-only

    def log(self, message):
        """
        Appends a message to the RPC communication log window.
        Args:
            message (str): The message to append.
        """
        # Check if the window still exists before attempting to log
        if not self.log_text.winfo_exists():
            return
        self.log_text.config(state=tk.NORMAL) # Enable editing to insert text
        self.log_text.insert(tk.END, message + "\n") # Insert message at the end
        self.log_text.see(tk.END) # Scroll to the end to show the latest message
        self.log_text.config(state=tk.DISABLED) # Disable editing again


class RecentNotesOptionsWindow(tk.Toplevel):
    """
    A modal Toplevel window for configuring options when fetching recent patient notes.
    Allows the user to specify the number of notes, document class IEN, and status (signed/unsigned).
    """
    def __init__(self, master):
        """
        Initializes the RecentNotesOptionsWindow.
        Args:
            master: The parent Tkinter window.
        """
        super().__init__(master)
        self.master = master
        self.title("Recent Notes Options")
        self.geometry("300x200") # Increased height for new field
        self.transient(master)  # Make it a transient window relative to master
        self.grab_set()      # Make it modal, blocking interaction with other windows until closed

        # Variables to store the user's selections
        self.result_note_count = None
        self.result_doc_class_ien = None
        self.result_status = None

        self._create_widgets()

    def _create_widgets(self):
        """
        Creates and lays out the widgets for the recent notes options window.
        """
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Number of Notes input field
        ttk.Label(main_frame, text="Number of Notes:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.note_count_entry = ttk.Entry(main_frame)
        self.note_count_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.note_count_entry.insert(0, "100") # Default value to 100, matching Delphi

        # Document Class IEN input field
        ttk.Label(main_frame, text="Doc Class IEN:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.doc_class_ien_entry = ttk.Entry(main_frame)
        self.doc_class_ien_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.doc_class_ien_entry.insert(0, "3") # Default value to 3 (Progress Notes)

        # Status selection combobox
        ttk.Label(main_frame, text="Status:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.status_combobox = ttk.Combobox(main_frame, values=["All", "Signed", "Unsigned"], state="readonly")
        self.status_combobox.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.status_combobox.set("All") # Default to "All"

        # Buttons for interaction
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="Get Notes", command=self._on_get_notes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.LEFT, padx=5)

    def _on_get_notes(self):
        """
        Handles the "Get Notes" button click. Validates input and stores results.
        """
        try:
            count = int(self.note_count_entry.get())
            doc_class_ien = int(self.doc_class_ien_entry.get())

            if count <= 0:
                messagebox.showwarning("Invalid Input", "Number of notes must be a positive integer.")
                return
            if doc_class_ien <= 0:
                messagebox.showwarning("Invalid Input", "Document Class IEN must be a positive integer.")
                return

            self.result_note_count = count
            self.result_doc_class_ien = doc_class_ien
            self.result_status = self.status_combobox.get()
            self.destroy() # Close the window after successful input
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter valid numbers for notes and document class IEN.")

    def _on_cancel(self):
        """
        Handles the "Cancel" button click. Clears results and closes the window.
        """
        self.result_note_count = None
        self.result_doc_class_ien = None
        self.result_status = None
        self.destroy() # Close the window


class VistARPCGUI(tk.Tk):

    def _select_patient(self, dfn):
        """
        Selects a patient by DFN, fetches their data, and updates the GUI.
        This method orchestrates several RPC calls to gather patient information,
        notes, and note titles, then updates various UI elements accordingly.
        Args:
            dfn (str): The internal entry number (DFN) of the patient to select.
        """
        self.log_window.log(f"Attempting to select patient and load all related data for DFN: {dfn}...")
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA. Please connect first.")
            return

        try:
            # Single call to the service layer to handle all business logic
            # This method in vista_client is expected to encapsulate multiple RPCs
            # to get a comprehensive set of patient data.
            patient_data = self.vista_client.select_and_get_patient_data(dfn)

            # --- Unpack data and update UI ---
            patient_info = patient_data.get("patient_info", {})
            patient_name = patient_info.get("Name", "Unknown")
            
            self.log_window.log(f"Successfully selected patient: {patient_name} (DFN: {dfn})")
            # Update the displayed current patient name and DFN
            self.current_patient_label.config(text=f"{patient_name} (DFN: {dfn})")
            self.current_dfn = dfn # Store the currently selected patient's DFN

            # Update notes treeview with fetched notes
            self.notes_tree.delete(*self.notes_tree.get_children()) # Clear existing notes
            patient_notes = patient_data.get("patient_notes", [])
            for note in patient_notes:
                self.notes_tree.insert("", "end", values=(note.get('IEN'), note.get('Title'), note.get('Date')))
            self.log_window.log(f"Loaded {len(patient_notes)} notes.")

            # Update note titles combobox
            titles_data = patient_data.get("note_titles", [])
            # Create a dictionary mapping note titles to their IENs for easy lookup
            self.note_titles = {item['Title']: item['IEN'] for item in titles_data}
            self.note_title_combobox['values'] = list(self.note_titles.keys()) # Populate combobox
            if self.note_titles:
                self.note_title_combobox.set(list(self.note_titles.keys())[0]) # Set default selection
            self.log_window.log(f"Loaded {len(self.note_titles)} note titles.")

            # --- Handle UI state changes and other orchestration ---
            self.refresh_encounters_button.config(state=tk.NORMAL) # Enable encounter refresh button
            # Load order menus for the newly selected patient
            self._load_order_menus(dfn) # This remains as orchestration logic in the GUI

        except Exception as e:
            # Log and display any errors during patient selection
            self.log_window.log(f"ERROR: Failed to select patient or get related data: {e}")
            import traceback
            self.log_window.log(traceback.format_exc())
            messagebox.showerror("RPC Error", f"Failed to select patient: {e}")

    def _fetch_patient_encounters(self):
        """
        Populates the encounter treeview with available clinics/locations.
        It attempts to load clinic data from a local JSON cache first. If not found or
        if there's an error, it uses a hardcoded list and tries to save it to cache.
        """
        self.log_window.log("Populating encounters.")
        self.encounter_tree.delete(*self.encounter_tree.get_children()) # Clear existing encounters

        CLINICS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'clinics.json')
        clinics_data = []

        # Try to load from JSON cache
        if os.path.exists(CLINICS_FILE):
            try:
                with open(CLINICS_FILE, 'r') as f:
                    clinics_data = json.load(f)
                self.log_window.log(f"Loaded {len(clinics_data)} clinics from cache: {CLINICS_FILE}")
            except (IOError, json.JSONDecodeError) as e:
                self.log_window.log(f"ERROR: Could not load clinics from cache ({e}). Using hardcoded list.")
                clinics_data = self._get_hardcoded_clinics() # Use a helper for hardcoded list
        else:
            self.log_window.log(f"Clinics cache not found at {CLINICS_FILE}. Using hardcoded list.")
            clinics_data = self._get_hardcoded_clinics() # Use a helper for hardcoded list
            # Save to cache for next time to optimize future loads
            try:
                os.makedirs(os.path.dirname(CLINICS_FILE), exist_ok=True) # Ensure directory exists
                with open(CLINICS_FILE, 'w') as f:
                    json.dump(clinics_data, f, indent=4) # Pretty print JSON
                self.log_window.log(f"Saved clinics to cache: {CLINICS_FILE}")
            except IOError as e:
                self.log_window.log(f"ERROR: Could not save clinics to cache ({e}).")

        fm_timestamp = self.vista_client._get_fileman_timestamp() # Get current FileMan timestamp for visits
        for clinic in clinics_data:
            clinic_name = clinic.get("name")
            location_ien = clinic.get("ien")
            if clinic_name and location_ien:
                # Construct visit string as expected by VistA RPCs
                visit_str = f"{location_ien};{fm_timestamp};A" # Format: IEN;DATE;TYPE
                self.encounter_tree.insert("", "end", values=(clinic_name, fm_timestamp), iid=visit_str)

    # Helper method to keep the hardcoded list separate and clean
    def _get_hardcoded_clinics(self):
        """
        Helper method to provide a hardcoded list of clinic names and their IENs.
        This acts as a fallback if the clinics.json cache cannot be loaded or is missing.
        Returns:
            list: A list of dictionaries, each containing 'name' and 'ien' for a clinic.
        """
        return [
            {"name": "CARDIOLOGY", "ien": "100"}, {"name": "GENERAL MEDICINE", "ien": "101"},
            {"name": "GENERAL SURGERY", "ien": "102"}, {"name": "LABORATORY", "ien": "103"},
            {"name": "MAMMOGRAM", "ien": "104"}, {"name": "NEPHROLOGY", "ien": "105"},
            {"name": "NUCLEAR MEDICINE", "ien": "106"}, {"name": "OBSERVATION", "ien": "107"},
            {"name": "PLASTIC SURGERY", "ien": "108"}, {"name": "PODIATRY", "ien": "109"},
            {"name": "PRIMARY CARE", "ien": "200"}, {"name": "PSYCHIOLOGY", "ien": "110"},
            {"name": "RADIOLOGY", "ien": "111"}, {"name": "SOCIAL WORK", "ien": "112"},
            {"name": "SURGICAL CLINIC", "ien": "113"}
        ]

    def _fetch_patient_notes(self, dfn, note_count, doc_class_ien, context=1):
        """
        Fetches patient notes from VistA based on DFN, document class, and context,
        then populates the notes treeview.
        Args:
            dfn (str): Patient's DFN.
            note_count (int): Maximum number of notes to fetch.
            doc_class_ien (str): IEN of the document class (e.g., Progress Notes).
            context (int): Context for fetching notes (e.g., 1 for signed, 2 for unsigned, 15 for all).
        """
        try:
            self.log_window.log(f"_fetch_patient_notes: dfn={dfn}, note_count={note_count}, doc_class_ien={doc_class_ien}, context={context}")
            self.notes_tree.delete(*self.notes_tree.get_children()) # Clear existing notes
            self.log_window.log(f"Attempting to fetch notes for DFN: {dfn} with Doc Class IEN: {doc_class_ien} and context: {context}")
            # Call the vista_client to fetch notes
            notes = self.vista_client.fetch_patient_notes(dfn, doc_class_ien=doc_class_ien, context=context, max_docs=note_count)
            if notes:
                for note in notes:
                    self.notes_tree.insert("", "end", values=(note.get('IEN'), note.get('Title'), note.get('Date')))
            else:
                self.log_window.log("No notes found for this patient.")
        except Exception as e:
            # Log any errors during note fetching
            import traceback
            self.log_window.log(f"!!! FAILED to fetch patient notes: {e}")
            self.log_window.log(traceback.format_exc())

    

    def _get_recent_notes_for_current_patient(self):
        """
        Opens a dialog to get options for fetching recent notes, then calls
        _fetch_patient_notes with the selected parameters.
        """
        self.log_window.log(f"_get_recent_notes_for_current_patient called")
        if self.current_dfn:
            # Open the options window as a modal dialog
            options_window = RecentNotesOptionsWindow(self)
            self.wait_window(options_window) # Wait for the dialog to close
            
            # Retrieve results from the options window
            note_count = options_window.result_note_count
            doc_class_ien = options_window.result_doc_class_ien
            status = options_window.result_status
            
            # Map status string to VistA context integer
            context_map = {"All": 15, "Signed": 1, "Unsigned": 2}
            context = context_map.get(status, 15) # Default to "All" if status is not found
            
            if note_count is not None and doc_class_ien is not None:
                self._fetch_patient_notes(self.current_dfn, note_count, doc_class_ien, context)
        else:
            messagebox.showwarning("No Patient Selected", "Please select a patient first.")

    

    def _get_unsigned_notes_for_current_patient(self):
        """
        Fetches unsigned notes for the currently selected patient using default parameters.
        """
        self.log_window.log(f"_get_unsigned_notes_for_current_patient called")
        if self.current_dfn:
            # context=2 is specifically for unsigned notes as per VistA RPC context definitions
            self._fetch_patient_notes(self.current_dfn, 100, 3, context=2) # Default to 100 notes, Doc Class IEN 3 (Progress Notes)
        else:
            messagebox.showwarning("No Patient Selected", "Please select a patient first.")

    def _show_alert_list(self):
        """
        Fetches and displays the current user's alert list from VistA.
        """
        self.log_window.log(f"_show_alert_list called")
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA. Please connect first.")
            return
        try:
            # Calls the vista_client to retrieve alerts (RPC: ORQQAL LIST)
            alerts = self.vista_client.get_alerts()
            self.log_window.log(f"ORQQAL LIST Raw Reply: {alerts!r}")
            # Display alerts in a new window or log window
            messagebox.showinfo("Alert List", alerts)
        except Exception as e:
            self.log_window.log(f"Failed to retrieve alert list: {e}")
            messagebox.showerror("RPC Error", f"Failed to retrieve alert list: {e}")


    def _search_patient(self):
        """
        Initiates a patient search based on the input in the search bar.
        If successful, opens a patient selection dialog.
        """
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA. Please connect first.")
            return

        search_term = self.search_patient_entry.get()
        if not search_term:
            messagebox.showwarning("Search Error", "Please enter a patient name to search.")
            return

        self.log_window.log(f"Searching for patient: {search_term}")
        try:
            # Calls the vista_client to search for patients (RPC: ORWPT LIST ALL)
            patients = self.vista_client.search_patient(search_term)
            self.log_window.log(f"ORWPT LIST ALL Parsed Reply: {patients!r}")

            if patients:
                self.patients_data = patients # Store search results
                self._open_patient_selection() # Open selection dialog
            else:
                messagebox.showinfo("Search Results", "No patients found matching the search criteria.")

        except Exception as e:
            self.log_window.log(f"Failed to search for patients: {e}")
            messagebox.showerror("RPC Error", f"Failed to search for patients: {e}")

    def _add_patient_to_list(self):
        """
        Adds the currently selected patient to a persistent list within the GUI (if not already present).
        This functionality appears to be a placeholder or for a feature not fully implemented in the UI.
        """
        if self.current_dfn:
            # Check if patient is already in the list
            for item in self.patient_list_tree.get_children():
                if self.patient_list_tree.item(item, "values")[0] == self.current_dfn:
                    return
            patient_name = self.current_patient_label.cget("text").split(' (DFN:')[0]
            # self.patient_list_tree.insert("", "end", values=(self.current_dfn, patient_name)) # This line is commented out in the original code.

    def _set_patient_from_list(self):
        """
        Selects a patient from the patient list treeview and calls _select_patient.
        """
        selected_item = self.patient_list_tree.selection()
        if not selected_item:
            return
        dfn = self.patient_list_tree.item(selected_item[0], "values")[0]
        self._select_patient(dfn)

    def _on_patient_list_select(self, event):
        """
        Event handler for patient selection in a list (e.g., single click).
        This method needs 'patient_list_tree' to be defined and populated.
        """
        self._set_patient_from_list()

    def _on_note_double_click(self, event):
        """
        Event handler for double-clicking a note in the notes treeview.
        Fetches and displays the full content of the selected note.
        """
        if not self.notes_tree.selection():
            return
        item = self.notes_tree.selection()[0]
        values = self.notes_tree.item(item, "values")
        if not values:
            return
        ien = values[0] # The IEN (Internal Entry Number) of the note
        if not ien:
            return
        try:
            # Call vista_client to read the note content (RPC: ORWPT NOTE TEXT)
            note_text = self.vista_client.read_note_content(ien)
            self.log_window.log(f"--- Note IEN: {ien} ---\n{note_text}\n--- End Note IEN: {ien} ---")
        except Exception as e:
            self.log_window.log(f"ERROR: Failed to retrieve note text for IEN {ien}: {e}")
            messagebox.showerror("Error", f"Failed to retrieve note text: {e}")

    def __init__(self, master=None):
        """
        Initializes the main VistARPCGUI application window.
        Sets up the main window, log windows, and instantiates core client objects.
        """
        super().__init__()
        self.title("VistA RPC Client")
        self.geometry("600x800") # Main window dimensions

        # Initialize logging windows
        self.log_window = LogWindow(self)
        self.rpc_comm_window = RPCCommWindow(self) # New RPC Communication Log Window
        self.rpc_comm_window.withdraw() # Hide the RPC communication window initially

        # Position the log window next to the main window
        self.update_idletasks() # Ensure window dimensions are calculated
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_width = self.winfo_width() # This will now be 600
        log_width = 1020
        log_height = 800
        self.log_window.geometry(f"{log_width}x{log_height}+{(main_x + main_width)}+{main_y}") # Log window dimensions and position

        # Create a GUI logger instance that directs logs to the log_window
        gui_logger = GUILogger(self.log_window.log)
        # Instantiate the VistaRpcClient, passing both the general GUI logger
        # and a specific logger for raw RPC communication.
        self.vista_client = VistaRpcClient(logger=gui_logger, comm_logger=self.rpc_comm_window.log)
        # Instantiate the OrderEntry and LabOrderController, passing necessary dependencies
        self.order_entry = OrderEntry(self.vista_client)
        self.lab_order_controller = LabOrderController(self.order_entry, self.log_window, self)
        
        # Initialize application state variables
        self.locations = {}         # Stores location data (e.g., for encounters)
        self.providers = {}         # Stores provider data
        self.note_titles = {}       # Stores available note titles
        self.current_dfn = None     # DFN of the currently selected patient
        self.current_duz = None     # DUZ of the currently logged-in user
        self.current_order_category = None # Tracks the currently selected order category (e.g., "LAB", "RA")
        # self.param_entries = [] # Removed as RPC Call tab is gone (comment from original code)

        self._create_widgets() # Call method to build the GUI elements

    def _connect_to_vista(self):
        """
        Handles the connection attempt to the VistA server using credentials
        and context provided in the GUI. Updates UI state upon success or failure.
        """
        host = self.host_entry.get()
        port = self.port_entry.get()
        access = self.access_entry.get()
        verify = self.verify_entry.get()
        context = self.context_entry.get()

        if not all([host, port, access, verify, context]):
            messagebox.showerror("Connection Error", "All connection fields are required.")
            return

        try:
            self.log_window.log(f"Attempting to connect to {host}:{port}...")
            # Call the vista_client's connect method
            success = self.vista_client.connect_to_vista(host, port, access, verify, context)
            if success:
                self.log_window.log("Connection successful.")
                messagebox.showinfo("Success", "Successfully connected to VistA.")
                # Enable UI elements that require an active VistA connection
                self.get_patients_button.config(state=tk.NORMAL)
                self.search_patient_button.config(state=tk.NORMAL)
                self.get_recent_notes_button.config(state=tk.NORMAL)
                self.get_unsigned_notes_button.config(state=tk.NORMAL)
                self.show_alert_list_button.config(state=tk.NORMAL)
                self.save_note_button.config(state=tk.NORMAL)
                self.save_unsigned_button.config(state=tk.NORMAL)
                
                # Fetch user information (DUZ, Name) after successful login
                user_info = self.vista_client.get_user_info()
                self.current_duz = user_info.get("DUZ")
                doctor_name = user_info.get("Name")
                self.current_doctor_label.config(text=f"{doctor_name} (DUZ: {self.current_duz})")
                self.log_window.log(f"Logged in as {doctor_name} (DUZ: {self.current_duz}).")

                # Fetch available providers for the combobox
                provider_names, provider_map = self.vista_client.get_providers()
                self.providers = provider_map # Store map for IEN lookup
                self.provider_combobox['values'] = provider_names # Populate combobox
                if provider_names:
                    self.provider_combobox.set(provider_names[0]) # Set default selection

        except Exception as e:
            self.log_window.log(f"ERROR during connection: {e}")
            messagebox.showerror("Connection Error", f"An error occurred: {e}")

    def _get_doctor_patients(self):
        """
        Fetches patients associated with the selected provider (doctor) from VistA.
        Opens a patient selection dialog with the results.
        """
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA.")
            return

        selected_provider_name = self.provider_combobox.get()
        if not selected_provider_name or selected_provider_name == "N/A":
            messagebox.showwarning("Provider Error", "Please select a provider.")
            return
        
        provider_ien = self.providers.get(selected_provider_name)
        if not provider_ien:
            messagebox.showerror("Provider Error", f"Could not find IEN for provider: {selected_provider_name}")
            return

        self.log_window.log(f"Fetching patients for provider: {selected_provider_name} (IEN: {provider_ien})")
        try:
            # Call vista_client to get patients for a specific provider (RPC: ORQPT PROVIDER PATIENTS)
            patients = self.vista_client.get_doctor_patients(provider_ien)
            self.log_window.log(f"ORQPT PROVIDER PATIENTS Parsed Reply: {patients!r}")

            if patients:
                self.patients_data = patients # Store patient data
                self._open_patient_selection() # Open selection dialog
            else:
                messagebox.showinfo("Search Results", "No patients found for this provider.")

        except Exception as e:
            self.log_window.log(f"Failed to get provider patients: {e}")
            messagebox.showerror("RPC Error", f"Failed to get provider patients: {e}")

    def _open_patient_selection(self):
        """
        Opens a modal Toplevel window allowing the user to select a patient from a list.
        The list is populated with data from `self.patients_data`.
        """
        if not hasattr(self, 'patients_data') or not self.patients_data:
            return

        selection_window = tk.Toplevel(self)
        selection_window.title("Select Patient")
        selection_window.geometry("400x300")
        selection_window.transient(self) # Make it a transient window
        selection_window.grab_set() # Make it modal

        # Treeview to display patient DFN and Name
        tree = ttk.Treeview(selection_window, columns=("DFN", "Name"), show="headings")
        tree.heading("DFN", text="DFN")
        tree.heading("Name", text="Name")
        tree.pack(fill=tk.BOTH, expand=True)

        for patient in self.patients_data:
            tree.insert("", "end", values=(patient.get("DFN"), patient.get("Name")))

        def on_double_click(event):
            """
            Inner function to handle double-click event on the patient selection tree.
            Selects the patient and closes the selection window.
            """
            selected_item = tree.selection()
            if not selected_item:
                return
            dfn = tree.item(selected_item[0], "values")[0]
            self.log_window.log(f"Patient selected via double-click: DFN {dfn}")
            self._select_patient(dfn) # Call the main GUI's patient selection method
            selection_window.destroy()

        tree.bind("<Double-1>", on_double_click) # Bind double-click event

    def _save_note_internal(self, sign_note):
        """
        Internal method to handle saving a note to VistA, with an option to sign it.
        Gathers data from various GUI inputs (note content, title, encounter, ES code).
        Args:
            sign_note (bool): True to sign the note electronically, False to save unsigned.
        """
        if not self.current_dfn:
            messagebox.showwarning("Save Error", "No patient selected.")
            return

        title_item = self.note_title_combobox.get()
        if not title_item:
            messagebox.showwarning("Save Error", "No note title selected.")
            return
        title_ien = self.note_titles.get(title_item) # Get IEN from title

        encounter_item = self.encounter_tree.selection()
        if not encounter_item:
            messagebox.showwarning("Save Error", "No encounter selected.")
            return
        visit_str = encounter_item[0] # Get visit string (IEN;DATETIME;TYPE)
        location_ien = visit_str.split(';')[0] # Extract location IEN from visit string
        encounter_datetime = self.vista_client._get_fileman_timestamp() # Use current time as encounter time

        note_content = self.note_content_text.get("1.0", tk.END) # Get all text from content area
        es_code = self.es_code_entry.get() # Get electronic signature code

        if sign_note and not es_code:
            messagebox.showwarning("Signature Error", "Electronic signature is required to sign the note.")
            return

        try:
            self.log_window.log(f"Attempting to save note. Title IEN: {title_ien}, Sign: {sign_note}")
            # Call vista_client to create/save the note
            result = self.vista_client.create_note(
                patient_dfn=self.current_dfn,
                title_ien=title_ien,
                note_text=note_content,
                encounter_location_ien=location_ien,
                encounter_datetime=encounter_datetime,
                visit_str=visit_str,
                es_code=es_code if sign_note else None, # Only pass ES code if signing
                sign_note=sign_note
            )
            self.log_window.log(f"Save note result: {result}")
            messagebox.showinfo("Success", result)
            # Refresh patient notes after saving
            self._fetch_patient_notes(self.current_dfn, 100, 3)
        except Exception as e:
            self.log_window.log(f"ERROR saving note: {e}")
            messagebox.showerror("Save Error", f"Failed to save note: {e}")

    def _save_note(self):
        """
        Handler for saving a note with electronic signature.
        """
        self._save_note_internal(sign_note=True)

    def _save_note_unsigned(self):
        """
        Handler for saving an unsigned note.
        """
        self._save_note_internal(sign_note=False)

    def _open_rpc_comm_log(self):
        """
        Makes the RPC Communication Log window visible.
        """
        self.rpc_comm_window.deiconify() # De-minimizes or shows the window

    def get_current_location_ien(self):
        """
        Placeholder to return the IEN of the currently selected encounter location.
        Currently returns a hardcoded default. This needs to be made dynamic based
        on user selection in the encounter treeview.
        Returns:
            str: The IEN of the selected location.
        """
        # For now, return a hardcoded default. This will be made dynamic later.
        return "200" # Example: PRIMARY CARE IEN (hardcoded for demonstration)




    def _clear_lab_cache(self):
        """
        Clears the local cache file for lab tests (lab_tests.json).
        This forces the application to fetch a fresh list from VistA next time,
        useful if VistA's lab test configuration has changed.
        """
        if messagebox.askyesno("Confirm Refresh", "This will clear the local lab test cache. The list will be reloaded from the server the next time you open the lab category, which may be slow. Are you sure?"):
            self.log_window.log("User initiated clearing of lab test cache.")
            
            # Define the path to the cache file
            cache_file = 'static/lab_tests.json' # Assuming it's in the static folder
            try:
                if os.path.exists(cache_file):
                    os.remove(cache_file) # Delete the file
                    self.log_window.log(f"Removed cache file: {cache_file}")
                    messagebox.showinfo("Cache Cleared", "Lab test cache has been cleared. Please re-navigate to the lab category to load a fresh list from the server.")
                else:
                    messagebox.showinfo("Cache Cleared", "No lab test cache file found to clear.")
            except OSError as e:
                self.log_window.log(f"Error removing cache file: {e}")
                messagebox.showerror("Cache Error", f"Could not remove cache file: {e}")

    def _create_widgets(self):
        """
        Constructs the entire graphical user interface of the main application window.
        This includes connection controls, patient search, note display/entry,
        and order entry functionalities, organized into frames and notebooks.
        """
        # Configure the main window's grid layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Top frame for connection and controls
        top_frame = ttk.Frame(self)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top_frame.columnconfigure(0, weight=1)

        # Connection Frame (LabelFrame for visual grouping)
        conn_frame = ttk.LabelFrame(top_frame, text="VistA Connection", padding="10")
        conn_frame.grid(row=0, column=0, sticky="ew")

        # Configure columns within the connection frame for responsive layout
        conn_frame.columnconfigure(1, weight=1)
        conn_frame.columnconfigure(3, weight=1)

        # Host and Port input fields
        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.host_entry = ttk.Entry(conn_frame)
        self.host_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        self.host_entry.insert(0, "127.0.0.1") # Default host

        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.port_entry = ttk.Entry(conn_frame)
        self.port_entry.grid(row=0, column=3, padx=5, pady=2, sticky="ew")
        self.port_entry.insert(0, "9297") # Default port

        # Access Code and Verify Code input fields (password-masked)
        ttk.Label(conn_frame, text="Access Code:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.access_entry = ttk.Entry(conn_frame, show="*") # show="*" masks the input
        self.access_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.access_entry.insert(0, "DOCTOR1")

        ttk.Label(conn_frame, text="Verify Code:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.verify_entry = ttk.Entry(conn_frame, show="*")
        self.verify_entry.grid(row=1, column=3, padx=5, pady=2, sticky="ew")
        self.verify_entry.insert(0, "DOCTOR1.")

        # Application Context input field
        ttk.Label(conn_frame, text="App Context:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.context_entry = ttk.Entry(conn_frame)
        self.context_entry.grid(row=2, column=1, columnspan=3, padx=5, pady=2, sticky="ew")
        self.context_entry.insert(0, "OR CPRS GUI CHART") # Default context

        # Connect button
        self.connect_button = ttk.Button(conn_frame, text="Connect", command=self._connect_to_vista)
        self.connect_button.grid(row=0, column=4, rowspan=2, padx=10, pady=5, sticky="ns")

        # Button to open the RPC communication log
        self.open_rpc_comm_log_button = ttk.Button(conn_frame, text="Open RPC Comm Log", command=self._open_rpc_comm_log)
        self.open_rpc_comm_log_button.grid(row=2, column=4, padx=10, pady=5, sticky="ns")

        # Labels to display current patient and doctor information
        ttk.Label(conn_frame, text="Current Patient:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.current_patient_label = ttk.Label(conn_frame, text="N/A")
        self.current_patient_label.grid(row=3, column=1, columnspan=3, padx=5, pady=2, sticky="ew")

        ttk.Label(conn_frame, text="Current Doctor:").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.current_doctor_label = ttk.Label(conn_frame, text="N/A")
        self.current_doctor_label.grid(row=4, column=1, columnspan=3, padx=5, pady=2, sticky="ew")

        # Provider selection combobox
        ttk.Label(conn_frame, text="Provider:").grid(row=5, column=0, padx=5, pady=2, sticky="w")
        self.provider_combobox = ttk.Combobox(conn_frame, values=[], state="readonly")
        self.provider_combobox.grid(row=5, column=1, columnspan=3, padx=5, pady=2, sticky="ew")
        self.provider_combobox.set("N/A") # Default text

        # Main Paned Window for resizable sections
        main_pane = ttk.PanedWindow(self, orient=tk.VERTICAL)
        main_pane.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Raw RPC Response Display (ScrolledText)
        # This area is intended to show raw responses from VistA RPC calls for debugging.
        self.raw_response_text = scrolledtext.ScrolledText(main_pane, wrap=tk.WORD, height=10)
        # self.raw_response_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10) # Commented out in original
        # The main_pane.add method is used to add widgets to a PanedWindow
        main_pane.add(self.raw_response_text, weight=1) # The raw response text is now part of the paned window


        # Top pane for controls (within the main_pane)
        controls_pane = ttk.Frame(main_pane, padding="5")
        main_pane.add(controls_pane, weight=0) # Add to paned window, with fixed size
        controls_pane.columnconfigure(0, weight=1)
        controls_pane.rowconfigure(0, weight=1)

        # Notebook widget for tabbed interface (Patient Selection, Add Note, Order Entry)
        notebook = ttk.Notebook(controls_pane)
        notebook.grid(row=0, column=0, sticky="nsew")



        # Patient Tab
        patient_tab = ttk.Frame(notebook, padding="10")
        notebook.add(patient_tab, text="Patient Selection")
        patient_tab.columnconfigure(1, weight=1)

        # Patient DFN input and "Get My Patients" button
        ttk.Label(patient_tab, text="Patient DFN:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.dfn_entry = ttk.Entry(patient_tab)
        self.dfn_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.dfn_entry.insert(0, "100001") # Default DFN for testing

        self.get_patients_button = ttk.Button(patient_tab, text="Get My Patients", command=self._get_doctor_patients, state=tk.DISABLED)
        self.get_patients_button.grid(row=0, column=2, padx=5, pady=5)

        # Patient search by name
        ttk.Label(patient_tab, text="Search Name:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.search_patient_entry = ttk.Entry(patient_tab)
        self.search_patient_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.search_patient_button = ttk.Button(patient_tab, text="Search", command=self._search_patient, state=tk.DISABLED)
        self.search_patient_button.grid(row=1, column=2, padx=5, pady=5)

        # Buttons for fetching notes and alerts
        self.get_recent_notes_button = ttk.Button(patient_tab, text="Get Recent Notes", command=self._get_recent_notes_for_current_patient, state=tk.DISABLED)
        self.get_recent_notes_button.grid(row=2, column=0, columnspan=3, padx=5, pady=10, sticky="ew")

        self.get_unsigned_notes_button = ttk.Button(patient_tab, text="Get Unsigned Notes", command=self._get_unsigned_notes_for_current_patient, state=tk.DISABLED)
        self.get_unsigned_notes_button.grid(row=3, column=0, columnspan=3, padx=5, pady=10, sticky="ew")

        self.show_alert_list_button = ttk.Button(patient_tab, text="Show Alert List", command=self._show_alert_list, state=tk.DISABLED)
        self.show_alert_list_button.grid(row=4, column=0, columnspan=3, padx=5, pady=10, sticky="ew")

        # Patient Notes Treeview to display a list of notes
        self.notes_tree = ttk.Treeview(patient_tab, columns=("IEN", "Title", "Date"), show="headings")
        self.notes_tree.heading("IEN", text="IEN")
        self.notes_tree.heading("Title", text="Title")
        self.notes_tree.heading("Date", text="Date")
        self.notes_tree.column("IEN", width=100)
        self.notes_tree.column("Title", width=300)
        self.notes_tree.column("Date", width=150)
        self.notes_tree.grid(row=4, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        patient_tab.rowconfigure(4, weight=1) # Allow treeview to expand vertically
        self.notes_tree.bind("<Double-1>", self._on_note_double_click) # Bind double-click to view note content

        # Add Note Tab
        add_note_tab = ttk.Frame(notebook, padding="10")
        notebook.add(add_note_tab, text="Add Note")
        add_note_tab.columnconfigure(1, weight=1)

        # Note Title selection combobox
        ttk.Label(add_note_tab, text="Note Title:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.note_title_combobox = ttk.Combobox(add_note_tab, state="readonly")
        self.note_title_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Encounters Treeview and Refresh button
        ttk.Label(add_note_tab, text="Encounters:").grid(row=1, column=0, padx=5, pady=5, sticky="nw")
        self.encounter_tree = ttk.Treeview(add_note_tab, columns=("Location", "Date"), show="headings", height=5)
        self.encounter_tree.heading("Location", text="Location")
        self.encounter_tree.heading("Date", text="Date")
        self.encounter_tree.column("Location", width=200)
        self.encounter_tree.column("Date", width=150)
        self.encounter_tree.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.refresh_encounters_button = ttk.Button(add_note_tab, text="Refresh Encounters", command=self._fetch_patient_encounters, state=tk.DISABLED)
        self.refresh_encounters_button.grid(row=1, column=2, padx=5, pady=5)


        # Note Content input area
        ttk.Label(add_note_tab, text="Note Content:").grid(row=2, column=0, padx=5, pady=5, sticky="nw")
        self.note_content_text = scrolledtext.ScrolledText(add_note_tab, wrap=tk.WORD, height=10)
        self.note_content_text.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="nsew")
        add_note_tab.rowconfigure(2, weight=1)

        # Electronic Signature Code input
        ttk.Label(add_note_tab, text="Electronic Signature:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.es_code_entry = ttk.Entry(add_note_tab, show="*")
        self.es_code_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # Save Note and Save Unsigned buttons
        self.save_note_button = ttk.Button(add_note_tab, text="Save Note", command=self._save_note, state=tk.DISABLED)
        self.save_note_button.grid(row=4, column=1, padx=5, pady=10, sticky="e")

        self.save_unsigned_button = ttk.Button(add_note_tab, text="Save Unsigned", command=self._save_note_unsigned, state=tk.DISABLED)
        self.save_unsigned_button.grid(row=4, column=0, padx=5, pady=10, sticky="e")

        # Order Entry Tab
        order_entry_tab = ttk.Frame(notebook, padding="10")
        notebook.add(order_entry_tab, text="Order Entry")
        order_entry_tab.columnconfigure(1, weight=1)

        # Order Menu Treeview (for displaying order categories and orderable items)
        self.order_menu_tree = ttk.Treeview(order_entry_tab, columns=("IEN", "Name"), show="headings")
        self.order_menu_tree.heading("IEN", text="IEN")
        self.order_menu_tree.heading("Name", text="Name")
        self.order_menu_tree.column("IEN", width=100)
        self.order_menu_tree.column("Name", width=300)
        self.order_menu_tree.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        order_entry_tab.rowconfigure(0, weight=1)
        self.order_menu_tree.bind("<Double-1>", self._on_order_menu_double_click)

        # Buttons for navigation and refreshing lab cache
        self.back_to_categories_button = ttk.Button(order_entry_tab, text="Back to Categories", command=self._back_to_categories, state=tk.DISABLED)
        self.back_to_categories_button.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        self.refresh_labs_button = ttk.Button(order_entry_tab, text="Refresh Lab List", command=self._clear_lab_cache)
        self.refresh_labs_button.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

    def _load_order_menus(self, patient_dfn):
        """
        Loads and displays the top-level order menus (categories) from VistA.
        This is typically called after a patient is selected.
        Args:
            patient_dfn (str): The DFN of the currently selected patient.
        """
        self.log_window.log("Loading order menus...")
        try:
            # Get top-level order menus using the order_entry component
            menu_items = self.order_entry.get_main_order_menu()
            self.log_window.log(f"Main order menu items: {menu_items!r}")

            self.order_menu_tree.delete(*self.order_menu_tree.get_children()) # Clear existing items

            if menu_items:
                for item in menu_items:
                    self.order_menu_tree.insert("", "end", values=(item.get('IEN'), item.get('Name')))
            else:
                self.log_window.log("No main menu items returned.")
            # Disable back button when at the top-level categories
            self.back_to_categories_button.config(state=tk.DISABLED)

        except Exception as e:
            self.log_window.log(f"ERROR - _load_order_menus: Failed to load order menus: {e}")
            messagebox.showerror("RPC Error", f"Failed to load order menus: {e}")

    def _on_order_menu_double_click(self, event):
        """
        Event handler for double-clicking an item in the order menu treeview.
        If a category is double-clicked, it loads orderable items for that category.
        If an orderable item is double-clicked, it initiates the order process
        (e.g., for labs).
        Args:
            event: The Tkinter event object.
        """
        if not self.order_menu_tree.selection():
            return
        item = self.order_menu_tree.selection()[0]
        values = self.order_menu_tree.item(item, "values")
        if not values:
            return
        selected_ien = values[0]
        selected_name = values[1]

        if not self.current_dfn:
            messagebox.showwarning("Patient Error", "Please select a patient first.")
            return

        if self.current_order_category is None: # Currently displaying main categories
            # If a main category is selected, fetch its sub-items
            category_code = selected_ien
            category_name = selected_name
            self.log_window.log(f"Selected order category: {category_name} (Code: {category_code})")
            try:
                # Get orderable items within the selected category
                orderable_items = self.order_entry.get_order_group_items(category_code, self.current_dfn)
                
                self.order_menu_tree.delete(*self.order_menu_tree.get_children()) # Clear current display

                if isinstance(orderable_items, list):
                    if orderable_items:
                        for order_item in orderable_items:
                            self.order_menu_tree.insert("", "end", values=(order_item.get('IEN'), order_item.get('Name')))
                        self.log_window.log(f"Inserted {len(orderable_items)} orderable items into order_menu_tree for {category_name}.")
                        self.current_order_category = category_code # Set current category state
                        self.back_to_categories_button.config(state=tk.NORMAL) # Enable back button
                    else:
                        self.log_window.log(f"No orderable items found for {category_name}.")
                else:
                    # If orderable_items is not a list, it might be a direct message (e.g., error)
                    messagebox.showinfo(f"Orderable Items for {category_name}", orderable_items)

            except Exception as e:
                self.log_window.log(f"ERROR - _on_order_menu_double_click: Failed to get orderable items for {category_name}: {e}")
                messagebox.showerror("RPC Error", f"Failed to get orderable items for {category_name}: {e}")
        else: # Currently displaying orderable items within a category
            # If an orderable item is selected, process it based on the category
            self.log_window.log(f"Selected orderable item: {selected_name} (IEN: {selected_ien}) from category {self.current_order_category}")
            
            if self.current_order_category == "LAB":
                # For lab orders, delegate to the LabOrderController
                self.log_window.log(f"Calling handle_lab_order_selection with IEN: {selected_ien}, Name: {selected_name}")
                self.lab_order_controller.handle_lab_order_selection(selected_ien, selected_name)
            else:
                messagebox.showinfo("Orderable Item Selected", f"You selected: {selected_name} (IEN: {selected_ien})")
                # TODO: Implement logic for other order types

    def _back_to_categories(self):
        """
        Navigates back to displaying the main order categories in the order menu treeview.
        Resets the current order category state.
        """
        self.log_window.log("Navigating back to main order categories.")
        self.order_menu_tree.delete(*self.order_menu_tree.get_children()) # Clear current display
        self._load_order_menus(self.current_dfn) # Reload the top-level categories
        self.current_order_category = None # Reset the state variable
        self.back_to_categories_button.config(state=tk.DISABLED) # Disable back button

if __name__ == "__main__":
    """
    Main entry point of the application.
    Loads RPC configuration, initializes the GUI, and starts the Tkinter event loop.
    Includes basic error handling for startup issues.
    """
    try:
        # --- Load RPC Configuration ---
        # Define paths to the configuration files for RPC names and documentation
        project_root = os.path.dirname(os.path.abspath(__file__))
        rpc_list_file = os.path.join(project_root, 'static', 'cprs_rpc_list.txt')
        rpc_doc_file = os.path.join(project_root, 'static', 'cprs_rpc_documentation.md')

        # Use the RPCConfigLoader to parse RPC names and their details
        print("Loading RPC configuration...")
        loader = RPCConfigLoader(rpc_list_file, rpc_doc_file)
        rpc_names, rpc_info = loader.load_all() # Load all RPC names and their detailed info
        print("RPC configuration loaded.")

        # --- Create and run the GUI Application ---
        print("Starting GUI application...")
        app = VistARPCGUI() # Instantiate the main GUI application
        app.mainloop() # Start the Tkinter event loop, which handles all GUI interactions
        print("GUI application closed.")

    except Exception as e:
        # Catch any unexpected errors during application startup or runtime
        import traceback
        error_message = f"An unexpected error occurred on startup:\n\n{e}"
        traceback_str = traceback.format_exc() # Get full traceback for debugging
        print(f"FATAL ERROR: {error_message}\n{traceback_str}")
        # Use tkinter to show a popup even if the main app failed to initialize fully
        root = tk.Tk()
        root.withdraw() # Hide the main Tkinter window that gets created
        messagebox.showerror("Fatal Error", error_message) # Display error in a message box
        root.destroy() 