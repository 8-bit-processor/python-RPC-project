import sys
import os
import re
from vavista.rpc import connect, PLiteral, PList, PReference, PEncoded, PWordProcess

class VistAClient:
    def __init__(self):
        self.connection = None

    def connect_to_vista(self, host, port, access, verify, context):
        if not all([host, port, access, verify, context]):
            raise ValueError("All connection fields must be filled.")
        
        self.connection = connect(host, int(port), access, verify, context)
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

            # Determine parameter type based on prefix
            if part.lower().startswith("literal:"):
                params.append(PLiteral(part[len("literal:"):]))
            elif part.lower().startswith("list:"):
                # Format: list:key1=value1;key2=value2 or list:item1;item2
                list_content = part[len("list:"):]
                p_list = PList()
                # Split list items by semicolon, respecting quotes
                list_items = re.split(r';(?=(?:[^"]*"[^"]*")*[^"]*$)', list_content)
                for item in list_items:
                    item = item.strip()
                    if '=' in item:
                        key, value = item.split('=', 1)
                        p_list[key.strip()] = value.strip()
                    else:
                        # For non-keyed list items, vavista.rpc.PList.append() is not available.
                        # We'll treat them as keyed with an empty string or sequential numbers if needed by RPC.
                        # For now, assuming all list items are key-value pairs or simple values that can be assigned to a key.
                        # If the RPC expects a simple list, it might be better to pass it as a multi-line literal.
                        # For now, we'll just add it as a value with no key, which might not work for all RPCs.
                        # A better approach for non-keyed lists might be to pass them as a single literal with newlines.
                        # However, the Delphi code uses Mult[IntToStr(i+1)] := Strings[i], implying keyed list.
                        # So, we'll assume key-value pairs or single values that become keys with empty values.
                        p_list[item] = "" # Assign empty string as value if no '='
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
        return params

    def invoke_rpc(self, rpc_name, params_str):
        if not self.connection:
            raise ConnectionError("Not connected to VistA. Please connect first.")

        if not rpc_name:
            raise ValueError("Please select an RPC.")

        if rpc_name == "TIU GET RECORD TEXT" and not params_str:
            raise ValueError("The selected RPC, TIU GET RECORD TEXT, requires a note IEN. Please provide one in the parameters field.")

        params = self._parse_params(params_str)
        reply = self.connection.invoke(rpc_name, *params)
        return reply

    def get_user_info(self):
        if not self.connection:
            raise ConnectionError("Not connected to VistA.")
        return self.connection.invoke("ORWU USERINFO")

    def get_doctor_patients(self, provider_ien):
        if not self.connection:
            raise ConnectionError("Not connected to VistA.")
        return self.connection.invoke("ORQPT PROVIDER PATIENTS", PLiteral(provider_ien))

    def select_patient(self, dfn):
        if not self.connection:
            raise ConnectionError("Not connected to VistA.")
        return self.connection.invoke("ORWPT SELECT", PLiteral(dfn))

    def search_patient(self, search_term):
        if not self.connection:
            raise ConnectionError("Not connected to VistA.")
        if not search_term:
            raise ValueError("Please enter a patient name to search.")
        return self.connection.invoke("ORWPT LIST ALL", PLiteral(search_term), PLiteral("1"))

    def fetch_patient_notes(self, dfn):
        if not self.connection:
            raise ConnectionError("Not connected to VistA.")
        # Context Status (NC_CUSTOM) - literal:3
        # Patient.DFN - literal:dfn
        # FMBeginDate (empty for all dates) - literal:
        # FMEndDate (empty for all dates) - literal:
        # Author (empty) - literal:
        # MaxDocs (empty for no limit) - literal:
        # SortBy (empty) - literal:
        # ListAscending (empty) - literal:
        # GroupBy (empty) - literal:
        # SearchField (empty) - literal:
        # Keyword (empty) - literal:
        # Filtered (empty) - literal:
        # SearchString (empty) - literal:
        return self.connection.invoke("TIU DOCUMENTS BY CONTEXT", 
                                        PLiteral("3"),  # Context Status (NC_CUSTOM)
                                        PLiteral(dfn),  # Patient.DFN
                                        PLiteral(""),   # FMBeginDate (empty for all dates)
                                        PLiteral(""),   # FMEndDate (empty for all dates)
                                        PLiteral(""),   # Author (empty)
                                        PLiteral(""),   # MaxDocs (empty for no limit)
                                        PLiteral(""),   # SortBy (empty)
                                        PLiteral(""),   # ListAscending (empty)
                                        PLiteral(""),   # GroupBy (empty)
                                        PLiteral(""),   # SearchField (empty)
                                        PLiteral(""),   # Keyword (empty)
                                        PLiteral(""))   # SearchString (empty)
