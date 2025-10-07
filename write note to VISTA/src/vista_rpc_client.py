import re
import datetime
from vavista.rpc import connect, PLiteral, PList, PWordProcess
from rpc_config_loader import RPCConfigLoader

class VistaRpcClient:
    def __init__(self, logger=None, comm_logger=None):
        self.connection = None
        self.host = None
        self.port = None
        self.access_code = None
        self.verify_code = None
        self.context = None
        self.logger = logger
        self.comm_logger = comm_logger

    def _get_fileman_timestamp(self):
        return (datetime.datetime.now() - datetime.timedelta(hours=5)).strftime("%Y%m%d.%H%M%S")

    def _log_info(self, message):
        if self.logger:
            self.logger.logInfo("VistaRpcClient", message)
        else:
            print(f"[INFO] VistaRpcClient: {message}")

    def _log_error(self, message):
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
        self.host = host
        self.port = port
        self.access_code = access
        self.verify_code = verify
        self.context = context
        return self.login()

    def login(self):
        if not self.connection:
            if not all([self.host, self.port, self.access_code, self.verify_code, self.context]):
                self._log_error("Connection details are not set.")
                return False
            try:
                self._log_info(f"Connecting to {self.host}:{self.port}...")
                self.connection = connect(
                    self.host, int(self.port), self.access_code, self.verify_code, self.context, logger=self.logger
                )
                self._log_info("Connection successful.")
                return True
            except Exception as e:
                self._log_error(f"Connection failed: {e}")
                self.connection = None
                raise e
        return True

    def invoke_rpc(self, rpc_name, *params):
        if not self.login():
            raise ConnectionError("Not connected.")
        
        processed_params = []
        if len(params) == 1 and isinstance(params[0], str):
            processed_params = self._parse_params_str(params[0])
        else:
            processed_params = list(params)

        if self.comm_logger:
            log_msg = f"--- RPC Request ---\nName: {rpc_name}\nParameters:\n"
            for i, p in enumerate(processed_params):
                if isinstance(p, PList) or isinstance(p, PWordProcess):
                    log_msg += f"  [{i}]: {p.__class__.__name__} = {p.value}\n"
                else:
                    log_msg += f"  [{i}]: PLiteral = \"{p.value}\"\n"
            self.comm_logger(log_msg)

        raw_reply = self.connection.invoke(rpc_name, *processed_params)

        if self.comm_logger:
            self.comm_logger(f"--- Raw Reply ---\n{raw_reply}\n-------------------\n")

        return raw_reply

    def _parse_params_str(self, params_str):
        params = []
        if not params_str:
            return params
        parts = params_str.split(';')
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if part.lower().startswith("literal:"):
                params.append(PLiteral(part[len("literal:"):]))
            else:
                params.append(PLiteral(part))
        return params

    def get_user_info(self):
        raw_reply = self.invoke_rpc("ORWU USERINFO")
        parts = raw_reply.split('^')
        return {
            "DUZ": parts[0] if len(parts) > 0 else None,
            "Name": parts[1] if len(parts) > 1 else None,
            "UserClass": parts[2] if len(parts) > 2 else None
        }

    def get_note_titles(self, doc_class_ien=3, start_from="", direction=1):
        raw_list = self.invoke_rpc("TIU LONG LIST OF TITLES", PLiteral(doc_class_ien), PLiteral(start_from), PLiteral(direction)).splitlines()
        titles = []
        for item in raw_list:
            if item:
                parts = item.split('^')
                if len(parts) >= 2:
                    titles.append({"IEN": parts[0], "Title": parts[1]})
        return titles

    def search_patient(self, search_term):
        raw_list = self.invoke_rpc("ORWPT LIST ALL", PLiteral(search_term), PLiteral("1")).splitlines()
        patients = []
        for item in raw_list:
            if item:
                parts = item.split('^')
                if len(parts) >= 2:
                    patients.append({"DFN": parts[0], "Name": parts[1]})
        return patients

    def get_doctor_patients(self, provider_ien):
        raw_list = self.invoke_rpc("ORQPT PROVIDER PATIENTS", PLiteral(provider_ien)).splitlines()
        patients = []
        for item in raw_list:
            if item:
                parts = item.split('^')
                if len(parts) >= 2:
                    patients.append({"DFN": parts[0], "Name": parts[1]})
        return patients

    def select_patient(self, dfn):
        raw_reply = self.invoke_rpc("ORWPT SELECT", PLiteral(dfn))
        parts = raw_reply.split('^')
        return {
            "Name": parts[0] if len(parts) > 0 else None,
            "Sex": parts[1] if len(parts) > 1 else None,
            "DOB": parts[2] if len(parts) > 2 else None
        }

    def fetch_patient_notes(self, dfn, doc_class_ien=3, context=1, max_docs=100):
        raw_list = self.invoke_rpc(
            "TIU DOCUMENTS BY CONTEXT",
            PLiteral(doc_class_ien), PLiteral(context), PLiteral(dfn),
            PLiteral(""), PLiteral(""), PLiteral("0"),
            PLiteral(max_docs), PLiteral("D"), PLiteral("0")
        ).splitlines()
        notes = []
        for item in raw_list:
            if item:
                parts = item.split('^')
                if len(parts) >= 3:
                    notes.append({"IEN": parts[0], "Title": parts[1], "Date": parts[2]})
        return notes

    def fetch_patient_encounters(self, dfn):
        raw_list = self.invoke_rpc("ORWPCE GET VISITS", PLiteral(dfn), PLiteral(""), PLiteral("")).splitlines()
        encounters = []
        for item in raw_list:
            if item:
                parts = item.split('^')
                if len(parts) >= 2:
                    encounters.append({"VisitStr": parts[0], "Location": parts[1], "DateTime": parts[1]})
        return encounters

    def get_patient_dfn(self, patient_name):
        patients = self.search_patient(patient_name)
        if patients and len(patients) > 0:
            return patients[0]["DFN"]
        return None

    def get_unsigned_notes(self, patient_dfn):
        return self.fetch_patient_notes(patient_dfn, context=3)

    def _set_document_text(self, note_ien, note_text_lines, suppress_commit=1):
        DOCUMENT_PAGE_SIZE = 300
        error_message = ""

        num_lines = len(note_text_lines)
        pages = (num_lines // DOCUMENT_PAGE_SIZE) + (1 if num_lines % DOCUMENT_PAGE_SIZE > 0 else 0)
        
        if num_lines == 0:
            # If no text, still need to call TIU SET DOCUMENT TEXT to clear any existing text
            # or to finalize the note creation if it expects a text update.
            # Send an empty text page.
            multiples = {'"HDR"': f"1^{pages}"}
            result = self.invoke_rpc(
                "TIU SET DOCUMENT TEXT",
                PLiteral(note_ien),
                PList(multiples),
                PLiteral(str(suppress_commit))
            )
            if result and result.startswith('0^'): # Success for TIU SET DOCUMENT TEXT
                error_message = ""
            else:
                error_message = result if result else "Unknown error during empty text set."
            return error_message

        for page_num in range(1, pages + 1):
            start_index = (page_num - 1) * DOCUMENT_PAGE_SIZE
            end_index = min(start_index + DOCUMENT_PAGE_SIZE, num_lines)
            current_page_lines = note_text_lines[start_index:end_index]

            multiples = {}
            for i, line in enumerate(current_page_lines):
                # VistA expects 1-based indexing for text lines
                # Apply filtering to each line
                filtered_line = self._filter_string(line)
                # VistA expects 1-based indexing for text lines
                multiples[f'"TEXT",{i + 1},0'] = filtered_line

            multiples['"HDR"'] = f"{page_num}^{pages}"

            result = self.invoke_rpc(
                "TIU SET DOCUMENT TEXT",
                PLiteral(note_ien),
                PList(multiples),
                PLiteral(str(suppress_commit))
            )

            # Check for error in the result.
            # Delphi code extracts error from 4th piece: Piece(RPCBrokerV.Results[0], U, 4)
            if result:
                parts = result.split('^')
                if len(parts) >= 4 and parts[3]: # If 4th piece exists and is not empty
                    error_message = parts[3]
                elif len(parts) >= 2 and parts[1] == '1': # If 2nd piece is '1', it might be a success flag
                    error_message = "" # No error
                else:
                    error_message = result # Fallback to full result if no specific error message
            else:
                error_message = "Unknown error during text set."

            if error_message:
                self._log_error(f"Error setting document text for note {note_ien}, page {page_num}: {error_message}")
                return error_message # Stop on first error

        return error_message

    def read_note_content(self, note_ien):
        """Retrieves the full text content of a specific TIU document."""
        if not self.login():
            raise ConnectionError("Not connected.")
        
        raw_reply = self.invoke_rpc("TIU GET RECORD TEXT", PLiteral(note_ien))
        return raw_reply

    def create_note(self, patient_dfn, title_ien, note_text, encounter_location_ien, encounter_datetime, visit_str, es_code=None, sign_note=True):
        """Creates, populates, and optionally signs a new note following the full RPC sequence."""
        # Step 1: Create the note record
        user_info = self.get_user_info()
        author_ien = user_info.get("DUZ")
        multiples = {
            "1202": author_ien,
            "1301": encounter_datetime,
            "1205": encounter_location_ien,
            "1701": "" # Subject
        }
        note_ien_result = self.invoke_rpc(
            "TIU CREATE RECORD",
            PLiteral(patient_dfn),
            PLiteral(title_ien),
            PLiteral(""), # VisitDateTime - rely on PList and VisitStr
            PLiteral(""), # LocationIEN - rely on PList and VisitStr
            PLiteral(""),
            PList(multiples),
            PLiteral(visit_str),
            PLiteral("1")
        )

        if not note_ien_result or not note_ien_result.isdigit():
            raise Exception(f"Failed to create note record. Server returned: {note_ien_result}")
        note_ien = note_ien_result
        self._log_info(f"Successfully created note record. IEN: {note_ien}")

        # Step 2: Lock the record (Crucial for proper editing state)
        lock_result = self.invoke_rpc("TIU LOCK RECORD", PLiteral(note_ien))
        if not lock_result.startswith('0'): # Expect '0' for success
            self._log_error(f"Failed to lock note {note_ien}: {lock_result}")
            # Decide whether to raise an exception or continue. For now, we'll continue.

        # Step 3: Update the record (often used for subject or other metadata)
        # The subject is passed in the initial CREATE RECORD call, but can be updated here if needed.
        # For now, we'll ensure the subject is set if provided in note_text.
        subject_line = ""
        if note_text:
            first_line = note_text.splitlines()[0]
            # Apply filtering to the subject line
            filtered_subject = self._filter_string(first_line)
            if len(filtered_subject) > 80:
                subject_line = filtered_subject[:80]
            else:
                subject_line = filtered_subject
        
        if subject_line:
            update_params = {"1701": subject_line}
            self.invoke_rpc("TIU UPDATE RECORD", PLiteral(note_ien), PList(update_params))
            self._log_info(f"Successfully updated note record with subject: {subject_line}")
        else:
            self._log_info(f"No subject to update for note {note_ien}.")


        # Step 4: Link to PCE (Patient Care Encounter) - This RPC is ORWPCE PCE4NOTE, not ORWPCE PCE4NOTE
        # The Delphi code calls PCEForNote(AnIEN, uPCEEdit) which likely wraps this.
        # For now, we'll assume this RPC is correct as is, but it might need further investigation if issues arise.
        # self.invoke_rpc("ORWPCE PCE4NOTE", PLiteral(note_ien))
        # self._log_info(f"Successfully linked note to PCE.")

        # Step 5: Authorize the note (Important for status and visibility)
        auth_result = self.invoke_rpc("TIU AUTHORIZATION", PLiteral(note_ien), PLiteral("EDIT RECORD")) # ActionName is "EDIT RECORD" for authorization
        if not auth_result.startswith('1'):
            self._log_error(f"Failed to authorize note {note_ien}: {auth_result}")
            # Again, decide whether to raise or continue.

        # Step 6: Set the document text using the new paginated function
        text_lines = note_text.splitlines()
        error_message = self._set_document_text(note_ien, text_lines, suppress_commit=1)
        if error_message:
            raise Exception(f"Failed to set document text for note {note_ien}: {error_message}")
        self._log_info("Successfully saved note text using paginated method.")

        # Step 7: Unlock the record (Crucial for visibility)
        unlock_result = self.invoke_rpc("TIU UNLOCK RECORD", PLiteral(note_ien))
        if not unlock_result.startswith('1'):
            self._log_error(f"Failed to unlock note {note_ien}: {unlock_result}")
            # This is critical for the note to appear in lists.

        # Step 8: Sign the note if requested
        if sign_note:
            if not es_code:
                raise ValueError("Electronic signature is required to sign the note.")
            sign_result = self.invoke_rpc("TIU SIGN RECORD", PLiteral(note_ien), PLiteral(es_code))
            if not sign_result.startswith('0^'): # TIU SIGN RECORD returns 0^ for success
                raise Exception(f"Failed to sign note. Server returned: {sign_result}")
            return f"Note {note_ien} created and signed successfully."
        
        return f"Note {note_ien} created successfully (unsigned)."