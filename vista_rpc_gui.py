import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import sys
import os
import json

# Add the directory containing the vavista package to the Python path
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Add the vavista-rpc-master directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'vavista-rpc-master'))

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

class RPCBrowser(tk.Toplevel):
    def __init__(self, master, rpc_info):
        super().__init__(master)
        self.master = master
        self.rpc_info = rpc_info
        self.title("RPC Browser")
        self.geometry("800x600")

        self._create_widgets()
        self._populate_tree()

    def _create_widgets(self):
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # RPC Tree
        tree_frame = ttk.Frame(main_pane)
        main_pane.add(tree_frame, weight=1)
        self.tree = ttk.Treeview(tree_frame)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_rpc_selected)

        # Documentation Display
        doc_frame = ttk.Frame(main_pane)
        main_pane.add(doc_frame, weight=2)
        self.doc_text = scrolledtext.ScrolledText(doc_frame, wrap=tk.WORD)
        self.doc_text.pack(fill=tk.BOTH, expand=True)

    def _populate_tree(self):
        for category, rpcs_in_category in self.rpc_info.items():
            category_node = self.tree.insert("", "end", text=category, open=True)
            for rpc_name, rpc_details in rpcs_in_category.items():
                # Store rpc_details as a JSON string
                self.tree.insert(category_node, "end", text=rpc_name, values=(rpc_name, json.dumps(rpc_details)))

    def _on_rpc_selected(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            return

        item_id = selected_item[0]
        parent_id = self.tree.parent(item_id)

        if not parent_id:  # It's a category, not an RPC
            return

        rpc_name = self.tree.item(item_id, "text")
        # Retrieve rpc_details as a JSON string and load it back into a dictionary
        rpc_details_json = self.tree.item(item_id, "values")[1]
        rpc_details = json.loads(rpc_details_json)

        self.doc_text.config(state=tk.NORMAL)
        self.doc_text.delete(1.0, tk.END)
        self.doc_text.insert(tk.END, f"**Description:**\n{rpc_details.get('description', 'N/A')}\n\n")
        self.doc_text.insert(tk.END, f"**Parameters:**\n{rpc_details.get('parameters', 'N/A')}\n\n")
        self.doc_text.insert(tk.END, f"**Returns:**\n{rpc_details.get('returns', 'N/A')}")
        self.doc_text.config(state=tk.DISABLED)

        self.master.rpc_combobox.set(rpc_name)
        self.master._on_rpc_selected() # Call the master's method to update its parameter entry

class VistARPCGUI(tk.Tk):

    def _select_patient(self, dfn):
        print(f"DEBUG: _select_patient called with dfn={dfn}")
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA. Please connect first.")
            return

        self._log_status(f"Selecting patient with DFN: {dfn}")
        try:
            reply = self.vista_client.select_patient(dfn)
            self._log_status(f"ORWPT SELECT Raw Reply: {reply!r}")
            # Parse the reply to get the patient's name
            patient_name = "Unknown"
            reply_parts = reply.split('^')
            if len(reply_parts) > 0:
                patient_name = reply_parts[0] # Assuming name is the first part
            self._log_status(f"Successfully selected patient: {patient_name} (DFN: {dfn})")
            self.current_patient_label.config(text=f"{patient_name} (DFN: {dfn})") # Update patient label
            self.current_dfn = dfn # Store the current DFN
            self._fetch_patient_notes(dfn)
        except Exception as e:
            self._log_status(f"Failed to select patient: {e}")
            messagebox.showerror("RPC Error", f"Failed to select patient: {e}")

    def _fetch_patient_notes(self, dfn):
        self.notes_tree.delete(*self.notes_tree.get_children())
        try:
            self._log_status(f"Attempting to fetch notes for DFN: {dfn}")
            # TIU DOCUMENTS BY CONTEXT parameters: DocClassIEN, Context, PatientDFN, EarlyDate, LateDate, Person, OccLim, SortSeq
            # For now, we'll use a broad context to get all documents for the patient.
            # DocClassIEN: 3 (Progress Notes) is common, but for all documents, it might be different or omitted.
            # Let's try with DocClassIEN 3 and empty other parameters for simplicity.
            # The documentation for TIU DOCUMENTS BY CONTEXT is complex, so this might need refinement.
            # For now, let's assume we want all notes for the patient.
            # The RPC expects: literal:DocClassIEN;literal:Context;literal:PatientDFN;literal:EarlyDate;literal:LateDate;literal:Person;literal:OccLim;literal:SortSeq
            # Let's try with just DFN for now, as the vista_rpc_client.py's fetch_patient_notes already handles it.
            notes_reply = self.vista_client.fetch_patient_notes(dfn)
            if notes_reply and notes_reply.strip():
                notes_list = notes_reply.split('\r\n') # Use \r\n for consistency with other RPC replies
                for note_info in notes_list:
                    if note_info.strip():
                        parts = note_info.split('^')
                        if len(parts) >= 3:
                            ien = parts[0]
                            title = parts[1]
                            date = parts[2]
                            self.notes_tree.insert("", "end", values=(ien, title, date))
            else:
                self.notes_tree.insert("", "end", values=("", "No notes found for this patient.", ""))
        except Exception as e:
            self._log_status(f"Failed to fetch patient notes: {e}")

    def _on_note_selected(self, event):
        selected_item = self.notes_tree.selection()
        if not selected_item:
            return
        ien = self.notes_tree.item(selected_item[0], "values")[0]
        self.params_entry.delete(1.0, tk.END)
        self.params_entry.insert("1.0", f"literal:{ien}")
        self.rpc_combobox.set("TIU GET RECORD TEXT")
        self._invoke_rpc()

    def _search_patient(self):
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA. Please connect first.")
            return

        search_term = self.search_patient_entry.get()
        if not search_term:
            messagebox.showwarning("Search Error", "Please enter a patient name to search.")
            return

        self._log_status(f"Searching for patient: {search_term}")
        try:
            patients_reply = self.vista_client.search_patient(search_term)
            self._log_status(f"ORWPT LIST ALL Raw Reply: {patients_reply!r}")

            if patients_reply and patients_reply.strip():
                patients_list = patients_reply.split('\r\n')
                self.patients_data = []
                for patient_info in patients_list:
                    if patient_info.strip():
                        parts = patient_info.split('^')
                        if len(parts) >= 2:
                            dfn = parts[0]
                            name = parts[1]
                            self.patients_data.append({"DFN": dfn, "Name": name})
                
                if self.patients_data:
                    self._open_patient_selection()
                else:
                    messagebox.showinfo("Search Results", "No patients found matching the search criteria.")
            else:
                messagebox.showinfo("Search Results", "No patients found matching the search criteria or empty response.")

        except Exception as e:
            self._log_status(f"Failed to search for patients: {e}")
            messagebox.showerror("RPC Error", f"Failed to search for patients: {e}")

    def __init__(self, rpc_list, rpc_info):
        super().__init__()
        self.title("VistA RPC Client")
        self.geometry("1000x700")

        self.rpc_list = rpc_list
        self.rpc_info = rpc_info
        self.vista_client = VistAClient() # Instantiate the VistAClient
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

        # RPC Tab
        rpc_tab = ttk.Frame(notebook, padding="10")
        notebook.add(rpc_tab, text="RPC Call")
        rpc_tab.columnconfigure(1, weight=1)

        ttk.Label(rpc_tab, text="Select RPC:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.rpc_combobox = ttk.Combobox(rpc_tab, values=self.rpc_list, state="readonly")
        self.rpc_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.rpc_combobox.bind("<<ComboboxSelected>>", self._on_rpc_selected)

        self.browse_button = ttk.Button(rpc_tab, text="Browse RPCs", command=self._open_rpc_browser)
        self.browse_button.grid(row=0, column=2, padx=5, pady=5)

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

        # Encounter Tab
        encounter_tab = ttk.Frame(notebook, padding="10")
        notebook.add(encounter_tab, text="Encounter")
        encounter_tab.columnconfigure(1, weight=1)

        ttk.Label(encounter_tab, text="Location:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.location_combobox = ttk.Combobox(encounter_tab, state="readonly")
        self.location_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.load_locations_button = ttk.Button(encounter_tab, text="Load Locations", command=self._load_locations, state=tk.DISABLED)
        self.load_locations_button.grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(encounter_tab, text="Provider:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.provider_combobox = ttk.Combobox(encounter_tab, state="readonly")
        self.provider_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.load_providers_button = ttk.Button(encounter_tab, text="Load Providers", command=self._load_providers, state=tk.DISABLED)
        self.load_providers_button.grid(row=1, column=2, padx=5, pady=5)

        # Bottom pane for results
        results_pane = ttk.PanedWindow(main_pane, orient=tk.HORIZONTAL)
        main_pane.add(results_pane, weight=1)

        # Notes List
        notes_frame = ttk.LabelFrame(results_pane, text="Patient Notes", padding="10")
        results_pane.add(notes_frame, weight=1)
        notes_frame.rowconfigure(0, weight=1)
        notes_frame.columnconfigure(0, weight=1)
        self.notes_tree = ttk.Treeview(notes_frame, columns=("IEN", "Title", "Date"), show="headings")
        self.notes_tree.heading("IEN", text="IEN")
        self.notes_tree.heading("Title", text="Title")
        self.notes_tree.heading("Date", text="Date")
        self.notes_tree.column("IEN", width=80, stretch=tk.NO)
        self.notes_tree.column("Title", width=250)
        self.notes_tree.column("Date", width=150, stretch=tk.NO)
        self.notes_tree.grid(row=0, column=0, sticky="nsew")
        self.notes_tree.bind("<Double-1>", self._on_note_selected)

        # Response and Status Tab
        response_notebook = ttk.Notebook(results_pane)
        results_pane.add(response_notebook, weight=2)

        # Raw Response Tab
        response_tab = ttk.Frame(response_notebook, padding="5")
        response_notebook.add(response_tab, text="Raw Response")
        response_tab.columnconfigure(0, weight=1)
        response_tab.rowconfigure(0, weight=1)
        self.raw_response_text = scrolledtext.ScrolledText(response_tab, wrap=tk.WORD, height=10)
        self.raw_response_text.grid(row=0, column=0, sticky="nsew")

        # Status Messages Tab
        status_tab = ttk.Frame(response_notebook, padding="5")
        response_notebook.add(status_tab, text="Status Log")
        status_tab.columnconfigure(0, weight=1)
        status_tab.rowconfigure(0, weight=1)
        self.status_text = scrolledtext.ScrolledText(status_tab, wrap=tk.WORD, height=5)
        self.status_text.grid(row=0, column=0, sticky="nsew")

    def _open_rpc_browser(self):
        RPCBrowser(self, self.rpc_info)

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
            parameters_doc = rpc_details.get('parameters', 'N/A')
            if parameters_doc != 'N/A':
                # Attempt to parse parameters and create a template
                template_params = []
                # Split by '; ' to handle multiple parameters, but not within quoted strings
                # This regex splits by semicolon followed by a space, but not if inside double quotes
                param_parts = re.split(r';\s*(?=(?:[^"]*"[^"]*")*[^"]*$)', parameters_doc)
                
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
                    self.params_entry.insert("1.0", ";".join(template_params))
                else:
                    self.params_entry.insert("1.0", "# No specific parameters documented or complex parameters. Refer to documentation.")
            else:
                self.params_entry.insert("1.0", "# No parameters documented for this RPC.")
        else:
            self.params_entry.insert("1.0", "# RPC details not found in documentation.")

        # Special handling for TIU PERSONAL TITLE LIST (as it was before)
        if selected_rpc == "TIU PERSONAL TITLE LIST":
            doctor_info = self.current_doctor_label.cget("text")
            if "DUZ: " in doctor_info:
                duz = doctor_info.split("DUZ: ")[1].split(")")[0]
                self.params_entry.delete(1.0, tk.END) # Clear previous template
                self.params_entry.insert("1.0", f"literal:{duz};literal:3") # Default to ClassIEN 3 for Progress Notes
            else:
                self._log_status("Doctor DUZ not available. Please connect to VistA first.")
                if not self.params_entry.get(1.0, tk.END).strip(): # Only insert if empty
                    self.params_entry.insert("1.0", "")

    def _load_locations(self):
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA. Please connect first.")
            return

        self._log_status("Loading hospital locations...")
        try:
            locations_reply = self.vista_client.invoke_rpc("ORWU HOSPLOC", "literal:;literal:1")
            if locations_reply:
                locations_list = locations_reply.split('\r\n')
                self.locations = {loc.split('^')[1]: loc.split('^')[0] for loc in locations_list if loc.strip()}
                self.location_combobox['values'] = list(self.locations.keys())
                self._log_status("Hospital locations loaded successfully.")
        except Exception as e:
            self._log_status(f"Failed to load hospital locations: {e}")
            messagebox.showerror("RPC Error", f"Failed to load hospital locations: {e}")

    def _load_providers(self):
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA. Please connect first.")
            return

        self._log_status("Loading providers...")
        try:
            providers_reply = self.vista_client.invoke_rpc("ORWU NEWPERS", "literal:;literal:1")
            if providers_reply:
                providers_list = providers_reply.split('\r\n')
                self.provider_combobox['values'] = [prov.split('^')[1] for prov in providers_list if prov.strip()]
                self._log_status("Providers loaded successfully.")
        except Exception as e:
            self._log_status(f"Failed to load providers: {e}")
            messagebox.showerror("RPC Error", f"Failed to load providers: {e}")

    def _on_rpc_selected(self, event=None):
        selected_rpc = self.rpc_combobox.get()
        self.params_entry.delete(1.0, tk.END)

        if selected_rpc == "TIU PERSONAL TITLE LIST":
            doctor_info = self.current_doctor_label.cget("text")
            if "DUZ: " in doctor_info:
                duz = doctor_info.split("DUZ: ")[1].split(")")[0]
                # Correctly format the parameters for this specific RPC
                self.params_entry.insert("1.0", f"literal:{duz};literal:3")
            else:
                self._log_status("Doctor DUZ not available. Please connect to VistA first.")
        # Add other special RPC cases here with elif selected_rpc == ...

    def _log_status(self, message):
        print(f"LOG: {message}")
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)

    def _connect_to_vista(self):
        host = self.host_entry.get()
        port = self.port_entry.get()
        access = self.access_entry.get()
        verify = self.verify_entry.get()
        context = self.context_entry.get()

        try:
            self._log_status("Attempting to connect to VistA...")
            self.vista_client.connect_to_vista(host, port, access, verify, context)
            self._log_status("Connection successful!")
            self.invoke_button.config(state=tk.NORMAL)
            self.get_patients_button.config(state=tk.NORMAL)
            self.search_patient_button.config(state=tk.NORMAL)
            self.connect_button.config(text="Connected", state=tk.DISABLED)
            # Update doctor info
            self._update_doctor_info()
        except Exception as e:
            self._log_status(f"Connection failed: {e}")
            messagebox.showerror("Connection Error", f"Failed to connect: {e}")
            self.vista_client.connection = None
            self.connect_button.config(text="Connect", state=tk.NORMAL)

    def _update_doctor_info(self):
        try:
            user_info_reply = self.vista_client.get_user_info()
            parts = user_info_reply.split('^')
            if len(parts) >= 2:
                duz = parts[0]
                name = parts[1]
                self.current_doctor_label.config(text=f"{name} (DUZ: {duz})")
                self.providers[name] = duz
                self.provider_combobox['values'] = [name]
                self.provider_combobox.set(name)
                self.current_duz = duz # Store the current DUZ
            else:
                self.current_doctor_label.config(text="N/A")
        except Exception as e:
            self._log_status(f"Failed to get doctor info: {e}")
            self.current_doctor_label.config(text="N/A")

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
            self._log_status(f"RPC '{rpc_name}' invoked successfully. Response length: {len(reply) if reply else 0}")
            print(f"DEBUG: Raw RPC reply: {reply!r}")
        except Exception as e:
            self.raw_response_text.insert(tk.END, f"Error: {e}")
            self.raw_response_text.config(state=tk.DISABLED)
            self._log_status(f"RPC '{rpc_name}' invocation failed: {e}")
            messagebox.showerror("RPC Error", f"RPC invocation failed: {e}")

    def _get_doctor_patients(self):
        if not self.vista_client.connection:
            messagebox.showwarning("RPC Error", "Not connected to VistA. Please connect first.")
            return

        self._log_status("Attempting to retrieve DOCTOR1's IEN...")
        try:
            user_info_reply = self.vista_client.get_user_info()
            self._log_status(f"ORWU USERINFO Raw Reply: {user_info_reply!r}")
            
            # Parse the user info reply to get the IEN
            # The format is typically "DUZ^Name^...^IEN"
            user_info_parts = user_info_reply.split('^')
            if len(user_info_parts) > 0:
                provider_ien = user_info_parts[0] # Assuming IEN is the first part
                self._log_status(f"Retrieved Provider IEN: {provider_ien}")

                self._log_status(f"Invoking ORQPT PROVIDER PATIENTS with IEN: {provider_ien}")
                patients_reply = self.vista_client.get_doctor_patients(provider_ien)
                self._log_status(f"ORQPT PROVIDER PATIENTS Raw Reply: {patients_reply!r}")

                self.raw_response_text.config(state=tk.NORMAL)
                self.raw_response_text.delete(1.0, tk.END)
                
                if patients_reply:
                    patients_list = patients_reply.split('\r\n')
                    formatted_output = "Patients for DOCTOR1 (IEN: " + provider_ien + "):\n"
                    for patient_info in patients_list:
                        if patient_info.strip():
                            # Assuming format is DFN^PatientName
                            parts = patient_info.split('^')
                            if len(parts) >= 2:
                                dfn = parts[0]
                                name = parts[1]
                                formatted_output += f"DFN: {dfn}, Name: {name}\n"
                            else:
                                formatted_output += f"Raw: {patient_info}\n"
                    self.raw_response_text.insert(tk.END, formatted_output)
                self.patients_data = []
                for patient_info in patients_list:
                    if patient_info.strip():
                        parts = patient_info.split('^')
                        if len(parts) >= 2:
                            dfn = parts[0]
                            name = parts[1]
                            self.patients_data.append({"DFN": dfn, "Name": name})
                else:
                    self.raw_response_text.insert(tk.END, "No patients found for this provider or empty response.")
                self.raw_response_text.config(state=tk.DISABLED)
                self._log_status("Successfully retrieved and displayed patients.")

            else:
                self._log_status("Could not parse provider IEN from ORWU USERINFO response.")
                messagebox.showerror("RPC Error", "Could not retrieve provider IEN.")

        except Exception as e:
            self._log_status(f"Failed to get doctor's patients: {e}")
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