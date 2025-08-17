# VistA RPC Client

This project provides a Python client for interacting with a VistA EMR system via remote procedure calls (RPCs).
You must have permission to obtain the cipher (encryption) for the vista you are using for this to work.
After obtaining this encryption key belongs in the broker_rpc.py file

## Summary of the project structure:
    1 .
    2 ├── .gitignore
    3 ├── LICENSE
    4 ├── README.md
    5 ├── requirements.txt
    6 ├── src   
    7 │   ├── broker_rpc.py  (handles low-level VistA RPC communication). 
    8 │   ├── cprs_rpc_documentation.md
    9 │   ├── cprs_rpc_list.txt
   10 │   ├── rpc_config_loader.py  (loads RPC configurations)
   11 │   └── vista_rpc_client.py  (handles the high-level VistA client)
   12 ├── vavista
   13 │   ├── __init__.py  (defines the vavista package)
   14 │   └── rpc.py  (vavista/rpc.py acts as an intermediary, using broker_rpc for communication)
   15 └── vista_rpc_gui.py  <----- (vista_rpc_gui.py provides the GUI Launch from here)

## Usage

```python
from src.vista_rpc_client import VistAClient

# Replace with your VistA instance details
HOST = "your_host"
PORT = your_port
ACCESS_CODE = "your_access_code"
VERIFY_CODE = "your_verify_code"
CONTEXT = "your_context"

# Create a VistAClient instance
client = VistAClient()

# Connect to VistA
try:
    connection_message = client.connect_to_vista(HOST, PORT, ACCESS_CODE, VERIFY_CODE, CONTEXT)
    print(connection_message)

    # Get user info
    user_info = client.get_user_info()
    print(user_info)

except (ValueError, ConnectionError) as e:
    print(e)

finally:
    # Disconnect from VistA
    disconnection_message = client.disconnect()
    print(disconnection_message)


  Each Python code file's function:

   * `src/broker_rpc.py`:
       * Purpose: This file provides the low-level communication layer for interacting with VistA RPCs. It
         handles the network connection (sockets), authentication (access and verify codes), and the specific
         RPC message formatting required by VistA's Broker. It supports both the "new style" VA Broker and
         IHS's CIA Broker.
       * Key Classes/Functions:
           * RPCConnection: A base class for handling the core connection logic, including encryption and
             reading responses up to a defined end-marker.
           * VistARPCConnection: Inherits from RPCConnection and specializes in the VistA Broker's handshake
             and request formatting.
           * CIARPCConnection: Inherits from RPCConnection and specializes in the CIA Broker's handshake and
             request formatting.
           * RPCConnectionPool: Manages a pool of RPCConnection objects for thread-safe access to VistA,
             useful in multi-threaded environments.


   * `src/vista_rpc_client.py`:
       * Purpose: This file defines a high-level client (VistAClient) that simplifies making RPC calls to a
         VistA system. It abstracts away the complexities of parameter formatting and direct RPC invocation,
         providing more user-friendly methods for common VistA operations (e.g., getting patient information,
         fetching notes).
       * Key Classes/Functions:
           * VistAClient: The main class that encapsulates the connection and provides methods like
             connect_to_vista, disconnect, invoke_rpc, get_user_info, select_patient, fetch_patient_notes,
             etc.
           * _parse_params: A crucial internal method that takes a string of parameters (as might be entered
             in a GUI) and converts them into the appropriate vavista.rpc parameter objects (PLiteral, PList,
             etc.).


   * `src/rpc_config_loader.py`:
       * Purpose: This file is responsible for loading and parsing RPC configuration data from external files.
          It reads a list of RPC names and their associated documentation (description, parameters, returns)
         from Markdown and text files. This data is then used to populate the RPC browser in the GUI.
       * Key Classes/Functions:
           * RPCConfigLoader: The class that handles reading the RPC list and documentation files, parsing
             their content, and filtering RPCs based on importance.


   * `vavista/__init__.py`:
       * Purpose: This is a standard Python package initialization file. In this project, it primarily serves
         to make the vavista directory a Python package. It also imports key components from vavista/rpc.py
         (like connect, PLiteral, PList, etc.) so they can be directly imported from vavista (e.g., from
         vavista.rpc import connect becomes from vavista import connect).


   * `vavista/rpc.py`:
       * Purpose: This file acts as an intermediary layer between the high-level VistAClient and the low-level
          broker_rpc.py. It defines classes that represent different types of RPC parameters (PLiteral, PList,
          PReference, PEncoded, PWordProcess) and provides a connect function that sets up the VistA
         connection using broker_rpc.py. It also includes a Connection class that wraps the VistARPCConnection
          and handles the invocation of RPCs with the correctly formatted parameters.
       * Key Classes/Functions:
           * PLiteral, PList, PReference, PEncoded, PWordProcess: Classes to represent different RPC parameter
              types.
           * Connection: A wrapper class that provides the invoke method, translating the Pythonic parameter
             objects into the format expected by broker_rpc.py.
           * connect: A factory function to establish a VistA connection.


   * `vista_rpc_gui.py`:
       * Purpose: This file implements the graphical user interface (GUI) for the VistA RPC client using the
         tkinter library. It provides a user-friendly way to connect to a VistA instance, browse available
         RPCs, input parameters, invoke RPCs, and view the responses. It integrates all the other Python
         modules to provide a complete client application.
       * Key Classes/Functions:
           * VistARPCGUI: The main Tkinter application class that sets up the window, connection controls, RPC
              invocation area, patient selection, and results display.
           * RPCBrowser: A tk.Toplevel window that allows users to browse RPCs and their documentation.
           * PatientSelectionWindow: A tk.Toplevel window for selecting patients from search results.
           * Various _on_* and _load_* methods: Event handlers and utility functions for GUI interactions and
             data loading.