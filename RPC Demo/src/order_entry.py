import sys
import os
import json

# Add the project root and vavista directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'vavista'))

from vista_rpc_client import VistaRpcClient
from vavista.rpc import PLiteral, PList

class OrderEntry:
    """
    Provides methods for interacting with VistA's Computerized Patient Record System (CPRS)
    ordering functionalities. This class encapsulates RPC calls related to patient orders,
    including retrieving orderable items, simulating UI actions, and saving orders.
    It acts as a higher-level abstraction over the raw VistaRpcClient.
    """
    def __init__(self, vista_client: VistaRpcClient):
        """
        Initializes the OrderEntry class.
        Args:
            vista_client (VistaRpcClient): An instance of the VistaRpcClient for RPC communication.
        """
        self.vista_client = vista_client

    def get_user_info(self):
        """
        Calls the ORWU USERINFO RPC to get user information.
        This is a wrapper around the VistaRpcClient's get_user_info, logging the activity.
        Returns:
            str: Raw reply from the ORWU USERINFO RPC.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self.vista_client._log_info("Getting user info.")
        if not self.vista_client.login():
            raise ConnectionError("Not connected.")

        raw_reply = self.vista_client.invoke_rpc("ORWU USERINFO")
        self.vista_client._log_info(f"Raw reply for user info: {raw_reply}")
        return raw_reply

    def get_patient_info(self, patient_dfn: str):
        """
        Calls the ORWPT SELECT RPC to get patient information.
        This is a wrapper around the VistaRpcClient's select_patient, logging the activity.
        Args:
            patient_dfn (str): The DFN of the patient.
        Returns:
            str: Raw reply from the ORWPT SELECT RPC.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self.vista_client._log_info(f"Getting patient info for DFN: {patient_dfn}")
        if not self.vista_client.login():
            raise ConnectionError("Not connected.")

        raw_reply = self.vista_client.invoke_rpc("ORWPT SELECT", PLiteral(patient_dfn))
        self.vista_client._log_info(f"Raw reply for patient info: {raw_reply}")
        return raw_reply

    def click_orders_tab(self, patient_dfn: str):
        """
        Simulates the sequence of RPC calls that occur when a user clicks the "Orders" tab in CPRS.
        This sequence is crucial for setting the correct patient context and loading order-related data.
        RPCs: ORWDX WRLST, OREVNTX PAT, ORWORDG IEN, ORWOR VWGET, ORWORR AGET, ORWORR GET4LST.
        Args:
            patient_dfn (str): The DFN of the currently selected patient.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self.vista_client._log_info("Simulating click on orders tab.")
        if not self.vista_client.login():
            raise ConnectionError("Not connected.")

        # These RPCs are typically invoked in a sequence by CPRS GUI upon tab selection
        self.vista_client.invoke_rpc("ORWDX WRLST") # Workload List
        self.vista_client.invoke_rpc("OREVNTX PAT", PLiteral(patient_dfn)) # Set patient context for events
        self.vista_client.invoke_rpc("ORWORDG IEN", PLiteral("ALL")) # Get order display groups (from Delphi source: Orders\\rOrders.pas)
        self.vista_client.invoke_rpc("ORWOR VWGET") # Get View/Write settings
        # self.vista_client.invoke_rpc("ORTO SET UAP FLAG") # Not found in Delphi source or on server (commented out)
        self.vista_client.invoke_rpc(
            "ORWORR AGET", # Get active orders for the patient
            PLiteral(patient_dfn),
            PLiteral("2"),  # Filter for active orders
            PLiteral("1"),  # DGroup 'ALL'
            PLiteral(""),   # Start Date
            PLiteral(""),   # Stop Date
            PLiteral(""),   # PtEvtID
            PLiteral("0")    # AlertUserOnly
        )
        # self.vista_client.invoke_rpc("ORTO DGROUP") # Not found in Delphi source or on server (commented out)
        self.vista_client.invoke_rpc("ORWORR GET4LST") # Get additional list data for orders

    def click_lab_ordering_menu(self):
        """
        Simulates the sequence of RPC calls that occur when a user selects the "Labs" ordering menu item in CPRS.
        This prepares the VistA backend for lab order entry.
        RPCs: ORWU NPHASKEY, ORPWDX LOCK, ORWDX DISMSG, ORWDXM MSTYLE, ORWDXM MENU.
        Returns:
            str: The raw reply from the final ORWDXM MENU RPC, which typically contains menu options.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self.vista_client._log_info("Simulating click on lab ordering menu.")
        if not self.vista_client.login():
            raise ConnectionError("Not connected.")

        # These RPCs are typically invoked in a sequence by CPRS GUI upon selecting Lab Ordering
        self.vista_client.invoke_rpc("ORWU NPHASKEY") # Check key access (called multiple times in Delphi)
        self.vista_client.invoke_rpc("ORWU NPHASKEY")
        self.vista_client.invoke_rpc("ORWU NPHASKEY")
        self.vista_client.invoke_rpc("ORPWDX LOCK")   # Lock patient record for ordering
        self.vista_client.invoke_rpc("ORWDX DISMSG")  # Display order messages
        self.vista_client.invoke_rpc("ORWDXM MSTYLE") # Get menu style
        return self.vista_client.invoke_rpc("ORWDXM MENU") # Get the actual menu items

    def get_main_order_menu(self):
        """
        Retrieves the main order menu categories from a static JSON file or a hardcoded list.
        This method implements caching to 'static/order_menu.json' to optimize performance
        by avoiding repeated parsing or API calls for static menu data.
        Returns:
            list: A list of dictionaries, each with 'IEN' (code) and 'Name' for order categories.
        """
        self.vista_client._log_info("Getting main order menu categories.")

        # Define the path to the static JSON cache file
        ORDER_MENU_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'order_menu.json')
        order_types_data = []

        # Try to load from JSON cache
        if os.path.exists(ORDER_MENU_FILE):
            try:
                with open(ORDER_MENU_FILE, 'r') as f:
                    order_types_data = json.load(f)
                self.vista_client._log_info(f"Loaded {len(order_types_data)} order types from cache: {ORDER_MENU_FILE}")
            except (IOError, json.JSONDecodeError) as e:
                self.vista_client._log_error(f"ERROR: Could not load order types from cache ({e}). Using hardcoded list.")
                order_types_data = self._get_hardcoded_order_types() # Fallback to hardcoded list on error
        else:
            self.vista_client._log_info(f"Order types cache not found at {ORDER_MENU_FILE}. Using hardcoded list.")
            order_types_data = self._get_hardcoded_order_types() # Use hardcoded list if file doesn't exist
            # Save the hardcoded list to cache for next time
            try:
                os.makedirs(os.path.dirname(ORDER_MENU_FILE), exist_ok=True) # Ensure directory exists
                with open(ORDER_MENU_FILE, 'w') as f:
                    json.dump(order_types_data, f, indent=4) # Pretty print JSON
                self.vista_client._log_info(f"Saved order types to cache: {ORDER_MENU_FILE}")
            except IOError as e:
                self.vista_client._log_error(f"ERROR: Could not save order types to cache ({e}).")

        menu_items = []
        for item in order_types_data:
            # Map the internal structure to "IEN" and "Name" for consistency with other data
            menu_items.append({"IEN": item.get("code"), "Name": item.get("name")})
        
        return menu_items

    def _get_hardcoded_order_types(self):
        """
        Helper method to provide a hardcoded list of main order categories.
        This serves as a fallback or initial data source for `get_main_order_menu`.
        Returns:
            list: A list of dictionaries, each with 'name' and 'code' for an order type.
        """
        return [
            {"name": "Medications (Inpatient)", "code": "S.UD RX"},
            {"name": "Medications (Outpatient)", "code": "S.O RX"},
            {"name": "Labs", "code": "LAB"},
            {"name": "Radiology", "code": "RA"},
            {"name": "Consults", "code": "CON"},
            {"name": "Dietetics", "code": "DIET"},
            {"name": "Procedures", "code": "PROC"},
            {"name": "Supplies", "code": "SUP"}
        ]

    def get_consult_order_dialog_def(self):
        """
        Calls the ORWDCN32 DEF RPC to get the consult order dialog definition.
        This RPC provides the structure and default values for initiating a consult order.
        RPC: ORWDCN32 DEF
        Returns:
            str: The raw reply from the RPC containing the consult dialog definition.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self.vista_client._log_info("Getting consult order dialog definition.")
        if not self.vista_client.login():
            raise ConnectionError("Not connected.")

        raw_reply = self.vista_client.invoke_rpc("ORWDCN32 DEF", PLiteral("C")) # "C" is likely for Consults
        self.vista_client._log_info(f"Raw reply for consult order dialog definition: {raw_reply}")
        return raw_reply

    def get_med_order_dialog_def(self, is_inpatient: bool):
        """
        Calls the ORWPS1 NEWDLG RPC to get the new medication order dialog definition.
        This RPC provides the structure and default values for initiating a medication order,
        differentiated by inpatient or outpatient context.
        RPC: ORWPS1 NEWDLG
        Args:
            is_inpatient (bool): True if requesting an inpatient medication dialog, False for outpatient.
        Returns:
            str: The raw reply from the RPC containing the medication dialog definition.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self.vista_client._log_info(f"Getting med order dialog definition for inpatient status: {is_inpatient}")
        if not self.vista_client.login():
            raise ConnectionError("Not connected.")

        inpatient_param = "1" if is_inpatient else "0" # VistA often uses "1" for true, "0" for false
        
        raw_reply = self.vista_client.invoke_rpc("ORWPS1 NEWDLG", PLiteral(inpatient_param))
        self.vista_client._log_info(f"Raw reply for med order dialog definition: {raw_reply}")
        return raw_reply

    def save_order(self, patient_dfn: str, provider_duz: str, location_ien: str, order_dialog_name: str, display_group: int, orderable_item_ien: int, responses: dict, signature: str = ""):
        """
        Calls the ORWDX SAVE RPC to save a new order in VistA.
        This method typically follows a call to `accept_order` for server-side validation.
        RPC: ORWDX SAVE
        Args:
            patient_dfn (str): The DFN of the patient for whom the order is being placed.
            provider_duz (str): The DUZ of the provider placing the order.
            location_ien (str): The IEN of the patient's current location.
            order_dialog_name (str): The name of the order dialog (e.g., "LR OTHER LAB TESTS").
            display_group (int): The display group for the order (e.g., 2 for Labs).
            orderable_item_ien (int): The IEN of the specific orderable item.
            responses (dict): A dictionary mapping prompt IDs to their values,
                              containing all user input for the order dialog.
            signature (str, optional): The electronic signature of the ordering provider.
        Returns:
            str: The raw reply from the ORWDX SAVE RPC.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self.vista_client._log_info(f"Saving order for patient DFN: {patient_dfn}")
        if not self.vista_client.login():
            raise ConnectionError("Not connected.")

        self.vista_client._log_info("Performing order checks...")
        # It's typical for a VistA order entry sequence to perform validation before saving
        self.accept_order(patient_dfn, provider_duz, location_ien, order_dialog_name, display_group, orderable_item_ien, responses)
        self.vista_client._log_info("Order checks passed.")

        # Prepare the ordialog parameter for the RPC, which is a PList of user responses
        ordialog = {}
        for prompt_id, (prompt_ien, instance, ivalue) in responses.items():
            subs = f"{prompt_ien},{instance}" # Format: PromptIEN,InstanceNumber
            ordialog[subs] = ivalue # Map the formatted sub-script to its value

        params = [
            PLiteral(patient_dfn),
            PLiteral(provider_duz),
            PLiteral(location_ien),
            PLiteral(order_dialog_name),
            PLiteral(str(display_group)),
            PLiteral(str(orderable_item_ien)),
            PLiteral(""), # EditOf - null for new order
            PList(ordialog), # The collected user responses
            PLiteral(signature)
        ]

        self.vista_client._log_info("Calling ORWDX SAVE RPC...")
        raw_reply = self.vista_client.invoke_rpc("ORWDX SAVE", *params)
        self.vista_client._log_info(f"Raw reply from save order: {raw_reply}")
        return raw_reply

    def accept_order(self, patient_dfn: str, provider_duz: str, location_ien: str, order_dialog_name: str, display_group: int, orderable_item_ien: int, responses: dict):
        """
        Calls the ORWDXC ACCEPT RPC to perform server-side order checks and validations.
        This RPC does not save the order but performs necessary pre-save validations
        and may return messages or prompts to the user.
        RPC: ORWDXC ACCEPT
        Args:
            patient_dfn (str): The DFN of the patient.
            provider_duz (str): The DUZ of the provider.
            location_ien (str): The IEN of the patient's current location.
            order_dialog_name (str): The name of the order dialog.
            display_group (int): The display group for the order.
            orderable_item_ien (int): The IEN of the specific orderable item.
            responses (dict): A dictionary mapping prompt IDs to their values (user input).
        Returns:
            str: The raw reply from the ORWDXC ACCEPT RPC, which may contain validation messages.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self.vista_client._log_info("Calling ORWDXC ACCEPT RPC for order checks.")
        if not self.vista_client.login():
            raise ConnectionError("Not connected.")

        # Prepare the ordialog parameter, similar to save_order
        ordialog = {}
        for prompt_id, (prompt_ien, instance, ivalue) in responses.items():
            subs = f"{prompt_ien},{instance}"
            ordialog[subs] = ivalue

        params = [
            PLiteral(patient_dfn),
            PLiteral(provider_duz),
            PLiteral(location_ien),
            PLiteral(order_dialog_name),
            PLiteral(str(display_group)),
            PLiteral(str(orderable_item_ien)),
            PList(ordialog), # The user responses for validation
        ]

        raw_reply = self.vista_client.invoke_rpc("ORWDXC ACCEPT", *params)
        self.vista_client._log_info(f"Raw reply from accept order: {raw_reply}")
        return raw_reply

    def order_lab_test_full_sequence(self, patient_dfn: str, location_ien: str, orderable_item_ien: int, provider_duz: str, responses: dict, signature: str = ""):
        """
        Orders a lab test by executing a comprehensive sequence of RPCs that mimic
        the CPRS client's interaction flow for lab order entry.
        This method combines UI simulation steps with actual order creation and saving.
        Args:
            patient_dfn (str): The DFN of the patient.
            location_ien (str): The IEN of the patient's current location.
            orderable_item_ien (int): The IEN of the specific lab test being ordered.
            provider_duz (str): The DUZ of the provider placing the order.
            responses (dict): A dictionary of user responses/inputs for the lab order dialog.
            signature (str, optional): The electronic signature of the ordering provider.
        Returns:
            None (or potentially the result of the final save_order RPC).
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self.vista_client._log_info(f"Ordering lab test for patient DFN: {patient_dfn}")
        if not self.vista_client.login():
            raise ConnectionError("Not connected.")

        # Step 1: Simulate "clicking" the Orders Tab to set context
        self.click_orders_tab(patient_dfn)

        # Step 2: Simulate "clicking" the Lab Ordering Menu to further set context
        self.click_lab_ordering_menu()

        # Step 3: Sequence of RPCs typically invoked when selecting a lab test (e.g., "Chem 7")
        # These RPCs are often called by CPRS to fetch details, validate, and prepare the order dialog.
        self.vista_client.invoke_rpc("ORWDXM3 ISUDQO")
        self.vista_client.invoke_rpc("ORIMO ISIVQD")
        self.vista_client.invoke_rpc("ORIMO IMOLOC")
        self.vista_client.invoke_rpc("ORWDXM3 ISUDQO")
        self.vista_client.invoke_rpc("OREVNTX1 ODPTEVID")
        self.vista_client.invoke_rpc("OREVNTX1 GTEVT")
        self.vista_client.invoke_rpc("ORWDPS2 QOGRP")
        self.vista_client.invoke_rpc("ORWDXM1 BLDQRSP")
        self.vista_client.invoke_rpc("ORWDRA32 LOCTYPE")
        self.vista_client.invoke_rpc("ORIMO IMOLOC")
        self.vista_client.invoke_rpc("ORWDXC DISPLAY")
        self.vista_client.invoke_rpc("ORWU HASKEY")
        self.vista_client.invoke_rpc("ORWDX DLGDEF")
        self.vista_client.invoke_rpc("ORWDLR32 DEF", PLiteral(location_ien))
        self.vista_client.invoke_rpc("ORWDLR33 LASTTIME")
        self.vista_client.invoke_rpc("ORWDX ORDITM")
        self.vista_client.invoke_rpc("ORWDX ORDITM")
        self.vista_client.invoke_rpc("ORWDLR32 MAXDAYS")
        self.vista_client.invoke_rpc("ORWDXRO1 ISSPLY")
        self.vista_client.invoke_rpc("ORWDXRO1 ISSPLY")
        self.vista_client.invoke_rpc("ORWDX LOADRSP")
        self.vista_client.invoke_rpc("ORWDX ORDITM")

        # Step 4: Accepting and Saving the Lab Order
        # The display group for lab tests is typically 2 ("LR OTHER LAB TESTS").
        # The specific dialog name for labs is often "LR OTHER LAB TESTS".
        self.accept_order(patient_dfn, provider_duz, location_ien, "LR OTHER LAB TESTS", 2, orderable_item_ien, responses)
        self.save_order(patient_dfn, provider_duz, location_ien, "LR OTHER LAB TESTS", 2, orderable_item_ien, responses, signature)
        
        # Additional RPCs often called after saving an order in CPRS
        self.vista_client.invoke_rpc("ORWDDBA1 BASTATUS")
        self.vista_client.invoke_rpc("ORWCOM ORDEROBJ")
        self.vista_client.invoke_rpc("ORTO DGROUP")
        self.vista_client.invoke_rpc("ORWPT CWAD")
        self.vista_client.invoke_rpc("ORWDX AGAIN")
        self.vista_client.invoke_rpc("ORWDXM2 CLRRCL")

    def get_order_group_items(self, order_type: str, patient_dfn: str):
        """
        Retrieves a list of orderable items for a specific order group (category).
        This method uses different logic based on the `order_type`. For "LAB", it
        utilizes `vista_client.get_all_lab_tests` and processes the results.
        For other types, it attempts to mimic CPRS behavior to retrieve items.
        Args:
            order_type (str): The code of the order group (e.g., "LAB", "RA", "CON").
            patient_dfn (str): The DFN of the patient.
        Returns:
            list or str: A list of dictionaries (IEN, Name) for orderable items,
                         or a raw RPC reply string for non-LAB types.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self.vista_client._log_info(f"Getting order group items for order type: '{order_type}', and patient DFN: {patient_dfn}")
        if not self.vista_client.login():
            raise ConnectionError("Not connected.")

        if order_type == "LAB":
            # Use get_all_lab_tests to get a comprehensive list of lab tests
            all_lab_tests = self.vista_client.get_all_lab_tests()
            self.vista_client._log_info(f"Found {len(all_lab_tests)} lab tests from ORWLRR ALLTESTS.")
            
            orderable_lab_tests = []
            for test in all_lab_tests:
                # Assuming all tests returned are orderable for now, as the previous check was not reliable.
                orderable_lab_tests.append(test)
                self.vista_client._log_info(f"  Added orderable lab test: {test['Name']} (IEN: {test['IEN']})")

            self.vista_client._log_info(f"Parsed orderable lab items from ORWLRR ALLTESTS: {orderable_lab_tests!r}")
            return orderable_lab_tests
        else:
            # For other order types, a sequence of RPCs is typically called to set context
            # and retrieve the orderable items. This sequence is based on CPRS client analysis.
            self.vista_client.invoke_rpc("ORWDXM3 ISUDQO", PLiteral(order_type)) # Set order group context
            self.vista_client.invoke_rpc("ORIMO ISIVQO")
            self.vista_client.invoke_rpc("ORIMO IMOLOC")
            self.vista_client.invoke_rpc("ORWDXM3 ISUDQO") # Second call, common in CPRS sequences
            self.vista_client.invoke_rpc("OREVNTX1 ODPTEVID")
            self.vista_client.invoke_rpc("OREVNTX1 GTEVT")

            raw_reply = self.vista_client.invoke_rpc("ORWDPS2 QOGRP") # Get orderable items for the group

        self.vista_client._log_info(f"Raw reply for order group items: {raw_reply}")
        return raw_reply
    def get_all_orderable_items(self, patient_dfn: str):
        """
        Retrieves and combines orderable items from various services/categories in VistA.
        This method iterates through a predefined list of order types, calls
        `get_orderable_items` for each, and consolidates the results.
        Args:
            patient_dfn (str): The DFN of the patient, used for patient-specific orderable queries.
        Returns:
            dict: A dictionary where keys are formatted item names (e.g., "[Labs] CBC")
                  and values are their corresponding IENs.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self.vista_client._log_info("Attempting to retrieve all orderable items from various services.")
        if not self.vista_client.login():
            raise ConnectionError("Not connected.")

        all_items = {}
        # Define order types to query. These are based on common VistA order types.
        # This list can be expanded or refined based on specific VistA instance configuration.
        order_types = {
            "Medications (Inpatient)": "S.UD RX",
            "Medications (Outpatient)": "S.O RX",
            "Labs": "LAB",
            "Radiology": "RA",
            "Consults": "CON",
            "Dietetics": "DIET",
            "Procedures": "PROC",
            "Supplies": "SUP"
        }

        for service_name, order_type_code in order_types.items():
            self.vista_client._log_info(f"Fetching orderable items for service: {service_name} (Type: {order_type_code})")
            try:
                # Call the generic get_orderable_items method
                # Using a space as search_string often means "list all" or "default list"
                raw_reply = self.get_orderable_items(search_string=" ", order_type=order_type_code, patient_dfn=patient_dfn)
                
                if raw_reply:
                    for line in raw_reply.splitlines():
                        if line.strip():
                            parts = line.split('^')
                            if len(parts) >= 2:
                                item_ien = parts[0].strip()
                                item_name = parts[1].strip()
                                # Store with service name prefix to avoid name collisions and provide context
                                display_name = f"[{service_name}] {item_name}"
                                all_items[display_name] = item_ien
                                self.vista_client._log_info(f"  Added item: {display_name} (IEN: {item_ien})")
                            else:
                                self.vista_client._log_info(f"  WARNING: Skipping malformed line from {order_type_code}: {line!r}")
                else:
                    self.vista_client._log_info(f"No items returned for service: {service_name}")
            except Exception as e:
                self.vista_client._log_error(f"Error fetching items for {service_name}: {e}")
        
        self.vista_client._log_info(f"Finished retrieving all orderable items. Total unique items found: {len(all_items)}")
        return all_items

    def get_order_menu_items(self, patient_dfn: str, display_group: int = None):
        """
        Retrieves all available orderable items for a patient and formats them into
        a string representation suitable for display or further processing.
        Args:
            patient_dfn (str): The DFN of the patient.
            display_group (int, optional): An optional display group filter (not currently used in this method).
        Returns:
            str: A newline-separated string of "IEN^Name" for each orderable item.
        """
        self.vista_client._log_info(f"Getting order menu items for patient DFN: {patient_dfn}")
        all_orderable_items = self.get_all_orderable_items(patient_dfn) # Get all items

        # Format the dictionary into a string similar to RPC replies (IEN^Name)
        formatted_output = []
        for name, ien in all_orderable_items.items():
            formatted_output.append(f"{ien}^{name}")
        
        return "\n".join(formatted_output)

    def _parse_lab_details(self, raw_details: str) -> dict:
        """
        Parses the raw string reply from the ORWDLR32 LOAD RPC into a structured dictionary.
        This RPC returns lab test details in a complex TStrings-like format with various sections.
        Args:
            raw_details (str): The raw string reply from ORWDLR32 LOAD.
        Returns:
            dict: A structured dictionary containing parsed lab details,
                  with keys for sections like 'CollSamp', 'Specimens', 'Urgencies', etc.
        """
        details = {}
        lines = raw_details.splitlines()
        current_section = None
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line: # Skip empty lines during parsing
                i += 1
                continue

            if line.startswith('~'):
                current_section = line[1:] # Section starts with '~'
                details[current_section] = [] # Initialize section as a list
                i += 1
                continue
            
            if current_section and line:
                # 'd' prefix often indicates a single data value for a section
                if 'd' in line[:1]:
                    details[current_section] = line[1:].strip()
                # 'i' prefix often indicates an item in a list for a section
                elif 'i' in line[:1]:
                    details[current_section].append(line[1:].strip())
                # Fallback for lines without a prefix (should ideally not happen if parsing is strict)
                else:
                    details[current_section].append(line.strip()) # Add as raw string
            i += 1
            
        # Further structure specific sections that are lists of IEN^Name or similar
        # "CollSamp" (Collection Samples)
        if 'CollSamp' in details and isinstance(details['CollSamp'], list):
            samples = []
            for item in details['CollSamp']:
                parts = item.split('^')
                if len(parts) >= 3: # Expecting ID^IEN^Name
                    samples.append({'id': parts[0], 'ien': parts[1], 'name': parts[2]})
            details['CollSamp'] = samples

        # "Specimens"
        if 'Specimens' in details and isinstance(details['Specimens'], list):
            specimens = []
            for item in details['Specimens']:
                parts = item.split('^')
                if len(parts) >= 2: # Expecting IEN^Name
                    specimens.append({'ien': parts[0], 'name': parts[1]})
            details['Specimens'] = specimens

        # "Urgencies"
        if 'Urgencies' in details and isinstance(details['Urgencies'], list):
            urgencies = []
            for item in details['Urgencies']:
                parts = item.split('^')
                if len(parts) >= 2: # Expecting IEN^Name
                    urgencies.append({'ien': parts[0], 'name': parts[1]})
            details['Urgencies'] = urgencies

        return details

    def get_and_parse_lab_details(self, lab_test_ien: str) -> dict:
        """
        Fetches the raw details for a given lab test IEN from VistA and then parses them
        into a structured Python dictionary. This combines the RPC call and the parsing logic.
        Args:
            lab_test_ien (str): The IEN of the lab test.
        Returns:
            dict: A structured dictionary containing parsed lab details,
                  or an empty dictionary if no raw details are returned.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self.vista_client._log_info(f"Getting and parsing lab details for IEN: {lab_test_ien}")
        raw_details = self.vista_client.get_lab_test_details(lab_test_ien)
        if not raw_details:
            return {}
        
        parsed_details = self._parse_lab_details(raw_details)
        return parsed_details
