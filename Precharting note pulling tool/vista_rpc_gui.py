import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import sys
import os
import json
import re
import time

# Add the directory containing the vavista package to the Python path
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Add the vavista-rpc-master directory to the Python path

from vista_rpc_client import VistaRpcClient

class GUILogger:
    def __init__(self, log_func):
        self.log_func = log_func

    def logInfo(self, tag, msg):
        self.log_func(f"{tag}: {msg}")

    def logError(self, tag, msg):
        self.log_func(f"ERROR - {tag}: {msg}")


class LogWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Log")
        self.geometry("800x500")
        self.log_text = scrolledtext.ScrolledText(self, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

    def log(self, message):
        if not self.log_text.winfo_exists():
            return
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)


class RPCCommWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("RPC Communication Log")
        self.geometry("500x500")
        self.log_text = scrolledtext.ScrolledText(self, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

    def log(self, message):
        if not self.log_text.winfo_exists():
            return
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)


class RecentNotesOptionsWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.title("Recent Notes Options")
        self.geometry("300x200") # Increased height for new field
        self.transient(master)  # Make it a transient window relative to master
        self.grab_set()      # Make it modal

        self.result_note_count = None
        self.result_doc_class_ien = None

        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Number of Notes:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.note_count_entry = ttk.Entry(main_frame)
        self.note_count_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.note_count_entry.insert(0, "100") # Default value to 100, matching Delphi

        ttk.Label(main_frame, text="Doc Class IEN:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.doc_class_ien_entry = ttk.Entry(main_frame)
        self.doc_class_ien_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.doc_class_ien_entry.insert(0, "3") # Default value to 3 (Progress Notes)

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="Get Notes", command=self._on_get_notes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.LEFT, padx=5)

    def _on_get_notes(self):
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
            self.destroy()
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter valid numbers for notes and document class IEN.")

    def _on_cancel(self):
        self.result_note_count = None
        self.result_doc_class_ien = None
        self.destroy()


class Widgets:
    def __init__(self, master):
        pass


class VistARPCGUI(tk.Tk):













    def __init__(self):
        super().__init__()
        self.title("VistA RPC Client")
        self.geometry("800x900") # Main window dimensions

        self.log_window = LogWindow(self)
        self.rpc_comm_window = RPCCommWindow(self) # New RPC Communication Log Window
        self.rpc_comm_window.withdraw() # Hide the window initially
        self.update_idletasks()
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_width = self.winfo_width() # This will now be 600
        log_width = 1020
        log_height = 800
        self.log_window.geometry(f"{log_width}x{log_height}+{(main_x + main_width)}+{main_y}") # Log window dimensions and position



        gui_logger = GUILogger(self.log_window.log)
        # Pass the new comm_logger to VistAClient
        self.vista_client = VistaRpcClient(logger=gui_logger, comm_logger=self.rpc_comm_window.log) # Instantiate the VistaRpcClient
        self.locations = {}
        self.providers = {}
        self.current_duz = None # Store current user DUZ

        self._create_widgets()

    def _create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Top frame for connection and controls
        top_frame = ttk.Frame(self)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top_frame.columnconfigure(0, weight=1)

        # Connection Frame
        conn_frame = ttk.LabelFrame(top_frame, text="VistA Connection", padding="10")
        conn_frame.grid(row=0, column=0, sticky="ew")

        conn_frame.columnconfigure(1, weight=1)
        conn_frame.columnconfigure(3, weight=1)

        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.host_entry = ttk.Entry(conn_frame)
        self.host_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        self.host_entry.insert(0, "127.0.0.1")

        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.port_entry = ttk.Entry(conn_frame)
        self.port_entry.grid(row=0, column=3, padx=5, pady=2, sticky="ew")
        self.port_entry.insert(0, "9297")

        ttk.Label(conn_frame, text="Access Code:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.access_entry = ttk.Entry(conn_frame, show="*")
        self.access_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.access_entry.insert(0, "DOCTOR1")

        ttk.Label(conn_frame, text="Verify Code:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.verify_entry = ttk.Entry(conn_frame, show="*")
        self.verify_entry.grid(row=1, column=3, padx=5, pady=2, sticky="ew")
        self.verify_entry.insert(0, "DOCTOR1.")

        ttk.Label(conn_frame, text="App Context:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.context_entry = ttk.Entry(conn_frame)
        self.context_entry.grid(row=2, column=1, columnspan=3, padx=5, pady=2, sticky="ew")
        self.context_entry.insert(0, "OR CPRS GUI CHART")

        self.connect_button = ttk.Button(conn_frame, text="Connect", command=self._connect_to_vista)
        self.connect_button.grid(row=0, column=4, rowspan=2, padx=10, pady=5, sticky="ns")

        self.open_rpc_comm_log_button = ttk.Button(conn_frame, text="Open RPC Comm Log", command=self._open_rpc_comm_log)
        self.open_rpc_comm_log_button.grid(row=2, column=4, padx=10, pady=5, sticky="ns")

        ttk.Label(conn_frame, text="Current Patient:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.current_patient_label = ttk.Label(conn_frame, text="N/A")
        self.current_patient_label.grid(row=3, column=1, columnspan=3, padx=5, pady=2, sticky="ew")

        ttk.Label(conn_frame, text="Current Doctor:").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.current_doctor_label = ttk.Label(conn_frame, text="N/A")
        self.current_doctor_label.grid(row=4, column=1, columnspan=3, padx=5, pady=2, sticky="ew")

        # Main Paned Window
        main_pane = ttk.PanedWindow(self, orient=tk.VERTICAL)
        main_pane.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)



        # Top pane for controls
        controls_pane = ttk.Frame(main_pane, padding="5")
        main_pane.add(controls_pane, weight=0)
        controls_pane.columnconfigure(0, weight=1)
        controls_pane.rowconfigure(0, weight=1)

        # Notebook for RPC and Patient controls
        notebook = ttk.Notebook(controls_pane)
        notebook.grid(row=0, column=0, sticky="nsew")





        # Patient List and Note Retrieval Tab Widgets
        patient_list_tab = ttk.Frame(notebook, padding="10")
        notebook.add(patient_list_tab, text="Iterate patient list and get notes")
        patient_list_tab.columnconfigure(1, weight=1) # Allow the entry fields to expand
        patient_list_tab.rowconfigure(4, weight=1) # Allow the selected patients treeview to expand

        # Patient Search Section
        ttk.Label(patient_list_tab, text="Search Patient Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.patient_list_search_entry = ttk.Entry(patient_list_tab)
        self.patient_list_search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.patient_list_search_button = ttk.Button(patient_list_tab, text="Search", command=self._search_patients_for_list, state=tk.DISABLED)
        self.patient_list_search_button.grid(row=0, column=2, padx=5, pady=5)

        # Search Results Treeview
        self.patient_search_results_tree = ttk.Treeview(patient_list_tab, columns=("DFN", "Name"), show="headings", height=10)
        self.patient_search_results_tree.heading("DFN", text="DFN")
        self.patient_search_results_tree.heading("Name", text="Patient Name")
        self.patient_search_results_tree.column("DFN", width=100)
        self.patient_search_results_tree.column("Name", width=250)
        self.patient_search_results_tree.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        self.patient_search_results_tree.bind("<Double-1>", self._add_selected_patient_to_list)

        # Add Patient Button
        self.add_patient_to_list_button = ttk.Button(patient_list_tab, text="Add Selected Patient", command=self._add_selected_patient_to_list, state=tk.DISABLED)
        self.add_patient_to_list_button.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        # Selected Patients Listbox
        ttk.Label(patient_list_tab, text="Selected Patients:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.selected_patients_tree = ttk.Treeview(patient_list_tab, columns=("DFN", "Name"), show="headings", height=10)
        self.selected_patients_tree.heading("DFN", text="DFN")
        self.selected_patients_tree.heading("Name", text="Patient Name")
        self.selected_patients_tree.column("DFN", width=100)
        self.selected_patients_tree.column("Name", width=250)
        self.selected_patients_tree.grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        self.selected_patients_tree.bind("<Double-1>", self._remove_selected_patient_from_list)

        # Remove Patient Button
        self.remove_patient_from_list_button = ttk.Button(patient_list_tab, text="Remove Selected Patient", command=self._remove_selected_patient_from_list, state=tk.DISABLED)
        self.remove_patient_from_list_button.grid(row=5, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        # Fetch and Display Notes Button
        ttk.Label(patient_list_tab, text="Number of Notes to Fetch (n):").grid(row=6, column=0, padx=5, pady=5, sticky="w")
        self.num_notes_to_fetch_entry = ttk.Entry(patient_list_tab)
        self.num_notes_to_fetch_entry.grid(row=6, column=1, padx=5, pady=5, sticky="ew")
        self.num_notes_to_fetch_entry.insert(0, "3") # Default to 3 notes



        self.fetch_all_notes_button = ttk.Button(patient_list_tab, text="Fetch and Display Notes for Selected Patients", command=self._fetch_and_display_all_notes, state=tk.DISABLED)
        self.fetch_all_notes_button.grid(row=7, column=0, columnspan=3, padx=5, pady=10, sticky="ew")









    def _connect_to_vista(self):
        host = self.host_entry.get()
        port = self.port_entry.get()
        access = self.access_entry.get()
        verify = self.verify_entry.get()
        context = self.context_entry.get()

        try:
            self.log_window.log("Attempting to connect to VistA...")
            self.vista_client.connect_to_vista(host, port, access, verify, context)
            self.log_window.log("Connection successful!")




            # Enable new patient list and note retrieval buttons
            self.patient_list_search_button.config(state=tk.NORMAL)
            self.add_patient_to_list_button.config(state=tk.NORMAL)
            self.remove_patient_from_list_button.config(state=tk.NORMAL)
            self.fetch_all_notes_button.config(state=tk.NORMAL)
            self.connect_button.config(text="Connected", state=tk.DISABLED)
            # Update doctor info
            self._update_doctor_info()

        except Exception as e:
            self.log_window.log(f"Connection failed: {e}")
            messagebox.showerror("Connection Error", f"Failed to connect: {e}")
            self.vista_client.connection = None
            self.connect_button.config(text="Connect", state=tk.NORMAL)

    def _update_doctor_info(self):
        try:
            user_info = self.vista_client.get_user_info()
            if user_info and user_info.get("DUZ") and user_info.get("Name"):
                duz = user_info["DUZ"]
                name = user_info["Name"]
                self.current_doctor_label.config(text=f"{name} (DUZ: {duz})")
                self.providers[name] = duz
                # self.provider_combobox['values'] = [name]
                # self.provider_combobox.set(name)
                self.current_duz = duz # Store the current DUZ
            else:
                self.current_doctor_label.config(text="N/A")
        except Exception as e:
            self.log_window.log(f"Failed to get doctor info: {e}")
            self.current_doctor_label.config(text="N/A")

    def _open_rpc_comm_log(self):
        self.rpc_comm_window.deiconify() # Show the window if it's minimized or hidden
        self.rpc_comm_window.lift() # Bring to front



    def _get_doctor_patients(self):
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA. Please connect first.")
            return

        self.log_window.log("Attempting to retrieve current user's IEN...")
        try:
            user_info = self.vista_client.get_user_info()
            self.log_window.log(f"ORWU USERINFO Raw Reply: {user_info!r}")
            
            if user_info and user_info.get("DUZ") and user_info.get("Name"):
                provider_ien = user_info["DUZ"]
                self.log_window.log(f"Retrieved Provider IEN: {provider_ien}")

                self.log_window.log(f"Invoking ORQPT PROVIDER PATIENTS with IEN: {provider_ien}")
                patients = self.vista_client.get_doctor_patients(provider_ien)
                self.log_window.log(f"ORQPT PROVIDER PATIENTS Parsed Reply: {patients!r}")

                if patients:
                    formatted_output = "Patients for current user (IEN: " + provider_ien + "):\n"
                    for patient in patients:
                        formatted_output += f"DFN: {patient['DFN']}, Name: {patient['Name']}\n"
                    self.log_window.log(formatted_output)
                    self.patients_data = patients
                else:
                    self.log_window.log("No patients found for this provider or empty response.")
                self.log_window.log("Successfully retrieved and displayed patients.")

            else:
                self.log_window.log("Could not parse provider IEN from ORWU USERINFO response.")
                messagebox.showerror("RPC Error", "Could not retrieve provider IEN.")

        except Exception as e:
            self.log_window.log(f"Failed to get doctor's patients: {e}")
            messagebox.showerror("RPC Error", f"Failed to get doctor's patients: {e}")

    def _search_patients_for_list(self):
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA. Please connect first.")
            return

        search_term = self.patient_list_search_entry.get()
        if not search_term:
            messagebox.showwarning("Search Error", "Please enter a patient name to search.")
            return

        self.log_window.log(f"Searching for patient: {search_term}")
        try:
            patients = self.vista_client.search_patient(search_term)
            self.log_window.log(f"ORWPT LIST ALL Parsed Reply: {patients!r}")

            # Clear previous results
            for item in self.patient_search_results_tree.get_children():
                self.patient_search_results_tree.delete(item)

            if patients:
                for patient in patients:
                    self.patient_search_results_tree.insert("", "end", values=(patient["DFN"], patient["Name"]))
            else:
                messagebox.showinfo("Search Results", "No patients found matching the search criteria.")

        except Exception as e:
            self.log_window.log(f"Failed to search for patients: {e}")
            messagebox.showerror("RPC Error", f"Failed to search for patients: {e}")

    def _add_selected_patient_to_list(self, event=None):
        selected_item = self.patient_search_results_tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a patient from the search results to add.")
            self.log_window.log("Patient Selection: No patient selected from search results.")
            return

        # Get patient info from the selected item
        dfn, name = self.patient_search_results_tree.item(selected_item[0], "values")

        # Check if already in the selected list
        for item in self.selected_patients_tree.get_children():
            if self.selected_patients_tree.item(item, "values")[0] == dfn:
                messagebox.showinfo("Duplicate", f"{name} (DFN: {dfn}) is already in the selected patients list.")
                self.log_window.log(f"Patient Selection: Patient {name} (DFN: {dfn}) already in selected list.")
                return

        self.selected_patients_tree.insert("", "end", values=(dfn, name))
        self.log_window.log(f"Patient Selection: Added patient {name} (DFN: {dfn}) to the selected list.")

    def _remove_selected_patient_from_list(self, event=None):
        selected_item = self.selected_patients_tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a patient from the 'Selected Patients' list to remove.")
            return

        dfn, name = self.selected_patients_tree.item(selected_item[0], "values")
        self.selected_patients_tree.delete(selected_item[0])
        self.log_window.log(f"Removed patient {name} (DFN: {dfn}) from the selected list.")

    def _fetch_and_display_all_notes(self):
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA. Please connect first.")
            return

        selected_patients = self.selected_patients_tree.get_children()
        if not selected_patients:
            messagebox.showwarning("No Patients Selected", "Please add patients to the 'Selected Patients' list first.")
            return

        self.log_window.log(f"Fetching notes for selected patients...\n\n")
        self.log_window.log("Starting note retrieval for selected patients.\n")

        for item_id in selected_patients:
            dfn, name = self.selected_patients_tree.item(item_id, "values")
            self.log_window.log(f"Fetching notes for patient: {name} (DFN: {dfn})\n")
            
            try:
                # Fetch up to 3 notes for the patient (doc_class_ien=3 for Progress Notes, context=1 for signed notes)
                notes = self.vista_client.fetch_patient_notes(dfn, doc_class_ien=3, context=1, max_docs=3)
                
                self.log_window.log(f"--- Patient: {name} (DFN: {dfn}) ---\n")
                
                if notes:
                    self.log_window.log(f"Found {len(notes)} notes for {name}. Processing first 3.\n")
                    for i, note in enumerate(notes):
                        if i >= 3: # Ensure only first 3 notes are processed
                            self.log_window.log("Reached limit of 3 notes for this patient.\n")
                            break
                        note_ien = note.get('IEN')
                        note_title = note.get('Title')
                        note_date = note.get('Date')
                        
                        self.log_window.log(f"  Fetching content for note: {note_title} (IEN: {note_ien})\n")
                        note_content = self.vista_client.read_note_content(note_ien)
                        
                        self.log_window.log(f"  Note {i+1} - Title: {note_title}, Date: {note_date}\n")
                        self.log_window.log(f"  Content:\n{note_content}\n\n")
                else:
                    self.log_window.log("  No notes found for this patient.\n\n")
                    self.log_window.log(f"No notes found for {name}.\n")

            except Exception as e:
                self.log_window.log(f"  ERROR fetching notes for {name} (DFN: {dfn}): {e}\n\n")
        
        self.log_window.log("--- Finished fetching notes ---\n")
        self.log_window.log("Completed note retrieval for all selected patients.\n")






    def _search_patients_for_list(self):
        """Searches for patients based on the input in patient_list_search_entry and populates the patient_search_results_tree."""
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA. Please connect first.")
            self.log_window.logError("Patient Search", "Not connected to VistA.")
            return

        search_term = self.patient_list_search_entry.get()
        if not search_term:
            messagebox.showwarning("Search Error", "Please enter a patient name to search.")
            self.log_window.log("Patient Search: No search term entered.")
            return

        self.log_window.log(f"Patient Search: Searching for patient: {search_term}")
        try:
            patients = self.vista_client.search_patient(search_term)
            self.log_window.log(f"Patient Search: ORWPT LIST ALL Parsed Reply: {patients!r}")

            # Clear previous results
            for item in self.patient_search_results_tree.get_children():
                self.patient_search_results_tree.delete(item)

            if patients:
                for patient in patients:
                    self.patient_search_results_tree.insert("", "end", values=(patient["DFN"], patient["Name"]))
                self.log_window.log(f"Patient Search: Found {len(patients)} patients.")
            else:
                messagebox.showinfo("Search Results", "No patients found matching the search criteria.")
                self.log_window.log("Patient Search: No patients found.")

        except Exception as e:
            self.log_window.log(f"Patient Search: Failed to search for patients: {e}")
            messagebox.showerror("RPC Error", f"Failed to search for patients: {e}")

    def _add_selected_patient_to_list(self, event=None):
        """Adds the selected patient from the search results to the selected patients list."""
        selected_item = self.patient_search_results_tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a patient from the search results to add.")
            self.log_window.log("Patient Selection: No patient selected from search results.")
            return

        # Get patient info from the selected item
        dfn, name = self.patient_search_results_tree.item(selected_item[0], "values")

        # Check if already in the selected list
        for item in self.selected_patients_tree.get_children():
            if self.selected_patients_tree.item(item, "values")[0] == dfn:
                messagebox.showinfo("Duplicate", f"{name} (DFN: {dfn}) is already in the selected patients list.")
                self.log_window.log(f"Patient Selection: Patient {name} (DFN: {dfn}) already in selected list.")
                return

        self.selected_patients_tree.insert("", "end", values=(dfn, name))
        self.log_window.log(f"Patient Selection: Added patient {name} (DFN: {dfn}) to the selected list.")

    def _remove_selected_patient_from_list(self, event=None):
        """Removes the selected patient from the selected patients list."""
        selected_item = self.selected_patients_tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a patient from the 'Selected Patients' list to remove.")
            self.log_window.log("Patient Selection: No patient selected from selected list to remove.")
            return

        dfn, name = self.selected_patients_tree.item(selected_item[0], "values")
        self.selected_patients_tree.delete(selected_item[0])
        self.log_window.log(f"Patient Selection: Removed patient {name} (DFN: {dfn}) from the selected list.")

    def _fetch_and_display_all_notes(self):
        """Fetches and displays the specified number of notes for all selected patients to the log window."""
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA. Please connect first.")
            self.log_window.log("Note Retrieval: Not connected to VistA.")
            return

        selected_patients = self.selected_patients_tree.get_children()
        if not selected_patients:
            messagebox.showwarning("No Patients Selected", "Please add patients to the 'Selected Patients' list first.")
            self.log_window.log("Note Retrieval: No patients in selected list.")
            return

        try:
            num_notes_to_fetch = int(self.num_notes_to_fetch_entry.get())
            if num_notes_to_fetch <= 0:
                messagebox.showwarning("Invalid Input", "Number of notes to fetch must be a positive integer.")
                self.log_window.log("Note Retrieval: Invalid number of notes specified.")
                return
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid number for notes to fetch.")
            self.log_window.log("Note Retrieval: Invalid number of notes format.")
            return

        self.log_window.log("\n" + "="*80)
        self.log_window.log("Starting note retrieval for selected patients...")
        self.log_window.log("="*80 + "\n")

        for item_id in selected_patients:
            dfn, name = self.selected_patients_tree.item(item_id, "values")
            self.log_window.log(f"\n{'='*10} Fetching notes for patient: {name} (DFN: {dfn}) {'='*10}\n")
            
            try:
                # Fetch up to num_notes_to_fetch for the patient (doc_class_ien=3 for Progress Notes, context=1 for signed notes)
                notes = self.vista_client.fetch_patient_notes(dfn, doc_class_ien=3, context=1, max_docs=num_notes_to_fetch)
                
                if notes:
                    self.log_window.log(f"Found {len(notes)} notes for {name}. Processing up to {num_notes_to_fetch}.\n")
                    for i, note in enumerate(notes):
                        if i >= num_notes_to_fetch: # Ensure only up to num_notes_to_fetch are processed
                            self.log_window.log("Reached limit of notes for this patient.\n")
                            break
                        note_ien = note.get('IEN')
                        note_title = note.get('Title')
                        note_date = note.get('Date')
                        
                        self.log_window.log(f"  {'--'*5} Note {i+1} - Title: {note_title}, Date: {note_date} (IEN: {note_ien}) {'--'*5}")
                        note_content = self.vista_client.read_note_content(note_ien)
                        
                        self.log_window.log(f"  Content:\n{note_content}\n")
                else:
                    self.log_window.log("  No notes found for this patient.\n")

            except Exception as e:
                self.log_window.log(f"  ERROR fetching notes for {name} (DFN: {dfn}): {e}\n")
        
        self.log_window.log("\n" + "="*80)
        self.log_window.log("Completed note retrieval for all selected patients.")
        self.log_window.log("="*80 + "\n")




class PatientSelectionWindow(tk.Toplevel):
    def __init__(self, master, patients_data):
            super().__init__(master)
            self.master = master
            self.title("Select Patient")
            self.geometry("400x300")
            self.patients_data = patients_data
            self.selected_dfn = None

            self._create_widgets()

    def _create_widgets(self):
        self.tree = ttk.Treeview(self, columns=("DFN", "Name"), show="headings")
        self.tree.heading("DFN", text="DFN")
        self.tree.heading("Name", text="Patient Name")
        self.tree.column("DFN", width=100)
        self.tree.column("Name", width=250)
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)

        for patient in self.patients_data:
            self.tree.insert("", "end", values=(patient["DFN"], patient["Name"]))

        self.tree.bind("<Double-1>", self._on_double_click)

        select_button = ttk.Button(self, text="Select Patient", command=self._on_select_button_click)
        select_button.pack(pady=5)

    def _on_double_click(self, event):
        item = self.tree.selection()[0]
        self.selected_dfn = self.tree.item(item, "values")[0]
        self.master.dfn_entry.delete(0, tk.END)
        self.master.dfn_entry.insert(0, self.selected_dfn)
        self.master._select_patient(self.selected_dfn)
        self.destroy()

    def _on_select_button_click(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a patient from the list.")
            return
        self.selected_dfn = self.tree.item(selected_item[0], "values")[0]
        self.master.dfn_entry.delete(0, tk.END)
        self.master.dfn_entry.insert(0, self.selected_dfn)
        self.master._select_patient(self.selected_dfn)
        self.destroy()



class RecentNotesWindow(tk.Toplevel):
    def __init__(self, master, notes_data):
        super().__init__(master)
        self.master = master
        self.title("Recent Notes for My Patients")
        self.geometry("800x600")
        self.notes_data = notes_data

        self._create_widgets()

    def _create_widgets(self):
        self.tree = ttk.Treeview(self, columns=("Patient DFN", "Patient Name", "Note IEN", "Note Title", "Note Date"), show="headings")
        self.tree.heading("Patient DFN", text="Patient DFN")
        self.tree.heading("Patient Name", text="Patient Name")
        self.tree.heading("Note IEN", text="Note IEN")
        self.tree.heading("Note Title", text="Note Title")
        self.tree.heading("Note Date", text="Note Date")
        self.tree.column("Patient DFN", width=100)
        self.tree.column("Patient Name", width=150)
        self.tree.column("Note IEN", width=100)
        self.tree.column("Note Title", width=250)
        self.tree.column("Note Date", width=150)
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)

        for note in self.notes_data:
            self.tree.insert("", "end", values=(note.get('PatientDFN'), note.get('PatientName'), note.get('IEN'), note.get('Title'), note.get('Date')))

        self.tree.bind("<Double-1>", self._on_double_click)

    def _on_double_click(self):
        item = self.tree.selection()[0]
        ien = self.tree.item(item, "values")[2]
        # Now, instead of opening a new window, we'll just log the note text to the main log window
        # The main GUI's _on_note_double_click already handles fetching and logging the text.
        # We can simulate a double click on the main notes treeview if needed, or just log here.
        # For now, let's just log it directly.
        try:
            note_text = self.master.vista_client.invoke_rpc("TIU GET RECORD TEXT", f"literal:{ien}")
            self.master.log_window.log(f"--- Note IEN: {ien} (from Recent Notes) ---\n{note_text}\n--- End Note IEN: {ien} ---")
        except Exception as e:
            self.master.log_window.log(f"ERROR: Failed to retrieve note text for IEN {ien} (from Recent Notes): {e}")
            messagebox.showerror("Error", f"Failed to retrieve note text: {e}")
        self.destroy()



if __name__ == "__main__":


    app = VistARPCGUI()
    app.mainloop()