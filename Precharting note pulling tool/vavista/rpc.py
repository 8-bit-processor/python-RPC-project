from broker_rpc import VistARPCConnection

class RPCLogger:
    def __init__(self):
        pass

    def logInfo(self, tag, msg):
        self.__log(tag, msg)

    def logError(self, tag, msg):
        self.__log(tag, msg)

    def __log(self, tag, msg):
        print(f"BROKERRPC -- {tag} {msg}")

class PLiteral:
    def __init__(self, value):
        self.value = str(value)

class PList:
    def __init__(self, value):
        # PList can be a list of tuples or a dictionary
        if isinstance(value, list):
            self.value = {str(k): str(v) for k, v in value}
        elif isinstance(value, dict):
            self.value = {str(k): str(v) for k, v in value.items()}
        else:
            raise ValueError("PList must be initialized with a list of tuples or a dictionary.")

class PReference:
    def __init__(self, value):
        self.value = str(value)

class PEncoded:
    def __init__(self, value):
        self.value = str(value)

class PWordProcess:
    def __init__(self, value):
        self.value = str(value)

class Connection:
    def __init__(self, conn):
        self._conn = conn

    def invoke(self, rpcid, *params):
        processed_params = []
        for param in params:
            if isinstance(param, PLiteral) or isinstance(param, PReference) or isinstance(param, PEncoded) or isinstance(param, PWordProcess):
                processed_params.append(param.value)
            elif isinstance(param, PList):
                processed_params.append(param.value)
            else: # Default to PLiteral if no specific type is given
                processed_params.append(str(param))
        return self._conn.invokeRPC(rpcid, processed_params)

    def l_invoke(self, rpcid, *params):
        # This is a simplified l_invoke. In a real scenario, you'd need to parse
        # the string response from VistA into a Python list based on delimiters.
        # For now, it will just call invoke and split by \r\n as suggested in the doc.
        response = self.invoke(rpcid, *params)
        return response.split('\r\n')

def connect(hostname, port, access_code, verify_code, context, debug=False, logger=None):
    if not logger:
        logger = RPCLogger()
    # The brokerRPC3.py script expects the context to be passed directly.
    # The hardcoded context in brokerRPC3.py's main_test() is "OR CPRS GUI CHART"
    # We will use the provided context here.
    conn = VistARPCConnection(hostname, int(port), access_code, verify_code, context, logger)
    return Connection(conn)
