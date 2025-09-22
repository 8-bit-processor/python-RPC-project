import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import sys
import os
import json
import re

# Add the directory containing the vavista package to the Python path
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Add the vavista-rpc-master directory to the Python path

from vista_rpc_client import VistAClient
from rpc_config_loader import RPCConfigLoader

important_rpcs = [
    "ORQQAL LIST",
    "TIU SUMMARIES",
    "TIU DOCUMENTS BY CONTEXT",
    "TIU GET RECORD TEXT",
    "ORQQPL SELECTION LIST",
    "ORWU USERINFO",
    "ORQPT PROVIDER PATIENTS",
    "TIU LONG LIST OF TITLES",
    "ORWPT LIST ALL",
    "ORWPT SELECT",
    "ORVAA VAA",
    "ORWPT ENCTITL",
    "ORWORB FASTUSER",
    "ORQQCN DETAIL",
    "ORWU HASKEY",
    "ORWORB FASTUSER"
    ]



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
        self.geometry("600x800")
        self.log_text = scrolledtext.ScrolledText(self, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)


class RPCCommWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("RPC Communication Log")
        self.geometry("800x600")
        self.log_text = scrolledtext.ScrolledText(self, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

    def log(self, message):
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

    def _select_patient(self, dfn):
        print(f"DEBUG: _select_patient called with dfn={dfn}")
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA. Please connect first.")
            return

        self.log_window.log(f"Selecting patient with DFN: {dfn}")
        try:
            patient_info = self.vista_client.select_patient(dfn)
            self.log_window.log(f"ORWPT SELECT Parsed Reply: {patient_info!r}")
            
            if patient_info and patient_info.get("Name"):
                patient_name = patient_info["Name"]
                self.log_window.log(f"Successfully selected patient: {patient_name} (DFN: {dfn})")
                self.current_patient_label.config(text=f"{patient_name} (DFN: {dfn})") # Update patient label
                self.current_dfn = dfn # Store the current DFN
                self._fetch_patient_notes(dfn, 100, 3) # Fetch 100 recent notes of class 3 by default
            else:
                self.log_window.log(f"Could not get patient name from ORWPT SELECT reply.")

        except Exception as e:
            self.log_window.log(f"Failed to select patient: {e}")
            messagebox.showerror("RPC Error", f"Failed to select patient: {e}")

    def _fetch_patient_notes(self, dfn, note_count, doc_class_ien):
        try:
            self.log_window.log(f"_fetch_patient_notes: dfn={dfn}, note_count={note_count}, doc_class_ien={doc_class_ien}")
            self.notes_tree.delete(*self.notes_tree.get_children())
            self.log_window.log(f"Attempting to fetch notes for DFN: {dfn} with Doc Class IEN: {doc_class_ien}")
            notes = self.vista_client.fetch_patient_notes(dfn, doc_class_ien=doc_class_ien, max_docs=note_count)
            if notes:
                for note in notes:
                    self.notes_tree.insert("", "end", values=(note.get('IEN'), note.get('Title'), note.get('Date')))
            else:
                self.log_window.log("No notes found for this patient.")
                self.notes_tree.insert("", "end", values=("", "No notes found for this patient.", ""))
        except Exception as e:
            import traceback
            self.log_window.log(f"!!! FAILED to fetch patient notes: {e}")
            self.log_window.log(traceback.format_exc())

    

    def _get_recent_notes_for_current_patient(self):
        self.log_window.log(f"_get_recent_notes_for_current_patient called")
        if self.current_dfn:
            options_window = RecentNotesOptionsWindow(self)
            self.wait_window(options_window) # Wait for the dialog to close
            note_count = options_window.result_note_count
            doc_class_ien = options_window.result_doc_class_ien
            if note_count is not None and doc_class_ien is not None:
                self._fetch_patient_notes(self.current_dfn, note_count, doc_class_ien)
        else:
            messagebox.showwarning("No Patient Selected", "Please select a patient first.")

    

    def _search_patient(self):
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA. Please connect first.")
            return

        search_term = self.search_patient_entry.get()
        if not search_term:
            messagebox.showwarning("Search Error", "Please enter a patient name to search.")
            return

        self.log_window.log(f"Searching for patient: {search_term}")
        try:
            patients = self.vista_client.search_patient(search_term)
            self.log_window.log(f"ORWPT LIST ALL Parsed Reply: {patients!r}")

            if patients:
                self.patients_data = patients
                self._open_patient_selection()
            else:
                messagebox.showinfo("Search Results", "No patients found matching the search criteria.")

        except Exception as e:
            self.log_window.log(f"Failed to search for patients: {e}")
            messagebox.showerror("RPC Error", f"Failed to search for patients: {e}")

    def _add_patient_to_list(self):
        if self.current_dfn:
            # Check if patient is already in the list
            for item in self.patient_list_tree.get_children():
                if self.patient_list_tree.item(item, "values")[0] == self.current_dfn:
                    return
            patient_name = self.current_patient_label.cget("text").split(' (DFN:')[0]
            self.patient_list_tree.insert("", "end", values=(self.current_dfn, patient_name))

    def _set_patient_from_list(self):
        selected_item = self.patient_list_tree.selection()
        if not selected_item:
            return
        dfn = self.patient_list_tree.item(selected_item[0], "values")[0]
        self._select_patient(dfn)

    def _on_patient_list_select(self, event):
        self._set_patient_from_list()

    def _on_note_double_click(self, event):
        item = self.notes_tree.selection()[0]
        ien = self.notes_tree.item(item, "values")[0]
        try:
            note_text = self.vista_client.invoke_rpc("TIU GET RECORD TEXT", f"literal:{ien}")
            self.log_window.log(f"--- Note IEN: {ien} ---\n{note_text}\n--- End Note IEN: {ien} ---")
        except Exception as e:
            self.log_window.log(f"ERROR: Failed to retrieve note text for IEN {ien}: {e}")
            messagebox.showerror("Error", f"Failed to retrieve note text: {e}")

    def __init__(self, rpc_list, rpc_info):
        super().__init__()
        self.title("VistA RPC Client")
        self.geometry("600x800") # Main window dimensions

        self.log_window = LogWindow(self)
        self.rpc_comm_window = RPCCommWindow(self) # New RPC Communication Log Window
        self.update_idletasks()
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_width = self.winfo_width() # This will now be 600
        log_width = 1020
        log_height = 800
        self.log_window.geometry(f"{log_width}x{log_height}+{(main_x + main_width)}+{main_y}") # Log window dimensions and position

        self.rpc_list = rpc_list
        self.rpc_info = rpc_info
        gui_logger = GUILogger(self.log_window.log)
        # Pass the new comm_logger to VistAClient
        self.vista_client = VistAClient(logger=gui_logger, comm_logger=self.rpc_comm_window.log) # Instantiate the VistAClient
        self.locations = {}
        self.providers = {}
        self.current_dfn = None # Store current patient DFN
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

        # Raw RPC Response Display
        self.raw_response_text = scrolledtext.ScrolledText(main_pane, wrap=tk.WORD, height=10)
        self.raw_response_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top pane for controls
        controls_pane = ttk.Frame(main_pane, padding="5")
        main_pane.add(controls_pane, weight=0)
        controls_pane.columnconfigure(0, weight=1)
        controls_pane.rowconfigure(0, weight=1)

        # Notebook for RPC and Patient controls
        notebook = ttk.Notebook(controls_pane)
        notebook.grid(row=0, column=0, sticky="nsew")

        # RPC Tab
        rpc_tab = ttk.Frame(notebook, padding="10")
        notebook.add(rpc_tab, text="RPC Call")
        rpc_tab.columnconfigure(1, weight=1)

        ttk.Label(rpc_tab, text="Select RPC:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.rpc_combobox = ttk.Combobox(rpc_tab, values=self.rpc_list, state="readonly")
        self.rpc_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.rpc_combobox.bind("<<ComboboxSelected>>", self._on_rpc_selected)

        

        ttk.Label(rpc_tab, text="Parameters:").grid(row=1, column=0, padx=5, pady=5, sticky="nw")
        self.params_entry = scrolledtext.ScrolledText(rpc_tab, wrap=tk.WORD, height=5)
        self.params_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        self.invoke_button = ttk.Button(rpc_tab, text="Invoke RPC", command=self._invoke_rpc, state=tk.DISABLED)
        self.invoke_button.grid(row=2, column=1, columnspan=2, padx=5, pady=10, sticky="e")

        # Patient Tab
        patient_tab = ttk.Frame(notebook, padding="10")
        notebook.add(patient_tab, text="Patient Selection")
        patient_tab.columnconfigure(1, weight=1)

        ttk.Label(patient_tab, text="Patient DFN:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.dfn_entry = ttk.Entry(patient_tab)
        self.dfn_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.dfn_entry.insert(0, "100001")

        self.get_patients_button = ttk.Button(patient_tab, text="Get My Patients", command=self._get_doctor_patients, state=tk.DISABLED)
        self.get_patients_button.grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(patient_tab, text="Search Name:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.search_patient_entry = ttk.Entry(patient_tab)
        self.search_patient_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.search_patient_button = ttk.Button(patient_tab, text="Search", command=self._search_patient, state=tk.DISABLED)
        self.search_patient_button.grid(row=1, column=2, padx=5, pady=5)

        self.get_recent_notes_button = ttk.Button(patient_tab, text="Get Recent Notes", command=self._get_recent_notes_for_current_patient, state=tk.DISABLED)
        self.get_recent_notes_button.grid(row=2, column=0, columnspan=3, padx=5, pady=10, sticky="ew")

        # Patient Notes Treeview
        self.notes_tree = ttk.Treeview(patient_tab, columns=("IEN", "Title", "Date"), show="headings")
        self.notes_tree.heading("IEN", text="IEN")
        self.notes_tree.heading("Title", text="Title")
        self.notes_tree.heading("Date", text="Date")
        self.notes_tree.column("IEN", width=100)
        self.notes_tree.column("Title", width=300)
        self.notes_tree.column("Date", width=150)
        self.notes_tree.grid(row=3, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        patient_tab.rowconfigure(3, weight=1)
        self.notes_tree.bind("<Double-1>", self._on_note_double_click)

        


    def _on_rpc_selected(self, event=None):
        selected_rpc = self.rpc_combobox.get()
        self.params_entry.delete(1.0, tk.END)

        # Find the RPC details in rpc_info
        rpc_details = None
        for category, rpcs_in_category in self.rpc_info.items():
            if selected_rpc in rpcs_in_category:
                rpc_details = rpcs_in_category[selected_rpc]
                break

        if rpc_details:
            # Display Description
            self.params_entry.insert(tk.END, f"Description:\n{rpc_details.get('description', 'N/A')}\n\n")

            # Display Parameters
            parameters_doc = rpc_details.get('parameters', 'N/A')
            self.params_entry.insert(tk.END, f"Parameters:\n")
            if parameters_doc != 'N/A':
                # Attempt to parse parameters and create a template
                template_params = []
                # Split by '; ' to handle multiple parameters, but not within quoted strings
                # This regex splits by semicolon followed by a space, but not if inside double quotes
                param_parts = re.split(r';\s*(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)', parameters_doc)
                
                for param in param_parts:
                    param = param.strip()
                    if param:
                        # Extract parameter name if available (e.g., "DFN: The patient's DFN.")
                        match = re.match(r"^(.*?):\s*.*", param)
                        if match:
                            param_name = match.group(1).strip()
                            template_params.append(f"literal:{param_name.replace(' ', '_').upper()}_VALUE")
                        else:
                            template_params.append(f"literal:PARAM_VALUE")
                
                if template_params:
                    self.params_entry.insert(tk.END, ";".join(template_params) + "\n\n")
                else:
                    self.params_entry.insert(tk.END, "# No specific parameters documented or complex parameters. Refer to documentation.\n\n")
            else:
                self.params_entry.insert(tk.END, "# No parameters documented for this RPC.\n\n")

            # Display Returns
            self.params_entry.insert(tk.END, f"Returns:\n{rpc_details.get('returns', 'N/A')}\n")

        else:
            self.params_entry.insert(tk.END, "# RPC details not found in documentation.\n")

        # Special handling for TIU PERSONAL TITLE LIST (as it was before)
        if selected_rpc == "TIU PERSONAL TITLE LIST":
            doctor_info = self.current_doctor_label.cget("text")
            if "DUZ: " in doctor_info:
                duz = doctor_info.split("DUZ: ")[1].split(")")[0]
                # Clear previous template and insert specific one
                self.params_entry.delete(1.0, tk.END) 
                self.params_entry.insert(tk.END, f"literal:{duz};literal:3") # Default to ClassIEN 3 for Progress Notes
            else:
                self.log_window.log("Doctor DUZ not available. Please connect to VistA first.")
                if not self.params_entry.get(1.0, tk.END).strip(): # Only insert if empty
                    self.params_entry.insert(tk.END, "")

    

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
            self.invoke_button.config(state=tk.NORMAL)
            self.get_patients_button.config(state=tk.NORMAL)
            self.search_patient_button.config(state=tk.NORMAL)
            self.get_recent_notes_button.config(state=tk.NORMAL)
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

    def _invoke_rpc(self, event=None):
        print(f"DEBUG: _invoke_rpc called with rpc_name={self.rpc_combobox.get()} and params_str={self.params_entry.get(1.0, tk.END).strip()}")
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA. Please connect first.")
            return

        rpc_name = self.rpc_combobox.get()
        params_str = self.params_entry.get(1.0, tk.END).strip()

        try:
            reply = self.vista_client.invoke_rpc(rpc_name, params_str)
            
            self.raw_response_text.config(state=tk.NORMAL)
            self.raw_response_text.delete(1.0, tk.END)

            if rpc_name == "ORQQAL LIST":
                # Clean up the response for ORQQAL LIST
                cleaned_reply = reply.replace("^", "").replace("\r\n", "").strip()
                self.raw_response_text.insert(tk.END, cleaned_reply)
            else:
                self.raw_response_text.insert(tk.END, reply)
            self.raw_response_text.config(state=tk.DISABLED)
            self.log_window.log(f"RPC '{rpc_name}' invoked successfully. Response length: {len(reply) if reply else 0}")
            print(f"DEBUG: Raw RPC reply: {reply!r}")
        except Exception as e:
            self.raw_response_text.insert(tk.END, f"Error: {e}")
            self.raw_response_text.config(state=tk.DISABLED)
            self.log_window.log(f"RPC '{rpc_name}' invocation failed: {e}")
            messagebox.showerror("RPC Error", f"RPC invocation failed: {e}")

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

                self.raw_response_text.config(state=tk.NORMAL)
                self.raw_response_text.delete(1.0, tk.END)
                
                if patients:
                    formatted_output = "Patients for current user (IEN: " + provider_ien + "):\n"
                    for patient in patients:
                        formatted_output += f"DFN: {patient['DFN']}, Name: {patient['Name']}\n"
                    self.raw_response_text.insert(tk.END, formatted_output)
                    self.patients_data = patients
                else:
                    self.raw_response_text.insert(tk.END, "No patients found for this provider or empty response.")
                self.raw_response_text.config(state=tk.DISABLED)
                self.log_window.log("Successfully retrieved and displayed patients.")

            else:
                self.log_window.log("Could not parse provider IEN from ORWU USERINFO response.")
                messagebox.showerror("RPC Error", "Could not retrieve provider IEN.")

        except Exception as e:
            self.log_window.log(f"Failed to get doctor's patients: {e}")
            messagebox.showerror("RPC Error", f"Failed to get doctor's patients: {e}")

    def _open_patient_selection(self):
        if not hasattr(self, 'patients_data') or not self.patients_data:
            messagebox.showwarning("Patient Selection", "Please click 'Get Doctor's Patients' first to load patient data.")
            return
        
        PatientSelectionWindow(self, self.patients_data)


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

    def _on_double_click(self, event):
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
    # Define file paths
    rpc_file_path = os.path.join(os.path.dirname(__file__), 'src', 'cprs_rpc_list.txt')
    rpc_doc_file_path = os.path.join(os.path.dirname(__file__), 'src', 'cprs_rpc_documentation.md')

    # Load RPC configuration
    config_loader = RPCConfigLoader(rpc_file_path, rpc_doc_file_path, important_rpcs)
    try:
        rpc_names, rpc_info = config_loader.load_all()
    except FileNotFoundError as e:
        messagebox.showerror("File Error", str(e))
        sys.exit(1)

    app = VistARPCGUI(rpc_names, rpc_info)
    app.mainloop()