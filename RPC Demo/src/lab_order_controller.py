import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json

class LabOrderDialog(tk.Toplevel):
    """
    A Toplevel dialog window used for ordering a specific lab test.
    It presents various options for the lab order (e.g., collection type, urgency)
    and allows the user to input details before submitting the order.
    """
    def __init__(self, master, lab_details, test_name, lab_defaults):
        """
        Initializes the LabOrderDialog.
        Args:
            master: The parent Tkinter window (typically the main VistARPCGUI).
            lab_details (dict): Parsed detailed information about the selected lab test.
                                Obtained from `order_entry.get_and_parse_lab_details`.
            test_name (str): The name of the lab test being ordered.
            lab_defaults (dict): Default values and lists for lab ordering,
                                 obtained from `vista_client.get_lab_order_defaults`.
        """
        super().__init__(master)
        self.title(f"Order Lab Test: {test_name}")
        self.geometry("500x600")
        self.transient(master) # Make it a transient window relative to master
        self.grab_set()      # Make it modal, blocking interaction with other windows until closed

        self.lab_details = lab_details    # Stores detailed info for the specific lab test
        self.lab_defaults = lab_defaults # Stores general lab ordering defaults and lists
        self.test_name = test_name       # Store test_name as an instance variable
        self.result = None               # To store the outcome of the dialog

        self._create_widgets() # Build the UI elements for the dialog

    def _create_widgets(self):
        """
        Creates and lays out the GUI widgets for the lab order dialog.
        This includes comboboxes for various lab order options, entry fields for text input,
        and displays parsed lab details for user reference.
        """
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Frame for lab order options (e.g., Collection Type, Urgency)
        options_frame = ttk.LabelFrame(main_frame, text="Lab Order Options", padding="10")
        options_frame.pack(fill=tk.X, pady=5)
        options_frame.columnconfigure(1, weight=1) # Allow the second column (comboboxes) to expand

        # Collection Type Selection
        ttk.Label(options_frame, text="Collection Type:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.collection_type_combobox = ttk.Combobox(options_frame, state="readonly")
        self.collection_type_combobox.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        # Populate Collection Type combobox from lab_defaults and set default if available
        if 'COLLECTION_TYPES' in self.lab_defaults:
            collection_types = [item['name'] for item in self.lab_defaults['COLLECTION_TYPES']]
            self.collection_type_combobox['values'] = collection_types
            
            default_coll_type_code = self.lab_defaults.get('DEFAULTS', {}).get('COLLECTION_TYPE')
            if default_coll_type_code:
                for item in self.lab_defaults['COLLECTION_TYPES']:
                    if item['ien'] == default_coll_type_code:
                        self.collection_type_combobox.set(item['name'])
                        break

        # Urgency Selection
        ttk.Label(options_frame, text="Urgency:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.urgency_combobox = ttk.Combobox(options_frame, state="readonly")
        self.urgency_combobox.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        # Populate Urgency combobox - Use 'URGENCIES' from lab_defaults
        if 'URGENCIES' in self.lab_defaults:
            urgencies = [item['name'] for item in self.lab_defaults['URGENCIES']]
            self.urgency_combobox['values'] = urgencies

            default_urgency_ien = self.lab_defaults.get('DEFAULTS', {}).get('URGENCY')
            if default_urgency_ien:
                for item in self.lab_defaults['URGENCIES']: # Needs to be 'URGENCIES'
                    if item['ien'] == default_urgency_ien:
                        self.urgency_combobox.set(item['name'])
                        break

        # Schedule (Frequency) Selection
        ttk.Label(options_frame, text="Schedule:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.schedule_combobox = ttk.Combobox(options_frame, state="readonly")
        self.schedule_combobox.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        # Populate Schedule combobox from lab_defaults and set default
        if 'SCHEDULES' in self.lab_defaults:
            schedules = [item['name'] for item in self.lab_defaults['SCHEDULES']]
            self.schedule_combobox['values'] = schedules

            default_schedule_ien = self.lab_defaults.get('DEFAULTS', {}).get('SCHEDULE')
            if default_schedule_ien:
                for item in self.lab_defaults['SCHEDULES']:
                    if item['ien'] == default_schedule_ien:
                        self.schedule_combobox.set(item['name'])
                        break

        # Collection Sample Selection
        ttk.Label(options_frame, text="Collection Sample:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.collection_sample_combobox = ttk.Combobox(options_frame, state="readonly")
        self.collection_sample_combobox.grid(row=3, column=1, padx=5, pady=2, sticky="ew")

        # Populate Collection Sample combobox from lab_details (specific to the lab test)
        if 'CollSamp' in self.lab_details: # This key is from _parse_lab_details
            collection_samples = [item['name'] for item in self.lab_details['CollSamp']]
            self.collection_sample_combobox['values'] = collection_samples
            # Set default if available (from lab_details, not lab_defaults)
            default_coll_sample_ien = self.lab_details.get('COLLECTION SAMPLE') # This key might be different
            if default_coll_sample_ien:
                for item in self.lab_details['CollSamp']:
                    if item['ien'] == default_coll_sample_ien:
                        self.collection_sample_combobox.set(item['name'])
                        break

        # Specimen Selection
        ttk.Label(options_frame, text="Specimen:").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.specimen_combobox = ttk.Combobox(options_frame, state="readonly")
        self.specimen_combobox.grid(row=4, column=1, padx=5, pady=2, sticky="ew")

        # Populate Specimen combobox from lab_details
        if 'Specimens' in self.lab_details: # This key is from _parse_lab_details
            specimens = [item['name'] for item in self.lab_details['Specimens']]
            self.specimen_combobox['values'] = specimens
            # Set default if available (from lab_details)
            default_specimen_ien = self.lab_details.get('SPECIMEN') # This key might be different
            if default_specimen_ien:
                for item in self.lab_details['Specimens']:
                    if item['ien'] == default_specimen_ien:
                        self.specimen_combobox.set(item['name'])
                        break

        # Collection Date/Time Entry
        ttk.Label(options_frame, text="Collection Date/Time:").grid(row=5, column=0, padx=5, pady=2, sticky="w")
        self.collection_datetime_entry = ttk.Entry(options_frame)
        self.collection_datetime_entry.grid(row=5, column=1, padx=5, pady=2, sticky="ew")
        self.collection_datetime_entry.insert(0, "NOW") # Default value for collection time

        # Number of Days Entry (for duration if applicable)
        ttk.Label(options_frame, text="Number of Days:").grid(row=6, column=0, padx=5, pady=2, sticky="w")
        self.num_days_entry = ttk.Entry(options_frame)
        self.num_days_entry.grid(row=6, column=1, padx=5, pady=2, sticky="ew")
        self.num_days_entry.insert(0, "") # Default to empty

        # Additional Comments Entry
        ttk.Label(options_frame, text="Additional Comments:").grid(row=7, column=0, padx=5, pady=2, sticky="w")
        self.addl_comments_entry = ttk.Entry(options_frame)
        self.addl_comments_entry.grid(row=7, column=1, padx=5, pady=2, sticky="ew")
        self.addl_comments_entry.insert(0, "") # Default to empty

        # Display the parsed lab data for verification (for debugging/information)
        ttk.Label(main_frame, text="Raw Lab Details:").pack(pady=(10,0), anchor="w")
        text_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD)
        text_area.pack(fill=tk.BOTH, expand=True)
        
        pretty_details = json.dumps(self.lab_details, indent=4)
        text_area.insert(tk.END, pretty_details)
        text_area.config(state=tk.DISABLED) # Make read-only

        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Accept Order", command=self._on_accept).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT)

    def _on_accept(self):
        """
        Handles the "Accept Order" button click. Gathers all selected/entered
        values from the dialog's UI fields, constructs an `order_params` dictionary,
        and delegates to the `LabOrderController` to place the lab order.
        """
        # Gather all selected values from the UI fields
        selected_collection_type_name = self.collection_type_combobox.get()
        selected_urgency_name = self.urgency_combobox.get()
        selected_schedule_name = self.schedule_combobox.get()
        selected_collection_sample_name = self.collection_sample_combobox.get()
        selected_specimen_name = self.specimen_combobox.get()
        collection_datetime = self.collection_datetime_entry.get()
        num_days = self.num_days_entry.get()
        addl_comments = self.addl_comments_entry.get()

        order_params = {
            "test_ien": self.lab_details.get("Item ID"), # Assuming Item ID is the test IEN from lab_details
            "test_name": self.test_name
        }

        # Map Collection Type name back to its IEN/code using lab_defaults
        if 'COLLECTION_TYPES' in self.lab_defaults:
            for item in self.lab_defaults['COLLECTION_TYPES']:
                if item['name'] == selected_collection_type_name:
                    order_params["collection_type_code"] = item['ien']
                    break

        # Map Urgency name back to its IEN using lab_defaults
        if 'URGENCIES' in self.lab_defaults: # Corrected to 'URGENCIES'
            for item in self.lab_defaults['URGENCIES']: # Corrected to 'URGENCIES'
                if item['name'] == selected_urgency_name:
                    order_params["urgency_ien"] = item['ien']
                    break

        # Map Schedule name back to its IEN using lab_defaults
        if 'SCHEDULES' in self.lab_defaults:
            for item in self.lab_defaults['SCHEDULES']:
                if item['name'] == selected_schedule_name:
                    order_params["schedule_ien"] = item['ien']
                    break

        # Map Collection Sample name back to its IEN using lab_details
        if 'CollSamp' in self.lab_details:
            for item in self.lab_details['CollSamp']:
                if item['name'] == selected_collection_sample_name:
                    order_params["collection_sample_ien"] = item['ien']
                    break

        # Map Specimen name back to its IEN using lab_details
        if 'Specimens' in self.lab_details:
            for item in self.lab_details['Specimens']:
                if item['name'] == selected_specimen_name:
                    order_params["specimen_ien"] = item['ien']
                    break

        # Add direct input values
        order_params["collection_datetime"] = collection_datetime
        order_params["num_days"] = num_days
        order_params["addl_comments"] = addl_comments

        # Delegate to the controller to place the order
        try:
            # The 'master' here refers to the main VistARPCGUI instance,
            # which holds an instance of LabOrderController.
            self.master.lab_order_controller.place_lab_order(order_params)
            messagebox.showinfo("Success", "Lab order placed successfully!")
            self.destroy() # Close the dialog on success
        except Exception as e:
            messagebox.showerror("Order Error", f"Failed to place lab order: {e}")

    def _on_cancel(self):
        """
        Handles the "Cancel" button click. Closes the dialog window without placing an order.
        """
        self.destroy()


class LabOrderController:
    """
    Controller class responsible for managing the business logic related to lab ordering.
    It orchestrates interactions between the main GUI, the `OrderEntry` service,
    and the `LabOrderDialog` to facilitate placing lab orders in VistA.
    """
    def __init__(self, order_entry, log_window, parent_view):
        """
        Initializes the LabOrderController.
        Args:
            order_entry (OrderEntry): An instance of the OrderEntry class for VistA order RPCs.
            log_window (LogWindow): An instance of the LogWindow for logging messages.
            parent_view (VistARPCGUI): A reference to the main GUI window for context and callbacks.
        """
        self.order_entry = order_entry
        self.log_window = log_window
        self.parent_view = parent_view
        self.lab_defaults = {} # Stores default values and lists for lab ordering fetched from VistA

    def handle_lab_order_selection(self, test_ien, test_name):
        """
        Handles the event when a user selects a lab test from the order menu in the main GUI.
        This method fetches the detailed information and default options for the selected lab,
        performs basic validation, and then displays the `LabOrderDialog` for user input.
        Args:
            test_ien (str): The IEN of the selected lab test.
            test_name (str): The name of the selected lab test.
        Raises:
            Exception: If fetching lab details or defaults fails.
        """
        self.log_window.log(f"LabOrderController: Handling selection of '{test_name}' (IEN: {test_ien})")
        try:
            # Get current location IEN from the main GUI (parent_view)
            location_ien = self.parent_view.get_current_location_ien()
            if not location_ien:
                messagebox.showwarning("Lab Order Error", "Could not determine current location for lab defaults.")
                return

            # Fetch general lab order defaults and available lists (collection types, urgencies, schedules)
            self.lab_defaults = self.order_entry.vista_client.get_lab_order_defaults(location_ien)
            self.log_window.log(f"LabOrderController: Fetched lab defaults: {self.lab_defaults}")

            # Fetch and parse specific details for the selected lab test (e.g., collection samples, specimens)
            self.log_window.log(f"Fetching and parsing details for lab test IEN: {test_ien}")
            lab_details = self.order_entry.get_and_parse_lab_details(test_ien)

            # --- Server Data Validation ---
            # It's good practice to validate if the server's returned name matches the client's selected name.
            parsed_name = lab_details.get("Test Name", "")
            if parsed_name and (parsed_name.lower() != test_name.lower()):
                self.log_window.log(f"WARNING: Server data mismatch. Selected: {test_name}, Received: {parsed_name}. Using server's name for processing.")
                test_name = parsed_name # Use the server's name for consistency
            # --- End Validation ---

            # Open the lab order dialog, passing in all relevant details and defaults
            dialog = LabOrderDialog(self.parent_view, lab_details, test_name, self.lab_defaults)
            # Wait for the dialog to close before continuing execution in the main GUI thread
            self.parent_view.wait_window(dialog)

        except Exception as e:
            self.log_window.log(f"ERROR: Failed to get lab test details: {e}")
            import traceback
            self.log_window.log(traceback.format_exc())
            messagebox.showerror("RPC Error", f"Failed to get lab test details: {e}")

    def place_lab_order(self, order_params: dict):
        """
        Constructs the necessary parameters from the `order_params` dictionary
        (received from `LabOrderDialog`) and calls the `order_entry` service
        to place the lab order in VistA.
        Args:
            order_params (dict): A dictionary containing all collected lab order details.
        Returns:
            Any: The result of the `order_entry.save_order` RPC call.
        Raises:
            ValueError: If critical patient, provider, or location information is missing.
            Exception: If the underlying RPC calls fail.
        """
        self.log_window.log(f"LabOrderController: Attempting to place lab order with params: {order_params}")

        # Retrieve necessary context from the parent view (main GUI)
        patient_dfn = self.parent_view.current_dfn
        provider_duz = self.parent_view.current_duz
        location_ien = self.parent_view.get_current_location_ien()

        if not all([patient_dfn, provider_duz, location_ien]):
            raise ValueError("Missing patient DFN, provider DUZ, or location IEN. Cannot place order.")

        # Define the VistA order dialog name and display group for lab orders
        # These are standard values for lab orders in CPRS.
        order_dialog_name = "LR OTHER LAB TESTS"
        display_group = 2 # Corresponds to the 'LAB' display group in VistA

        # The orderable_item_ien is the IEN of the specific lab test being ordered
        orderable_item_ien = order_params.get("test_ien")
        if not orderable_item_ien:
            raise ValueError("Orderable item IEN (test_ien) is missing from order_params.")

        # --- Construct the 'responses' dictionary for ORWDX SAVE ---
        # This is the most complex part of VistA ordering: mapping UI fields to
        # VistA RPC parameters, which are identified by prompt IENs and instance numbers.
        # The prompt_ien values (e.g., "1000", "1001") are educated guesses based on
        # common VistA patterns and may need to be confirmed via VistA introspection
        # or CPRS client analysis.
        responses = {}

        # Map Collection Type from selected name back to code/IEN
        if order_params.get("collection_type_code"):
            # Placeholder prompt_ien for Collection Type (needs to be actual VistA prompt IEN)
            responses["COLLECTION_TYPE_PROMPT"] = ("1000", "1", order_params["collection_type_code"])

        # Map Urgency from selected name back to IEN
        if order_params.get("urgency_ien"):
            # Placeholder prompt_ien for Urgency
            responses["URGENCY_PROMPT"] = ("1001", "1", order_params["urgency_ien"])

        # Map Schedule from selected name back to IEN
        if order_params.get("schedule_ien"):
            # Placeholder prompt_ien for Schedule
            responses["SCHEDULE_PROMPT"] = ("1002", "1", order_params["schedule_ien"])

        # Map Collection Sample from selected name back to IEN
        if order_params.get("collection_sample_ien"):
            # Placeholder prompt_ien for Collection Sample
            responses["COLLECTION_SAMPLE_PROMPT"] = ("1003", "1", order_params["collection_sample_ien"])

        # Map Specimen from selected name back to IEN
        if order_params.get("specimen_ien"):
            # Placeholder prompt_ien for Specimen
            responses["SPECIMEN_PROMPT"] = ("1004", "1", order_params["specimen_ien"])

        # Map Collection Date/Time
        if order_params.get("collection_datetime"):
            # Placeholder prompt_ien for Collection Date/Time
            responses["COLLECTION_DATETIME_PROMPT"] = ("1005", "1", order_params["collection_datetime"])

        # Map Number of Days (Duration)
        if order_params.get("num_days"):
            # Placeholder prompt_ien for Number of Days
            responses["NUM_DAYS_PROMPT"] = ("1006", "1", order_params["num_days"])

        # Map Additional Comments
        if order_params.get("addl_comments"):
            # Placeholder prompt_ien for Additional Comments
            responses["ADDL_COMMENTS_PROMPT"] = ("1007", "1", order_params["addl_comments"])

        # Call order_entry.save_order to submit the lab order to VistA
        self.log_window.log(f"LabOrderController: Calling save_order with responses: {responses}")
        result = self.order_entry.save_order(
            patient_dfn=patient_dfn,
            provider_duz=provider_duz,
            location_ien=location_ien,
            order_dialog_name=order_dialog_name,
            display_group=display_group,
            orderable_item_ien=orderable_item_ien,
            responses=responses,
            signature="" # Lab orders typically don't require immediate electronic signature in this specific context
        )
        self.log_window.log(f"LabOrderController: save_order result: {result}")
        return result
