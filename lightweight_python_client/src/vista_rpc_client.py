import re
from vavista.rpc import connect, PLiteral, PList, PReference, PEncoded, PWordProcess
print(f"DEBUG: Loading vista_rpc_client.py from: {__file__}")

class VistAClient:
    def __init__(self, rpc_info=None, logger=None, comm_logger=None):
        self.connection = None
        self.current_patient_dfn = None
        self.rpc_info = rpc_info
        self.logger = logger
        self.comm_logger = comm_logger # New communication logger

    def _log_info(self, message):
        if self.logger:
            self.logger.logInfo("VistAClient", message)

    def _log_error(self, message):
        if self.logger:
            self.logger.logError("VistAClient", message)

    def connect_to_vista(self, host, port, access, verify, context):
        if not all([host, port, access, verify, context]):
            raise ValueError("All connection fields must be filled.")
        
        self.connection = connect(host, int(port), access, verify, context, logger=self.logger)
        return "Connection successful!"

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None
            return "Disconnected from VistA."
        return "Not connected."

    def _parse_params(self, params_str):
        params = []
        if not params_str:
            return params

        # Split parameters by semicolon or newline, but not within quoted strings.
        # This regex handles cases like: literal:"value with;semicolon",literal:another
        # It splits by ; or \n only if they are not inside double quotes.
        parts = re.split(r';(?=(?:[^"]*"[^"]*")*[^"]*$)|\n', params_str)

        for part in parts:
            part = part.strip()
            if not part:
                continue
            try:
                # Determine parameter type based on prefix
                if part.lower().startswith("literal:"):
                    params.append(PLiteral(part[len("literal:"):]))
                elif part.lower().startswith("list:"):
                    # Format: list:key1=value1;key2=value2 or list:item1;item2
                    list_content = part[len("list:"):]
                    p_list = PList()
                    # Split list items by semicolon, respecting quotes
                    list_items = re.split(r';(?=(?:[^"]*"[^"]*")*[^"]*$)', list_content)
                    list_index = 1 # Start 1-based indexing for non-keyed list items
                    for item in list_items:
                        item = item.strip()
                        if '=' in item:
                            key, value = item.split('=', 1)
                            p_list[key.strip()] = value.strip()
                        else:
                            # Assign 1-based numeric key for non-keyed list items, matching Delphi's behavior
                            p_list[str(list_index)] = item
                            list_index += 1
                    params.append(p_list)
                elif part.lower().startswith("ref:"):
                    params.append(PReference(part[len("ref:"):]))
                elif part.lower().startswith("encoded:"):
                    params.append(PEncoded(part[len("encoded:"):]))
                elif part.lower().startswith("wordproc:"):
                    # Word processing parameters are typically multi-line text.
                    # The content after "wordproc:" is treated as the entire text.
                    # vavista.rpc.PWordProcess is the correct type for this.
                    # Assuming the content for wordproc is everything after the prefix until the next parameter.
                    # For simplicity, we'll take the rest of the 'part' as the word processing text.
                    # If multi-line, the input in the GUI should use actual newlines.
                    params.append(PWordProcess(part[len("wordproc:"):]))
                else:
                    # Default to literal if no prefix is given
                    params.append(PLiteral(part))
            except Exception as e:
                raise ValueError(f"Malformed parameter part: '{part}'. Error: {e}")
        return params

    def _parse_reply(self, rpc_name, raw_reply):
        parser_map = {
            "ORWU USERINFO": self._parse_user_info,
            "ORQPT PROVIDER PATIENTS": self._parse_patient_list,
            "ORWPT LIST ALL": self._parse_patient_list,
            "ORWPT SELECT": self._parse_patient_select,
            "TIU DOCUMENTS BY CONTEXT": self._parse_notes_list,
            "ORWORB FASTUSER": self._parse_generic_text_reply,
            "ORWORB TEXT FOLLOWUP": self._parse_generic_text_reply,
            "TIU GET RECORD TEXT": self._parse_generic_text_reply,
            "ORWU HOSPLOC": self._parse_location_list,
            "ORWU NEWPERS": self._parse_provider_list,
            "TIU DETAILED DISPLAY": self._parse_generic_text_reply,
            "TIU LONG LIST OF TITLES": self._parse_title_list,
            "TIU GET PERSONAL PREFERENCES": self._parse_tiu_preferences,
        }
        parser = parser_map.get(rpc_name)
        if parser:
            return parser(raw_reply)
        return raw_reply # Return raw reply if no specific parser is found

    def _parse_user_info(self, raw_reply):
        # Format: DUZ^Name^UserClass^CanSignOrders^IsProvider^OrderRole^NoOrdering^DTIME^CNTDN^VERORD^NOTIFYAPPS^MSGHANG^DOMAIN^SERVICE^AUTOSAVE^INITTAB^LASTTAB^WEBACCESS^ALLOWHOLD^ISRPL^RPLLIST^CORTABS^RPTTAB^STATION#^GECStatus^Production account?
        parts = raw_reply.split('^')
        user_info = {
            "DUZ": parts[0] if len(parts) > 0 else None,
            "Name": parts[1] if len(parts) > 1 else None,
            "UserClass": parts[2] if len(parts) > 2 else None,
            # ... add other fields as needed
        }
        return user_info

    def _parse_tiu_preferences(self, raw_reply):
        # Format: DfltLoc^DfltLocName^SortAscending^SortBy^AskNoteSubject^DfltCosigner^DfltCosignerName^MaxNotes^AskCosigner
        parts = raw_reply.split('^')
        prefs = {
            "DfltLoc": parts[0] if len(parts) > 0 else None,
            "DfltLocName": parts[1] if len(parts) > 1 else None,
            "SortAscending": parts[2] == '1' if len(parts) > 2 else False,
            "SortBy": parts[3] if len(parts) > 3 else None,
            "AskNoteSubject": parts[4] == '1' if len(parts) > 4 else False,
            "DfltCosigner": parts[5] if len(parts) > 5 else None,
            "DfltCosignerName": parts[6] if len(parts) > 6 else None,
            "MaxNotes": int(parts[7]) if len(parts) > 7 else 0,
            "AskCosigner": parts[8] == '1' if len(parts) > 8 else False,
        }
        return prefs

    def _parse_title_list(self, raw_reply):
        titles = []
        if raw_reply and raw_reply.strip():
            for line in raw_reply.split('\r\n'):
                if line.strip():
                    parts = line.split('^')
                    if len(parts) >= 2:
                        titles.append({"IEN": parts[0], "Title": parts[1]})
        return titles

    def fetch_note_details(self, note_ien):
        if not self.connection:
            raise ConnectionError("Not connected to VistA. Please connect first.")
        if not note_ien:
            raise ValueError("Note IEN is required to fetch note details.")
        params_str = f"literal:{note_ien}"
        return self.invoke_rpc("TIU DETAILED DISPLAY", params_str)

    def get_note_titles(self, doc_class_ien=3, start_from="", direction=1, id_notes_only=False):
        if not self.connection:
            raise ConnectionError("Not connected to VistA. Please connect first.")
        params_str = (
            f"literal:{doc_class_ien};"
            f"literal:{start_from};"
            f"literal:{direction};"
            f"literal:{'1' if id_notes_only else '0'}"
        )
        return self.invoke_rpc("TIU LONG LIST OF TITLES", params_str)

    def get_user_tiu_preferences(self):
        if not self.connection:
            raise ConnectionError("Not connected to VistA. Please connect first.")
        return self.invoke_rpc("TIU GET PERSONAL PREFERENCES", f"literal:{self.get_user_info()['DUZ']}")

    def save_user_tiu_preferences(self, preferences: dict):
        if not self.connection:
            raise ConnectionError("Not connected to VistA. Please connect first.")
        # The ORWTIU SAVE TIU CONTEXT RPC expects a semicolon-separated string of values.
        # The order of values is crucial and corresponds to the TTIUContext record in Delphi.
        # Changed: Boolean; BeginDate: string; EndDate: string; Status: string; Author: int64;
        # MaxDocs: integer; ShowSubject: Boolean; SortBy: string; ListAscending: Boolean;
        # TreeAscending: Boolean; GroupBy: string; SearchField: string; KeyWord: string; Filtered: Boolean;
        # We will construct this string from the provided dictionary.
        # Note: Some fields like 'Changed' and 'Filtered' are derived or managed internally by Delphi.
        # We'll focus on the fields that are typically user-configurable and sent to the RPC.
        
        # Default values for fields not explicitly provided or not directly user-configurable via this RPC
        begin_date = preferences.get("BeginDate", "")
        end_date = preferences.get("EndDate", "")
        status = preferences.get("Status", "1") # Default to '1' for all signed notes
        author = preferences.get("Author", "0") # Default to '0' for all authors
        max_docs = preferences.get("MaxDocs", "0") # Default to '0' for no limit
        show_subject = '1' if preferences.get("ShowSubject", False) else '0'
        sort_by = preferences.get("SortBy", "")
        list_ascending = '1' if preferences.get("ListAscending", False) else '0'
        tree_ascending = '1' if preferences.get("TreeAscending", False) else '0'
        group_by = preferences.get("GroupBy", "")
        search_field = preferences.get("SearchField", "")
        keyword = preferences.get("KeyWord", "")

        params_str = (
            f"literal:{begin_date};"
            f"literal:{end_date};"
            f"literal:{status};"
            f"literal:{author};"
            f"literal:{max_docs};"
            f"literal:{show_subject};"
            f"literal:{sort_by};"
            f"literal:{list_ascending};"
            f"literal:{tree_ascending};"
            f"literal:{group_by};"
            f"literal:{search_field};"
            f"literal:{keyword}"
        )
        return self.invoke_rpc("ORWTIU SAVE TIU CONTEXT", params_str)

    def _parse_patient_list(self, raw_reply):
        # Format: DFN^PatientName^...
        patients = []
        if raw_reply and raw_reply.strip():
            for line in raw_reply.split('\r\n'):
                if line.strip():
                    parts = line.split('^')
                    if len(parts) >= 2:
                        patients.append({"DFN": parts[0], "Name": parts[1]})
        return patients

    def _parse_patient_select(self, raw_reply):
        # Format: NAME^SEX^DOB^SSN^LOCIEN^LOCNAME^ROOMBED^CWAD^SENSITIVE^ADMITTIME^CONVERTED^SVCONN^SC%^ICN^Age^TreatSpec^HRN^AltHRN
        parts = raw_reply.split('^')
        patient_info = {
            "Name": parts[0] if len(parts) > 0 else None,
            "DFN": self.current_patient_dfn, # DFN is passed in, not returned by this RPC
            "SSN": parts[3] if len(parts) > 3 else None,
            "DOB": parts[2] if len(parts) > 2 else None,
            "Sex": parts[1] if len(parts) > 1 else None,
            # ... add other fields as needed
        }
        return patient_info

    def _parse_notes_list(self, raw_reply):
        # Format: IEN^Title^FMDateOfNote^Patient^Author^Location^Status^Visit
        notes = []
        if raw_reply and raw_reply.strip():
            for line in raw_reply.split('\r\n'):
                if line.strip():
                    parts = line.split('^')
                    if len(parts) >= 3:
                        notes.append({
                            "IEN": parts[0],
                            "Title": parts[1],
                            "Date": parts[2],
                            "PatientDFN": parts[3] if len(parts) > 3 else None,
                            "Author": parts[4] if len(parts) > 4 else None,
                            # ... add other fields as needed
                        })
        return notes

    def _parse_generic_text_reply(self, raw_reply):
        # For RPCs that return plain text or simple lists of strings
        return raw_reply.split('\r\n') if raw_reply else []

    def _parse_location_list(self, raw_reply):
        locations = {}
        if raw_reply and raw_reply.strip():
            for line in raw_reply.split('\r\n'):
                if line.strip():
                    parts = line.split('^')
                    if len(parts) >= 2:
                        locations[parts[1]] = parts[0] # Name: IEN
        return locations

    def _parse_provider_list(self, raw_reply):
        providers = []
        if raw_reply and raw_reply.strip():
            for line in raw_reply.split('\r\n'):
                if line.strip():
                    parts = line.split('^')
                    if len(parts) >= 2:
                        providers.append({"IEN": parts[0], "Name": parts[1]})
        return providers

    def invoke_rpc(self, rpc_name, params_str):
        if not self.connection:
            raise ConnectionError("Not connected to VistA. Please connect first.")

        if not rpc_name:
            raise ValueError("Please select an RPC.")

        if rpc_name == "TIU GET RECORD TEXT" and not params_str:
            raise ValueError("The selected RPC, TIU GET RECORD TEXT, requires a note IEN. Please provide one in the parameters field.")

        params = self._parse_params(params_str)
        self._log_info(f"Invoking RPC: {rpc_name}")
        self._log_info(f"Parameters: {params_str}")
        
        # Log the raw RPC request string if comm_logger is available
        if self.comm_logger and hasattr(self.connection, 'last_request_string'):
            self.comm_logger(f"RPC Request: {self.connection.last_request_string}")

        raw_reply = self.connection.invoke(rpc_name, *params)
        self._log_info(f"Raw Reply: {raw_reply}")

        # Log the raw RPC reply string if comm_logger is available
        if self.comm_logger:
            self.comm_logger(f"RPC Reply: {raw_reply}")

        return self._parse_reply(rpc_name, raw_reply)

    def _get_rpc_details(self, rpc_name):
        if not self.rpc_info:
            raise ValueError("RPC information not loaded.")
        for category, rpcs_in_category in self.rpc_info.items():
            if rpc_name in rpcs_in_category:
                return rpcs_in_category[rpc_name]
        raise ValueError(f"RPC '{rpc_name}' not found in RPC information.")

    def get_user_info(self):
        if not self.connection:
            raise ConnectionError("Not connected to VistA.")
        # ORWU USERINFO has no parameters, so params_str will be empty
        return self.invoke_rpc("ORWU USERINFO", "")

    def get_doctor_patients(self, provider_ien):
        if not self.connection:
            raise ConnectionError("Not connected to VistA.")
        # ORQPT PROVIDER PATIENTS expects a literal parameter for provider IEN
        params_str = f"literal:{provider_ien}"
        return self.invoke_rpc("ORQPT PROVIDER PATIENTS", params_str)

    def select_patient(self, dfn):
        if not self.connection:
            raise ConnectionError("Not connected to VistA.")
        # ORWPT SELECT expects a literal parameter for DFN
        params_str = f"literal:{dfn}"
        reply = self.invoke_rpc("ORWPT SELECT", params_str)
        self.current_patient_dfn = dfn # Store the selected DFN
        return reply

    def search_patient(self, search_term):
        if not self.connection:
            raise ConnectionError("Not connected to VistA.")
        if not search_term:
            raise ValueError("Please enter a patient name to search.")
        # ORWPT LIST ALL expects two literal parameters: search_term and a flag (usually "1")
        params_str = f"literal:{search_term};literal:1"
        return self.invoke_rpc("ORWPT LIST ALL", params_str)

    def fetch_patient_notes(self, dfn, doc_class_ien=3, context=1, start_date="", end_date="", author_ien=0, max_docs=100, sort_order="D", show_addenda=False):
        if not self.connection:
            raise ConnectionError("Not connected to VistA. Please connect first.")
        # TIU DOCUMENTS BY CONTEXT parameters: DocClassIEN, Context, PatientDFN, EarlyDate, LateDate, Person, OccLim, SortSeq, SHOW_ADDENDA
        params_str = (
            f"literal:{doc_class_ien};"
            f"literal:{context};"
            f"literal:{dfn};"
            f"literal:{start_date};"
            f"literal:{end_date};"
            f"literal:{author_ien};"
            f"literal:{max_docs};"
            f"literal:{sort_order};"
            f"literal:{'1' if show_addenda else '0'}"
        )
        return self.invoke_rpc("TIU DOCUMENTS BY CONTEXT", params_str)

    def get_recent_notes_for_patients(self, dfn_list, note_count=5):
        if not self.connection:
            raise ConnectionError("Not connected to VistA.")

        all_notes = []
        for dfn in dfn_list:
            try:
                # Select patient to set context
                patient_info = self.select_patient(dfn)
                patient_name = patient_info.get("Name", "Unknown")

                # Fetch notes for the selected patient
                notes = self.fetch_patient_notes(dfn, max_docs=note_count)
                if notes:
                    for note in notes:
                        # Append patient info to each note
                        note['PatientName'] = patient_name
                        note['PatientDFN'] = dfn
                        all_notes.append(note)
            except Exception as e:
                print(f"Could not fetch notes for DFN {dfn}: {e}")
                # Optionally, log this error or handle it as needed
                continue
        
        return all_notes

    def get_user_alerts(self, dfn):
        if not self.connection:
            raise ConnectionError("Not connected to VistA.")
        # ORWORB FASTUSER expects a literal parameter for DFN
        params_str = f"literal:{dfn}"
        return self.invoke_rpc("ORWORB FASTUSER", params_str)

    def get_alert_text(self, patient_dfn, notification, xqaid):
        if not self.connection:
            raise ConnectionError("Not connected to VistA.")
        # ORWORB TEXT FOLLOWUP expects literal parameters
        params_str = f"literal:{patient_dfn};literal:{notification};literal:{xqaid}"
        return self.invoke_rpc("ORWORB TEXT FOLLOWUP", params_str)
