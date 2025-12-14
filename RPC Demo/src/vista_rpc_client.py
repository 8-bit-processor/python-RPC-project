import re
import datetime
import json
import os
from vavista.rpc import connect, PLiteral, PList, PWordProcess
from rpc_config_loader import RPCConfigLoader

class VistaRpcClient:
    """
    Manages the connection to the VistA RPC Broker and provides methods
    for invoking various Remote Procedure Calls (RPCs) on the VistA server.
    It abstracts the low-level RPC communication, handles login/connection state,
    and often parses raw VistA responses into more usable Python data structures.
    """
    def __init__(self, logger=None, comm_logger=None):
        """
        Initializes the VistaRpcClient.
        Args:
            logger: An optional logger object (e.g., GUILogger instance) for general application logs.
            comm_logger: An optional logger object for logging raw RPC requests and replies.
        """
        self.connection = None  # Stores the active connection object to VistA
        self.host = None        # VistA server IP address or hostname
        self.port = None        # VistA server port
        self.access_code = None # User's VistA access code
        self.verify_code = None # User's VistA verify code
        self.context = None     # Application context for the VistA session (e.g., "OR CPRS GUI CHART")
        self.logger = logger    # General logger
        self.comm_logger = comm_logger # RPC communication logger

    def _get_fileman_timestamp(self):
        """
        Generates a FileMan-formatted timestamp (YYYYMMDD.HHMMSS) for the current time,
        adjusted by -5 hours (likely for a specific timezone requirement common in VistA).
        Returns:
            str: The formatted FileMan timestamp.
        """
        return (datetime.datetime.now() - datetime.timedelta(hours=5)).strftime("%Y%m%d.%H%M%S")

    def _log_info(self, message):
        """
        Logs an informational message using the provided logger or prints to console.
        Args:
            message (str): The informational message to log.
        """
        if self.logger:
            self.logger.logInfo("VistaRpcClient", message)
        else:
            print(f"[INFO] VistaRpcClient: {message}")

    def _log_error(self, message):
        """
        Logs an error message using the provided logger or prints to console.
        Args:
            message (str): The error message to log.
        """
        if self.logger:
            self.logger.logError("VistaRpcClient", message)
        else:
            print(f"[ERROR] VistaRpcClient: {message}")

    def _filter_string(self, text, tab_width=8):
        result = []
        current_col = 0
        # VistA often uses CP1252 or similar extended ASCII
        # Python's default string handling is Unicode, so encode to cp1252 to match Delphi behavior
        for char_code in text.encode('cp1252', errors='replace'):
            char = chr(char_code)
            if char_code == 9:  # Tab
                spaces_to_add = tab_width - (current_col % tab_width)
                result.append(' ' * spaces_to_add)
                current_col += spaces_to_add
            elif 32 <= char_code <= 127:  # Printable ASCII
                result.append(char)
                current_col += 1
            elif 128 <= char_code <= 159:  # Control characters/Extended ASCII
                result.append('?')
                current_col += 1
            elif char_code == 10 or char_code == 13 or char_code == 160:  # LF, CR, Non-breaking space
                result.append(' ')
                current_col += 1
            elif 161 <= char_code <= 255:  # Extended ASCII
                result.append(char)
                current_col += 1
            else: # Any other character not explicitly handled
                result.append('?')
                current_col += 1

        final_result = "".join(result)
        # Handle trailing space logic: if the string ends with a space,
        # trim all trailing spaces and then add a single space back.
        # This preserves a single trailing space if one existed.
        if final_result.endswith(' '):
            final_result = final_result.rstrip(' ')
            if final_result: # If not empty after rstrip, add one space
                final_result += ' '
            # If it was all spaces, it becomes empty, which is fine.
        return final_result

    def connect_to_vista(self, host, port, access, verify, context):
        """
        Sets the connection parameters and attempts to log in to VistA.
        Args:
            host (str): VistA server IP address or hostname.
            port (str): VistA server port.
            access (str): User's VistA access code.
            verify (str): User's VistA verify code.
            context (str): Application context for the VistA session.
        Returns:
            bool: True if connection and login are successful, False otherwise.
        """
        self.host = host
        self.port = port
        self.access_code = access
        self.verify_code = verify
        self.context = context
        return self.login()

    def login(self):
        """
        Attempts to establish a connection and log in to the VistA server
        using the stored connection details.
        Returns:
            bool: True if already connected or connection/login is successful, False otherwise.
        Raises:
            ConnectionError: If connection details are missing or connection fails.
        """
        if not self.connection:
            if not all([self.host, self.port, self.access_code, self.verify_code, self.context]):
                self._log_error("Connection details are not set.")
                return False
            try:
                self._log_info(f"Connecting to {self.host}:{self.port}...")
                # The 'connect' function from vavista.rpc establishes the actual TCP connection and authentication.
                self.connection = connect(
                    self.host, int(self.port), self.access_code, self.verify_code, self.context, logger=self.logger
                )
                self._log_info("Connection successful.")
                return True
            except Exception as e:
                self._log_error(f"Connection failed: {e}")
                self.connection = None # Clear connection on failure
                raise e # Re-raise the exception for upstream handling
        return True # Already connected

    def invoke_rpc(self, rpc_name, *params):
        """
        Invokes a VistA RPC with the given parameters.
        Automatically attempts to log in if not already connected.
        Logs raw RPC requests and replies if a communication logger is provided.
        Args:
            rpc_name (str): The name of the RPC to invoke.
            *params: Variable length argument list of RPC parameters.
                     Can be a single string for parsing or individual PLiteral/PList objects.
        Returns:
            str: The raw string reply from the VistA RPC.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        if not self.login():
            raise ConnectionError("Not connected.")
        
        processed_params = []
        # If a single string parameter is passed, attempt to parse it for VistA-specific types
        if len(params) == 1 and isinstance(params[0], str):
            processed_params = self._parse_params_str(params[0])
        else:
            processed_params = list(params) # Otherwise, use parameters as-is

        # Log the RPC request if a communication logger is configured
        if self.comm_logger:
            log_msg = f"--- RPC Request ---\nName: {rpc_name}\nParameters:\n"
            for i, p in enumerate(processed_params):
                # Distinguish between PList/PWordProcess and default PLiteral
                if isinstance(p, PList) or isinstance(p, PWordProcess):
                    log_msg += f"  [{i}]: {p.__class__.__name__} = {p.value}\n"
                else:
                    log_msg += f"  [{i}]: PLiteral = \"{p.value}\"\n"
            self.comm_logger(log_msg)

        # Invoke the RPC using the established connection
        raw_reply = self.connection.invoke(rpc_name, *processed_params)

        # Log the raw RPC reply if a communication logger is configured
        if self.comm_logger:
            self.comm_logger(f"--- Raw Reply ---\n{raw_reply}\n-------------------\n")

        return raw_reply

    def _parse_params_str(self, params_str):
        """
        Parses a string of RPC parameters, typically separated by semicolons,
        into a list of PLiteral objects. This is a convenience for simpler RPC calls.
        Args:
            params_str (str): A string containing parameters (e.g., "literal:VALUE1;VALUE2").
        Returns:
            list: A list of vavista.rpc.PLiteral objects.
        """
        params = []
        if not params_str:
            return params
        parts = params_str.split(';')
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # If a parameter starts with "literal:", treat the rest as a literal string.
            # Otherwise, the entire part is a literal string.
            if part.lower().startswith("literal:"):
                params.append(PLiteral(part[len("literal:"):]))
            else:
                params.append(PLiteral(part))
        return params

    def get_user_info(self):
        """
        Retrieves basic information about the currently logged-in user from VistA.
        RPC: ORWU USERINFO
        Returns:
            dict: A dictionary containing 'DUZ', 'Name', and 'UserClass'.
        """
        raw_reply = self.invoke_rpc("ORWU USERINFO")
        parts = raw_reply.split('^')
        return {
            "DUZ": parts[0] if len(parts) > 0 else None,
            "Name": parts[1] if len(parts) > 1 else None,
            "UserClass": parts[2] if len(parts) > 2 else None
        }

    def get_note_titles(self, doc_class_ien=3, direction=1):
        """
        Retrieves the complete, paginated list of TIU document titles.
        RPC: TIU LONG LIST OF TITLES
        Args:
            doc_class_ien (int): The IEN of the document class to filter titles by (default 3 for Progress Notes).
            direction (int): Pagination direction (1 for forward).
        Returns:
            list: A list of dictionaries, each with 'IEN' and 'Title' for a note title.
        """
        self._log_info(f"Fetching all note titles for class {doc_class_ien}...")
        all_titles = []
        start_from = "" # Used for pagination to indicate where to start the next fetch
        
        while True:
            self._log_info(f"Fetching note titles chunk, starting from: '{start_from}'")
            
            # Call the RPC for the current page of titles
            raw_list = self.invoke_rpc(
                "TIU LONG LIST OF TITLES", 
                PLiteral(doc_class_ien), 
                PLiteral(start_from), 
                PLiteral(direction)
            ).splitlines()

            # If the RPC returns an empty list, it means there are no more titles.
            if not raw_list:
                self._log_info("No more titles returned, ending pagination.")
                break

            chunk_titles = []
            for item in raw_list:
                if item:
                    parts = item.split('^')
                    if len(parts) >= 2:
                        chunk_titles.append({"IEN": parts[0], "Title": parts[1]})
            
            # If the parsed chunk is empty, but raw_list wasn't, indicates a parsing issue or end of valid data.
            if not chunk_titles:
                self._log_info("Parsed chunk is empty, ending pagination.")
                break
            
            all_titles.extend(chunk_titles) # Add fetched titles to the main list
            
            # The name of the last item in the current chunk becomes the starting point for the next request.
            start_from = chunk_titles[-1]["Title"]
            self._log_info(f"Fetched {len(chunk_titles)} titles in this chunk. Next start_from: '{start_from}'")

        self._log_info(f"Found a total of {len(all_titles)} note titles.")
        return all_titles

    def get_boilerplate(self, title_ien):
        """
        Retrieves the boilerplate text for a given TIU title IEN.
        RPC: TIU LOAD BOILERPLATE TEXT
        Args:
            title_ien (str): The IEN of the TIU title.
        Returns:
            str: The raw boilerplate text from VistA.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self._log_info(f"Getting boilerplate for title IEN: {title_ien}")
        if not self.login():
            raise ConnectionError("Not connected.")
        
        # The patient DFN and visit string can be passed to resolve any embedded patient data
        # For now, we pass them as empty strings for general boilerplate retrieval.
        raw_reply = self.invoke_rpc("TIU LOAD BOILERPLATE TEXT", PLiteral(title_ien), PLiteral(""), PLiteral(""))
        self._log_info(f"Raw reply for boilerplate: {raw_reply}")
        return raw_reply

    def search_patient(self, search_term):
        """
        Searches for patients in VistA based on a search term.
        RPC: ORWPT LIST ALL
        Args:
            search_term (str): The patient name or part of the name to search for.
        Returns:
            list: A list of dictionaries, each with 'DFN' and 'Name' of matching patients.
        """
        raw_list = self.invoke_rpc("ORWPT LIST ALL", PLiteral(search_term), PLiteral("1")).splitlines()
        patients = []
        for item in raw_list:
            if item:
                parts = item.split('^')
                if len(parts) >= 2:
                    patients.append({"DFN": parts[0], "Name": parts[1]})
        return patients

    def get_doctor_patients(self, provider_ien):
        """
        Retrieves a list of patients associated with a specific provider.
        RPC: ORQPT PROVIDER PATIENTS
        Args:
            provider_ien (str): The IEN (Internal Entry Number) of the provider.
        Returns:
            list: A list of dictionaries, each with 'DFN' and 'Name' of the patients.
        """
        raw_list = self.invoke_rpc("ORQPT PROVIDER PATIENTS", PLiteral(provider_ien)).splitlines()
        patients = []
        for item in raw_list:
            if item:
                parts = item.split('^')
                if len(parts) >= 2:
                    patients.append({"DFN": parts[0], "Name": parts[1]})
        return patients

    def select_patient(self, dfn):
        """
        Selects a patient in VistA and retrieves basic demographic information.
        RPC: ORWPT SELECT
        Args:
            dfn (str): The DFN (internal entry number) of the patient to select.
        Returns:
            dict: A dictionary containing 'Name', 'Sex', and 'DOB' of the selected patient.
        """
        raw_reply = self.invoke_rpc("ORWPT SELECT", PLiteral(dfn))
        parts = raw_reply.split('^')
        return {
            "Name": parts[0] if len(parts) > 0 else None,
            "Sex": parts[1] if len(parts) > 1 else None,
            "DOB": parts[2] if len(parts) > 2 else None
        }

    def get_orders(self, patient_dfn, filter_str="2"):
        """
        Retrieves a list of orders for a patient.
        RPC: ORWORR AGET
        Args:
            patient_dfn (str): The DFN of the patient.
            filter_str (str): A filter string (e.g., "2" for active orders).
        Returns:
            list: A list of dictionaries, each containing order 'ID', 'DGroup', and 'OrderTime'.
        """
        self._log_info(f"Getting orders for patient DFN: {patient_dfn} with filter: {filter_str}")
        if not self.login():
            raise ConnectionError("Not connected.")
        
        raw_list = self.invoke_rpc(
            "ORWORR AGET", 
            PLiteral(patient_dfn), 
            PLiteral(filter_str), 
            PLiteral("1"), # DGroup 'ALL'
            PLiteral(""),  # Start Date
            PLiteral(""),  # Stop Date
            PLiteral(""),  # PtEvtID
            PLiteral("0")   # AlertUserOnly
        ).splitlines()
        
        orders = []
        # Check if the reply indicates success (usually starts with '1')
        if not raw_list or not raw_list[0].startswith('1'):
            self._log_info("No orders found or error in reply.")
            return orders

        for item in raw_list[1:]: # Skip the first line which is often a status indicator
            if item:
                parts = item.split('^')
                if len(parts) >= 3:
                    orders.append({
                        "ID": parts[0],
                        "DGroup": parts[1],
                        "OrderTime": parts[2]
                    })
        self._log_info(f"Found {len(orders)} orders.")
        return orders

    def get_order_detail(self, order_id, patient_dfn):
        """
        Retrieves the detailed information for a single order.
        RPC: ORQOR DETAIL
        Args:
            order_id (str): The ID of the order.
            patient_dfn (str): The DFN of the patient associated with the order.
        Returns:
            str: The raw reply containing the order details.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self._log_info(f"Getting detail for order ID: {order_id}")
        if not self.login():
            raise ConnectionError("Not connected.")
        
        raw_reply = self.invoke_rpc("ORQOR DETAIL", PLiteral(order_id), PLiteral(patient_dfn))
        self._log_info(f"Raw reply for order detail: {raw_reply}")
        return raw_reply

    def discontinue_order(self, order_id, provider_duz, location_ien, reason_ien):
        """
        Discontinues an order in VistA. This involves a validation step before the actual discontinuation.
        RPCs: ORWDXA VALID, ORWDXA DC
        Args:
            order_id (str): The ID of the order to discontinue.
            provider_duz (str): The DUZ of the provider performing the action.
            location_ien (str): The IEN of the location.
            reason_ien (str): The IEN of the reason for discontinuation.
        Returns:
            str: The raw reply from the discontinuation RPC.
        Raises:
            ConnectionError: If not connected to VistA.
            Exception: If validation fails or the discontinuation RPC returns an error.
        """
        self._log_info(f"Discontinuing order ID: {order_id}")
        if not self.login():
            raise ConnectionError("Not connected.")

        # Step 1: Validate the discontinuation action
        self._log_info(f"Validating discontinue action for order ID: {order_id}")
        error_msg = self.invoke_rpc("ORWDXA VALID", PLiteral(order_id), PLiteral("DC"), PLiteral(provider_duz))
        if error_msg and error_msg != "1": # VistA RPCs often return '1' for success or error message
            self._log_error(f"Validation failed for discontinuing order {order_id}: {error_msg}")
            raise Exception(f"Validation failed for discontinuing order {order_id}: {error_msg}")
        self._log_info("Discontinue action validation successful.")

        # Step 2: Execute the discontinuation
        raw_reply = self.invoke_rpc("ORWDXA DC", PLiteral(order_id), PLiteral(provider_duz), PLiteral(location_ien), PLiteral(reason_ien), PLiteral("0"), PLiteral("0"))
        self._log_info(f"Raw reply from discontinue order: {raw_reply}")
        return raw_reply

    def get_renew_fields(self, order_id):
        """
        Retrieves the fields necessary to renew an order from VistA.
        RPC: ORWDXR RNWFLDS
        Args:
            order_id (str): The ID of the order to renew.
        Returns:
            dict: A dictionary containing parsed renewal fields like 'BaseType', 'StartTime', etc.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self._log_info(f"Getting renew fields for order ID: {order_id}")
        if not self.login():
            raise ConnectionError("Not connected.")
        
        raw_reply = self.invoke_rpc("ORWDXR RNWFLDS", PLiteral(order_id))
        self._log_info(f"Raw reply for renew fields: {raw_reply}")
        
        lines = raw_reply.splitlines()
        if not lines:
            self._log_error("No data returned for renew fields.")
            return {}

        # Parse the first line for key-value pairs
        parts = lines[0].split('^')
        renew_fields = {
            "BaseType": parts[0] if len(parts) > 0 else None,
            "StartTime": parts[1] if len(parts) > 1 else None,
            "StopTime": parts[2] if len(parts) > 2 else None,
            "Refills": parts[3] if len(parts) > 3 else None,
            "Pickup": parts[4] if len(parts) > 4 else None,
            # Remaining lines are treated as comments
            "Comments": "\n".join(lines[1:])
        }
        
        self._log_info(f"Processed renew fields: {renew_fields}")
        return renew_fields

    def renew_order(self, order_id, patient_dfn, provider_duz, location_ien, renew_fields):
        """
        Renews an existing order in VistA. This involves validation and sending structured parameters.
        RPCs: ORWDXA VALID, ORWDXR RENEW
        Args:
            order_id (str): The ID of the order to renew.
            patient_dfn (str): The DFN of the patient.
            provider_duz (str): The DUZ of the provider.
            location_ien (str): The IEN of the location.
            renew_fields (dict): A dictionary containing the fields for renewal (e.g., from get_renew_fields).
        Returns:
            str: The raw reply from the renewal RPC.
        Raises:
            ConnectionError: If not connected to VistA.
            Exception: If validation fails.
        """
        self._log_info(f"Renewing order ID: {order_id} for patient DFN: {patient_dfn}")
        if not self.login():
            raise ConnectionError("Not connected.")

        # Step 1: Validate the renewal action
        self._log_info(f"Validating renew action for order ID: {order_id}")
        error_msg = self.invoke_rpc("ORWDXA VALID", PLiteral(order_id), PLiteral("RN"), PLiteral(provider_duz))
        if error_msg and error_msg != "1": # VistA RPCs often return '1' for success or error message
            self._log_error(f"Validation failed for renewing order {order_id}: {error_msg}")
            raise Exception(f"Validation failed for renewing order {order_id}: {error_msg}")
        self._log_info("Renew action validation successful.")

        # Prepare parameters for the ORWDXR RENEW RPC
        # This RPC expects a PList for structured parameters
        param_list = {
            "1": f"{renew_fields.get('BaseType', '')}^{renew_fields.get('StartTime', '')}^{renew_fields.get('StopTime', '')}^{renew_fields.get('Refills', '')}^{renew_fields.get('Pickup', '')}"
        }
        comments = renew_fields.get('Comments', '').splitlines()
        for i, line in enumerate(comments):
            param_list[str(i + 2)] = line # Add comments as additional parameters

        self._log_info(f"Calling ORWDXR RENEW for order ID: {order_id}")
        raw_reply = self.invoke_rpc(
            "ORWDXR RENEW",
            PLiteral(order_id),
            PLiteral(patient_dfn),
            PLiteral(provider_duz),
            PLiteral(location_ien),
            PList(param_list), # Send structured parameters
            PLiteral("0"), # IsComplex (0 for simple renew)
            PLiteral("")  # IMOOrderAppt
        )

        self._log_info(f"Raw reply from renew order: {raw_reply}")
        return raw_reply

    def fetch_patient_notes(self, dfn, doc_class_ien=3, context=1, max_docs=100):
        """
        Fetches a list of patient notes (TIU documents) based on specified criteria.
        RPC: TIU DOCUMENTS BY CONTEXT
        Args:
            dfn (str): The DFN of the patient.
            doc_class_ien (int): The IEN of the document class (default 3 for Progress Notes).
            context (int): The context for the search (e.g., 1 for signed, 2 for unsigned, 15 for all).
            max_docs (int): Maximum number of documents to retrieve.
        Returns:
            list: A list of dictionaries, each with 'IEN', 'Title', and 'Date' of the notes.
        """
        raw_list = self.invoke_rpc(
            "TIU DOCUMENTS BY CONTEXT",
            PLiteral(doc_class_ien), PLiteral(context), PLiteral(dfn),
            PLiteral(""), PLiteral(""), PLiteral("0"), # These are placeholder parameters for filters not used here
            PLiteral(max_docs), PLiteral("D"), PLiteral("0") # D for descending date order, 0 for include addendums
        ).splitlines()
        notes = []
        for item in raw_list:
            if item:
                parts = item.split('^')
                if len(parts) >= 3: # Expecting at least IEN^Title^Date
                    notes.append({"IEN": parts[0], "Title": parts[1], "Date": parts[2]})
        return notes

    def fetch_patient_encounters(self, dfn):
        """
        Fetches a list of patient encounters/visits.
        RPC: ORWPCE GET VISITS
        Args:
            dfn (str): The DFN of the patient.
        Returns:
            list: A list of dictionaries, each with 'VisitStr', 'Location', and 'DateTime' of the encounters.
        """
        raw_list = self.invoke_rpc("ORWPCE GET VISITS", PLiteral(dfn), PLiteral(""), PLiteral("")).splitlines()
        encounters = []
        for item in raw_list:
            if item:
                parts = item.split('^')
                if len(parts) >= 2: # Expecting at least VisitStr^Location (DateTime is often part of Location or implicit)
                    encounters.append({"VisitStr": parts[0], "Location": parts[1], "DateTime": parts[1]}) # DateTime here is likely derived from Location string
        return encounters

    def get_patient_dfn(self, patient_name):
        """
        Retrieves the DFN (internal entry number) for a patient given their name.
        This is a convenience method that uses `search_patient` and returns the DFN of the first match.
        Args:
            patient_name (str): The name of the patient to find.
        Returns:
            str: The DFN of the patient, or None if not found.
        """
        patients = self.search_patient(patient_name)
        if patients and len(patients) > 0:
            return patients[0]["DFN"]
        return None

    def get_unsigned_notes(self, patient_dfn):
        """
        Retrieves unsigned notes for a specific patient.
        This is a convenience method that calls `fetch_patient_notes` with a context for unsigned notes.
        Args:
            patient_dfn (str): The DFN of the patient.
        Returns:
            list: A list of unsigned notes.
        """
        return self.fetch_patient_notes(patient_dfn, context=3) # Context 3 typically refers to unsigned notes

    def _set_document_text(self, note_ien, note_text_lines, suppress_commit=1):
        """
        Sets the text for a TIU document, handling pagination for potentially large notes.
        RPC: TIU SET DOCUMENT TEXT
        Args:
            note_ien (str): The IEN of the note to update.
            note_text_lines (list): A list of strings, where each string is a line of the note text.
            suppress_commit (int): If 1, suppresses the final commit until a subsequent RPC. If 0, commits immediately.
        Returns:
            str: An error message if an error occurred during text setting, otherwise an empty string.
        """
        self._log_info(f"Setting document text for note IEN: {note_ien}")
        DOCUMENT_PAGE_SIZE = 300 # VistA's TIU SET DOCUMENT TEXT RPC expects text in pages of max 300 lines
        error_message = ""

        num_lines = len(note_text_lines)
        pages = (num_lines // DOCUMENT_PAGE_SIZE) + (1 if num_lines % DOCUMENT_PAGE_SIZE > 0 else 0)
        if pages == 0: pages = 1 # Even an empty note needs to send at least one "page" RPC call
        
        self._log_info(f"Note has {num_lines} lines, which will be sent in {pages} pages.")

        # Special handling for empty notes: send a single RPC call with an empty text block
        if num_lines == 0:
            self._log_info("Note is empty, sending empty text block.")
            multiples = {'"HDR"': f"1^{pages}"} # Header indicates page 1 of 1
            result = self.invoke_rpc(
                "TIU SET DOCUMENT TEXT",
                PLiteral(note_ien),
                PList(multiples),
                PLiteral(str(suppress_commit))
            )
            if result and result.startswith('0^'): # VistA often returns '0^1' for success
                error_message = ""
            else:
                error_message = result if result else "Unknown error during empty text set."
            return error_message

        # Iterate through pages and send text chunks
        for page_num in range(1, pages + 1):
            self._log_info(f"Sending page {page_num} of {pages}.")
            start_index = (page_num - 1) * DOCUMENT_PAGE_SIZE
            end_index = min(start_index + DOCUMENT_PAGE_SIZE, num_lines)
            current_page_lines = note_text_lines[start_index:end_index]

            multiples = {}
            for i, line in enumerate(current_page_lines):
                # Filter each line to ensure VistA compatibility
                filtered_line = self._filter_string(line)
                multiples[f'"TEXT",{i + 1},0'] = filtered_line # Format for text lines

            multiples['"HDR"'] = f"{page_num}^{pages}" # Header with current page number and total pages

            result = self.invoke_rpc(
                "TIU SET DOCUMENT TEXT",
                PLiteral(note_ien),
                PList(multiples), # Send text lines and header as a PList
                PLiteral(str(suppress_commit))
            )

            if result:
                parts = result.split('^')
                # Check for specific error format in VistA reply
                if len(parts) >= 4 and parts[3]:
                    error_message = parts[3]
                elif len(parts) >= 2 and parts[1] == '1': # Success usually '1'
                    error_message = ""
                else:
                    error_message = result # General error
            else:
                error_message = "Unknown error during text set."

            if error_message:
                self._log_error(f"Error setting document text for note {note_ien}, page {page_num}: {error_message}")
                return error_message # Stop and return error on first failure

        self._log_info(f"Successfully set document text for note IEN: {note_ien}")
        return error_message # Return empty string on success

    def read_note_content(self, note_ien):
        """
        Retrieves the full text content of a specific TIU document.
        RPC: TIU GET RECORD TEXT
        Args:
            note_ien (str): The IEN of the TIU document.
        Returns:
            str: The raw text content of the note.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        if not self.login():
            raise ConnectionError("Not connected.")
        
        raw_reply = self.invoke_rpc("TIU GET RECORD TEXT", PLiteral(note_ien))
        return raw_reply

    def lock_record(self, note_ien):
        """
        Locks a TIU record for editing, preventing other users from modifying it concurrently.
        RPC: TIU LOCK RECORD
        Args:
            note_ien (str): The IEN of the TIU record to lock.
        Returns:
            bool: True if the record was successfully locked.
        Raises:
            ConnectionError: If not connected to VistA.
            Exception: If the lock operation fails.
        """
        self._log_info(f"Locking record for note IEN: {note_ien}")
        if not self.login():
            raise ConnectionError("Not connected.")
        lock_result = self.invoke_rpc("TIU LOCK RECORD", PLiteral(note_ien))
        if not lock_result.startswith('0'): # VistA RPCs often return '0^...' for success
            self._log_error(f"Failed to lock note {note_ien}: {lock_result}")
            raise Exception(f"Failed to lock note {note_ien}: {lock_result}")
        self._log_info(f"Record {note_ien} locked successfully.")
        return True

    def unlock_record(self, note_ien):
        """
        Unlocks a TIU record, releasing it for other users or processes.
        RPC: TIU UNLOCK RECORD
        Args:
            note_ien (str): The IEN of the TIU record to unlock.
        Returns:
            bool: True if the record was unlocked (or if the RPC returned a non-error).
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self._log_info(f"Unlocking record for note IEN: {note_ien}")
        if not self.login():
            raise ConnectionError("Not connected.")
        unlock_result = self.invoke_rpc("TIU UNLOCK RECORD", PLiteral(note_ien))
        if not unlock_result.startswith('1'): # VistA RPCs often return '1' for success, '0' for error
            self._log_error(f"Failed to unlock note {note_ien}: {unlock_result}")
        self._log_info(f"Record {note_ien} unlocked.")
        return True

    def create_note(self, patient_dfn, title_ien, note_text, encounter_location_ien, encounter_datetime, visit_str, es_code=None, sign_note=True):
        """
        Creates, populates, and optionally signs a new TIU document (note) in VistA.
        This method orchestrates a sequence of RPC calls: TIU CREATE RECORD, TIU LOCK RECORD,
        TIU UPDATE RECORD (for subject), TIU AUTHORIZATION, TIU SET DOCUMENT TEXT,
        TIU SIGN RECORD, and TIU UNLOCK RECORD.
        Args:
            patient_dfn (str): The DFN of the patient the note is for.
            title_ien (str): The IEN of the TIU title for the note.
            note_text (str): The main content of the note.
            encounter_location_ien (str): The IEN of the encounter location.
            encounter_datetime (str): FileMan-formatted datetime of the encounter.
            visit_str (str): The VistA visit string (e.g., "IEN;DATETIME;TYPE").
            es_code (str, optional): The Electronic Signature Code to sign the note. Required if sign_note is True.
            sign_note (bool): If True, attempts to sign the note after creation.
        Returns:
            str: A message indicating success, including the note IEN.
        Raises:
            ConnectionError: If not connected to VistA.
            Exception: If any step in the note creation process fails.
            ValueError: If sign_note is True but es_code is not provided.
        """
        self._log_info(f"Creating note with title IEN {title_ien} for patient DFN {patient_dfn}")
        user_info = self.get_user_info()
        author_ien = user_info.get("DUZ") # Get the DUZ of the current user as the author

        # Parameters for creating the initial record, including author, encounter, etc.
        multiples = {
            "1202": author_ien,                # Author
            "1301": encounter_datetime,        # Encounter Date/Time
            "1205": encounter_location_ien,    # Encounter Location
            "1701": ""                         # Subject (initially empty)
        }
        
        # Step 1: Create the initial TIU record
        note_ien_result = self.invoke_rpc(
            "TIU CREATE RECORD",
            PLiteral(patient_dfn),
            PLiteral(title_ien),
            PLiteral(""), # Visit IEN (optional, can be derived from visit_str)
            PLiteral(""), # Consultation IEN (not used here)
            PLiteral(""), # Problem IEN (not used here)
            PList(multiples), # Structured parameters
            PLiteral(visit_str), # Visit string
            PLiteral("1") # Suppress commit (0=commit, 1=suppress)
        )

        if not note_ien_result or not note_ien_result.isdigit():
            self._log_error(f"Failed to create note record. Server returned: {note_ien_result}")
            raise Exception(f"Failed to create note record. Server returned: {note_ien_result}")
        note_ien = note_ien_result
        self._log_info(f"Successfully created note record. IEN: {note_ien}")

        try:
            # Step 2: Lock the record for editing
            self.lock_record(note_ien)

            # Extract first line for subject and filter it
            subject_line = ""
            if note_text:
                first_line = note_text.splitlines()[0]
                filtered_subject = self._filter_string(first_line)
                # VistA subject lines have a max length
                subject_line = filtered_subject[:80] if len(filtered_subject) > 80 else filtered_subject
            
            # Step 3: Update the note record with a subject line if available
            if subject_line:
                self._log_info(f"Updating note with subject: {subject_line}")
                update_params = {"1701": subject_line}
                self.invoke_rpc("TIU UPDATE RECORD", PLiteral(note_ien), PList(update_params))

            # Step 4: Authorize the editing action
            auth_result = self.invoke_rpc("TIU AUTHORIZATION", PLiteral(note_ien), PLiteral("EDIT RECORD"))
            if not auth_result.startswith('1'): # Expecting '1' for success
                self._log_error(f"Failed to authorize note {note_ien}: {auth_result}")
                # This might not be a fatal error, so we log but don't raise
                # Depending on VistA configuration, this might be a soft warning

            text_lines = note_text.splitlines()
            # Step 5: Set the document text. Suppress commit if signing, commit immediately if not.
            error_message = self._set_document_text(note_ien, text_lines, suppress_commit=0 if not sign_note else 1)
            if error_message:
                raise Exception(f"Failed to set document text for note {note_ien}: {error_message}")
            self._log_info("Successfully saved note text.")

            # Step 6: Optionally sign the note
            if sign_note:
                if not es_code:
                    raise ValueError("Electronic signature is required to sign the note.")
                self._log_info(f"Signing note {note_ien}")
                sign_result = self.invoke_rpc("TIU SIGN RECORD", PLiteral(note_ien), PLiteral(es_code))
                if not sign_result.startswith('0^'): # Expected success format is often '0^1'
                    raise Exception(f"Failed to sign note. Server returned: {sign_result}")
                self._log_info(f"Note {note_ien} signed successfully.")
                return f"Note {note_ien} created and signed successfully."
        finally:
            # Ensure the record is unlocked even if errors occur
            self.unlock_record(note_ien)
        
        return f"Note {note_ien} created successfully (unsigned)."

    def delete_note(self, note_ien, reason="Entered in error"):
        """
        Deletes a TIU document (note) from VistA.
        RPC: TIU DELETE RECORD
        Args:
            note_ien (str): The IEN of the note to delete.
            reason (str): The reason for deleting the note (default: "Entered in error").
        Returns:
            bool: True if the note was successfully deleted.
        Raises:
            ConnectionError: If not connected to VistA.
            Exception: If the deletion RPC returns an error.
        """
        self._log_info(f"Deleting note IEN: {note_ien} with reason: {reason}")
        if not self.login():
            raise ConnectionError("Not connected.")
        
        delete_result = self.invoke_rpc("TIU DELETE RECORD", PLiteral(note_ien), PLiteral(reason))
        self._log_info(f"Raw delete result: {delete_result}")
        
        parts = delete_result.split('^')
        # VistA RPCs often return '0^...' for success, '1^...' for error
        if parts[0] != '0':
            self._log_error(f"Failed to delete note {note_ien}: {parts[1] if len(parts) > 1 else delete_result}")
            raise Exception(f"Failed to delete note {note_ien}: {parts[1] if len(parts) > 1 else delete_result}")
        
        self._log_info(f"Successfully deleted note {note_ien}.")
        return True

    def create_addendum(self, parent_ien, addendum_text, es_code=None, sign_addendum=True):
        """
        Creates, populates, and optionally signs a new addendum to an existing TIU document.
        This involves RPC calls: TIU CREATE ADDENDUM RECORD, TIU LOCK RECORD,
        TIU SET DOCUMENT TEXT, TIU SIGN RECORD, and TIU UNLOCK RECORD.
        Args:
            parent_ien (str): The IEN of the parent TIU document to which the addendum will be attached.
            addendum_text (str): The content of the addendum.
            es_code (str, optional): The Electronic Signature Code to sign the addendum. Required if sign_addendum is True.
            sign_addendum (bool): If True, attempts to sign the addendum after creation.
        Returns:
            str: The IEN of the newly created addendum.
        Raises:
            ConnectionError: If not connected to VistA.
            Exception: If any step in the addendum creation process fails.
            ValueError: If sign_addendum is True but es_code is not provided.
        """
        self._log_info(f"Creating addendum for parent IEN: {parent_ien}")
        if not self.login():
            raise ConnectionError("Not connected.")

        user_info = self.get_user_info()
        author_ien = user_info.get("DUZ") # Get the DUZ of the current user as the author
        
        # Parameters for creating the addendum record
        multiples = {
            "1202": author_ien,                 # Author
            "1301": self._get_fileman_timestamp(), # Current timestamp for addendum date/time
        }

        # Step 1: Create the initial addendum record
        addendum_ien_result = self.invoke_rpc(
            "TIU CREATE ADDENDUM RECORD",
            PLiteral(parent_ien),
            PList(multiples), # Structured parameters
            PLiteral("1") # Suppress commit
        )

        if not addendum_ien_result or not addendum_ien_result.isdigit():
            self._log_error(f"Failed to create addendum record. Server returned: {addendum_ien_result}")
            raise Exception(f"Failed to create addendum record. Server returned: {addendum_ien_result}")
        addendum_ien = addendum_ien_result
        self._log_info(f"Successfully created addendum record. IEN: {addendum_ien}")

        try:
            # Step 2: Lock the record for editing
            self.lock_record(addendum_ien)

            text_lines = addendum_text.splitlines()
            # Step 3: Set the document text for the addendum
            error_message = self._set_document_text(addendum_ien, text_lines, suppress_commit=0) # Commit text immediately
            if error_message:
                raise Exception(f"Failed to set document text for addendum {addendum_ien}: {error_message}")
            self._log_info("Successfully saved addendum text.")

            # Step 4: Optionally sign the addendum
            if sign_addendum:
                if not es_code:
                    raise ValueError("Electronic signature is required to sign the addendum.")
                self._log_info(f"Signing addendum {addendum_ien}")
                sign_result = self.invoke_rpc("TIU SIGN RECORD", PLiteral(addendum_ien), PLiteral(es_code))
                if not sign_result.startswith('0^'): # Expected success format is often '0^1'
                    raise Exception(f"Failed to sign addendum. Server returned: {sign_result}")
                self._log_info(f"Addendum {addendum_ien} signed successfully.")

        finally:
            # Ensure the addendum record is unlocked even if errors occur
            self.unlock_record(addendum_ien)

    def get_additional_signers(self, note_ien):
        """
        Retrieves the list of additional signers for a TIU document.
        RPC: TIU GET ADDITIONAL SIGNERS
        Args:
            note_ien (str): The IEN of the TIU document.
        Returns:
            list: A list of dictionaries, each with 'DUZ' and 'Name' of additional signers.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self._log_info(f"Getting additional signers for note IEN: {note_ien}")
        if not self.login():
            raise ConnectionError("Not connected.")
        raw_list = self.invoke_rpc("TIU GET ADDITIONAL SIGNERS", PLiteral(note_ien)).splitlines()
        signers = []
        for item in raw_list:
            if item:
                parts = item.split('^')
                if len(parts) >= 2:
                    signers.append({"DUZ": parts[0], "Name": parts[1]})
        self._log_info(f"Found {len(signers)} additional signers.")
        return signers



    def get_lab_order_dialog_def(self, location_ien: str, division_ien: str = "0"):
        """
        Calls the ORWDLR32 DEF RPC to get the lab order dialog definition.
        This RPC provides default values and lists for various fields in the lab ordering dialog.
        RPC: ORWDLR32 DEF
        Args:
            location_ien (str): The IEN of the patient's current location.
            division_ien (str, optional): The IEN of the division (default "0").
        Returns:
            str: The raw reply from the RPC containing the dialog definition.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self._log_info(f"Getting lab order dialog definition for location IEN: {location_ien}")
        if not self.login():
            raise ConnectionError("Not connected.")

        params = [
            PLiteral(location_ien),
            PLiteral(division_ien)
        ]

        raw_reply = self.invoke_rpc("ORWDLR32 DEF", *params)
        self._log_info(f"Raw reply for lab order dialog definition: {raw_reply}")
        return raw_reply

    def _parse_vista_shortlist(self, raw_reply: str) -> list:
        """
        Parses the "~ShortList" section from a VistA RPC reply into a list of dictionaries.
        This format is common for RPCs returning a short, selectable list of items (e.g., orderable items).
        Args:
            raw_reply (str): The raw string reply from a VistA RPC.
        Returns:
            list: A list of dictionaries, each with 'IEN' and 'Name' for the items in the ShortList.
        """
        items = []
        in_shortlist = False
        for line in raw_reply.splitlines():
            line = line.strip()
            if not line: continue # Skip empty lines

            if line == "~ShortList":
                in_shortlist = True # Start parsing when "~ShortList" marker is found
                continue
            if in_shortlist and line.startswith("~") and line != "~ShortList":
                # Reached the end of ShortList section (another section marker)
                in_shortlist = False
                break
            if in_shortlist and line:
                # Example expected format: iQ1321^CBC
                if line.startswith("iQ"): # VistA often prefixes IENs in shortlists with 'iQ'
                    parts = line[2:].split('^') # Remove 'iQ' and split by '^'
                    if len(parts) >= 2:
                        ien = parts[0].strip()
                        name = parts[1].strip()
                        self._log_info(f"_parse_vista_shortlist: Extracted IEN: {ien}, Name: {name}")
                        items.append({"IEN": ien, "Name": name})
        return items

    def get_orderable_items(self, search_string: str, order_type: str, patient_dfn: str):
        """
        Calls the ORWDPS2 OISLCT RPC to get a list of orderable items based on a search string and order type.
        This RPC is commonly used for searching specific orderable items within a category (e.g., LAB, MEDICATION).
        RPC: ORWDPS2 OISLCT
        Args:
            search_string (str): The search term for orderable items.
            order_type (str): The type of order (e.g., "LR" for Lab, "PS" for Pharmacy).
            patient_dfn (str): The DFN of the patient (may affect results for patient-specific orderables).
        Returns:
            str: The raw reply from the RPC containing the list of orderable items.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self._log_info(f"Getting orderable items for search string: '{search_string}', order type: '{order_type}', and patient DFN: {patient_dfn}")
        if not self.login():
            raise ConnectionError("Not connected.")

        params = [
            PLiteral(search_string),
            PLiteral(order_type),
            PLiteral(patient_dfn)
        ]

        raw_reply = self.invoke_rpc("ORWDPS2 OISLCT", *params)
        self._log_info(f"Raw reply for orderable items: {raw_reply}")
        return raw_reply

    def get_atomic_lab_tests(self, start_from="", direction=1):
        """
        Retrieves a paginated list of atomic lab tests from VistA.
        RPC: ORWLRR ATOMIC
        Args:
            start_from (str, optional): The name of the test to start the list from (for pagination).
            direction (int, optional): Pagination direction (1 for forward).
        Returns:
            list: A list of dictionaries, each with 'IEN' and 'Name' of atomic lab tests.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self._log_info(f"Getting atomic lab tests starting from: '{start_from}', direction: {direction}")
        if not self.login():
            raise ConnectionError("Not connected.")
        
        raw_list = self.invoke_rpc("ORWLRR ATOMIC", PLiteral(start_from), PLiteral(direction)).splitlines()
        tests = []
        for item in raw_list:
            if item:
                parts = item.split('^')
                if len(parts) >= 2:
                    tests.append({"IEN": parts[0], "Name": parts[1]})
        self._log_info(f"Found {len(tests)} atomic lab tests.")
        return tests

    def get_chem_lab_tests(self, start_from="", direction=1):
        """
        Retrieves a paginated list of chemistry lab tests from VistA.
        RPC: ORWLRR CHEMTEST
        Args:
            start_from (str, optional): The name of the test to start the list from (for pagination).
            direction (int, optional): Pagination direction (1 for forward).
        Returns:
            list: A list of dictionaries, each with 'IEN' and 'Name' of chemistry lab tests.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self._log_info(f"Getting chemistry lab tests starting from: '{start_from}', direction: {direction}")
        if not self.login():
            raise ConnectionError("Not connected.")
        
        raw_list = self.invoke_rpc("ORWLRR CHEMTEST", PLiteral(start_from), PLiteral(direction)).splitlines()
        tests = []
        for item in raw_list:
            if item:
                parts = item.split('^')
                if len(parts) >= 2:
                    tests.append({"IEN": parts[0], "Name": parts[1]})
        self._log_info(f"Found {len(tests)} chemistry lab tests.")
        return tests

    def get_all_lab_tests(self, start_from="", direction=1, force_refresh=False):
        """
        Retrieves a comprehensive list of all lab tests using ORWLRR ALLTESTS, with pagination.
        This function implements local caching to 'static/lab_tests.json' to improve performance
        and reduce repeated calls to VistA.
        RPC: ORWLRR ALLTESTS
        Args:
            start_from (str, optional): The name of the test to start the list from (for pagination).
            direction (int, optional): Pagination direction (1 for forward).
            force_refresh (bool, optional): If True, bypasses the cache and fetches data from VistA.
        Returns:
            list: A list of dictionaries, each with 'IEN' and 'Name' of all lab tests.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_file = os.path.join(project_root, 'static', 'lab_tests.json')

        # Attempt to load from cache first, unless force_refresh is True
        if not force_refresh and os.path.exists(cache_file):
            self._log_info(f"Loading lab tests from local cache file: {cache_file}")
            try:
                with open(cache_file, 'r') as f:
                    all_tests = json.load(f)
                self._log_info(f"Successfully loaded {len(all_tests)} tests from cache.")
                return all_tests
            except (IOError, json.JSONDecodeError) as e:
                self._log_error(f"Error reading cache file {cache_file}: {e}. Refreshing from server.")

        self._log_info("Getting all lab tests with pagination from server...")
        if not self.login():
            raise ConnectionError("Not connected.")

        all_tests = []
        current_start_from = start_from
        while True:
            self._log_info(f"Fetching lab tests starting from: '{current_start_from}', direction: {direction}")
            raw_list = self.invoke_rpc("ORWLRR ALLTESTS", PLiteral(current_start_from), PLiteral(direction)).splitlines()

            if not raw_list:
                self._log_info("No more lab tests returned, ending pagination.")
                break

            chunk_tests = []
            for item in raw_list:
                if item:
                    parts = item.split('^')
                    if len(parts) >= 2:
                        chunk_tests.append({"IEN": parts[0], "Name": parts[1]})
            
            if not chunk_tests:
                self._log_info("Returned list is empty, ending pagination.")
                break

            all_tests.extend(chunk_tests)
            # The last item's name is the starting point for the next chunk in pagination.
            current_start_from = chunk_tests[-1]["Name"]
            self._log_info(f"Fetched {len(chunk_tests)} tests in this chunk. Next start from: '{current_start_from}'")

        self._log_info(f"Found a total of {len(all_tests)} lab tests.")
        
        # Save the fetched data to the cache file for future use
        try:
            self._log_info(f"Saving lab test list to cache file: {cache_file}")
            with open(cache_file, 'w') as f:
                json.dump(all_tests, f, indent=4)
            self._log_info("Successfully saved tests to cache.")
        except IOError as e:
            self._log_error(f"Error saving cache file {cache_file}: {e}")

        return all_tests

    def get_lab_test_info(self, test_ien: str):
        """
        Retrieves information about a specific lab test from VistA.
        RPC: ORWLRR INFO
        Args:
            test_ien (str): The IEN of the lab test.
        Returns:
            str: The raw reply from the RPC containing information about the lab test.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self._log_info(f"Getting lab test info for IEN: {test_ien}")
        if not self.login():
            raise ConnectionError("Not connected.")
        
        raw_reply = self.invoke_rpc("ORWLRR INFO", PLiteral(test_ien))
        self._log_info(f"Raw reply for lab test info (IEN: {test_ien}): {raw_reply}")
        return raw_reply

    def get_lab_test_details(self, lab_test_ien: str):
        """
        Calls the ORWDLR32 LOAD RPC to get all details for a specific lab test.
        This RPC provides comprehensive information about a lab test,
        including collection samples, urgencies, schedules, and more.
        RPC: ORWDLR32 LOAD
        Args:
            lab_test_ien (str): The IEN of the lab test.
        Returns:
            str: The raw reply from the RPC containing the lab test details.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self._log_info(f"Getting lab test details for IEN: {lab_test_ien}")
        if not self.login():
            raise ConnectionError("Not connected.")
        
        raw_reply = self.invoke_rpc("ORWDLR32 LOAD", PLiteral(lab_test_ien))
        self._log_info(f"Raw reply for lab test details (IEN: {lab_test_ien}): {raw_reply}")
        return raw_reply

    def update_additional_signers(self, note_ien, signer_duz_list):
        """
        Updates the list of additional signers for a TIU document.
        RPC: TIU UPDATE ADDITIONAL SIGNERS
        Args:
            note_ien (str): The IEN of the note to update.
            signer_duz_list (list): A list of DUZs (strings) of the additional signers.
        Returns:
            bool: True if the update was successful.
        Raises:
            ConnectionError: If not connected to VistA.
            Exception: If the RPC returns an error message.
        """
        self._log_info(f"Updating additional signers for note IEN: {note_ien} with DUZs: {signer_duz_list}")
        if not self.login():
            raise ConnectionError("Not connected.")
        
        # Convert the list of DUZs into PLiteral parameters for the RPC
        param_list = [PLiteral(str(duz)) for duz in signer_duz_list]
        
        result = self.invoke_rpc("TIU UPDATE ADDITIONAL SIGNERS", PLiteral(note_ien), *param_list)
        
        # Check the RPC result for any error indicators
        if result and "error" in result.lower():
            self._log_error(f"Failed to update additional signers for note {note_ien}: {result}")
            raise Exception(f"Failed to update additional signers for note {note_ien}: {result}")
        
        self._log_info(f"Successfully updated additional signers for note {note_ien}.")
        return True

    def get_providers(self):
        """
        Fetches a list of providers from VistA.
        RPC: ORQQPL PROVIDER LIST
        Returns:
            tuple: A tuple containing:
                - list: A list of provider names (strings).
                - dict: A dictionary mapping provider names to their IENs.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self._log_info("Fetching provider list...")
        if not self.login():
            raise ConnectionError("Not connected.")
        
        # Invoke the RPC to get the raw list of providers
        providers_raw = self.invoke_rpc("ORQQPL PROVIDER LIST", PLiteral(""), PLiteral("1"))
        
        providers_map = {}
        provider_names = []
        
        # Parse the raw reply, which is typically in IEN^Name format
        for line in providers_raw.splitlines():
            if line:
                parts = line.split('^')
                if len(parts) >= 2:
                    ien, name = parts[0], parts[1]
                    providers_map[name] = ien # Map name to IEN
                    provider_names.append(name) # Collect names
        
        self._log_info(f"Found {len(provider_names)} providers.")
        return provider_names, providers_map

    def get_alerts(self):
        """
        Fetches the current user's alerts from VistA.
        RPC: ORQQAL LIST
        Returns:
            str: The raw reply from the RPC containing the list of alerts.
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self._log_info("Fetching alert list...")
        if not self.login():
            raise ConnectionError("Not connected.")
        
        return self.invoke_rpc("ORQQAL LIST", "")

    def select_and_get_patient_data(self, dfn):
        """
        Selects a patient and fetches initial related data (patient info, recent notes, and note titles).
        This is a high-level facade method that combines several RPC calls to prepare the GUI
        for a selected patient.
        Args:
            dfn (str): The DFN of the patient to select.
        Returns:
            dict: A dictionary containing:
                - 'patient_info': Basic demographic information of the patient.
                - 'patient_notes': A list of recent notes for the patient.
                - 'note_titles': A list of available note titles.
        Raises:
            ConnectionError: If not connected to VistA.
            Exception: If patient selection or data retrieval fails.
        """
        self._log_info(f"Selecting patient and fetching all initial data for DFN: {dfn}")
        if not self.login():
            raise ConnectionError("Not connected.")

        # 1. Select patient and get basic info
        patient_info = self.select_patient(dfn)
        if not (patient_info and patient_info.get("Name")):
            raise Exception(f"Could not select or find name for patient with DFN: {dfn}")

        # 2. Fetch patient notes (using default values from the original GUI method)
        patient_notes = self.fetch_patient_notes(dfn, doc_class_ien=3, context=1, max_docs=100)

        # 3. Fetch available note titles
        note_titles = self.get_note_titles()

        # 4. Bundle all fetched data and return
        return {
            "patient_info": patient_info,
            "patient_notes": patient_notes,
            "note_titles": note_titles
        }

    def get_lab_order_defaults(self, location_ien: str, division_ien: str = "0") -> dict:
        """
        Calls the ORWDLR32 DEF RPC to get default values and lists for the lab order dialog.
        Parses the complex TStrings reply into a structured dictionary for easier access.
        RPC: ORWDLR32 DEF
        Args:
            location_ien (str): The IEN of the patient's current location.
            division_ien (str, optional): The IEN of the division (default "0").
        Returns:
            dict: A dictionary containing parsed default values and lists for lab ordering.
                  Keys are typically section names (e.g., "COLLECTION_TYPES", "URGENCIES").
        Raises:
            ConnectionError: If not connected to VistA.
        """
        self._log_info(f"Getting lab order defaults for location IEN: {location_ien}, division IEN: {division_ien}")
        if not self.login():
            raise ConnectionError("Not connected.")

        params = [
            PLiteral(location_ien),
            PLiteral(division_ien)
        ]

        raw_reply = self.invoke_rpc("ORWDLR32 DEF", *params)
        self._log_info(f"Raw reply for ORWDLR32 DEF: {raw_reply}")
        
        # --- Parsing Logic for ORWDLR32 DEF --- 
        # This RPC returns a complex TStrings format with sections for defaults and lists.
        # Example sections: ~COLLECTION TYPES, ~URGENCIES, ~SCHEDULES, ~DEFAULTS
        defaults = {}
        current_section = None
        
        lines = raw_reply.splitlines()
        for line in lines:
            line = line.strip()
            if not line: continue

            if line.startswith('~'):
                # New section found, e.g., "~COLLECTION TYPES"
                current_section = line[1:].upper().replace(' ', '_') # Normalize section name
                defaults[current_section] = [] # Initialize as a list for items
            elif current_section:
                # Add items to the current section
                # Each item is typically IEN^Name or Code^Name
                parts = line.split('^')
                if len(parts) >= 2:
                    defaults[current_section].append({"ien": parts[0], "name": parts[1]})
                else:
                    # If a line in a section does not follow IEN^Name, treat it as a single value
                    # This might overwrite a list if a section only has one value not formatted as IEN^Name
                    # This behavior might need refinement based on exact VistA RPC output specifics.
                    defaults[current_section] = line 
        
        self._log_info(f"Parsed ORWDLR32 DEF defaults: {defaults}")
        return defaults