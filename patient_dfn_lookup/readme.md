  Python VistA RPC Client

  This project is a Python-based client designed to interact with a VistA electronic health record (EHR) system. The primary goal is to abstract the complexity of VistA's native communication protocol into a simplified, modern, and developer-friendly Python API.
  From this example Demo we are looking up DFN by name and date of birth, building out possiblilities can be anything from a small isolated funcionality to a complete remake of CPRS. 
 
  ---

  The Core Problem and Solution

  VistA's  primary method for programmatic interaction is through Remote Procedure
  Calls (RPCs), which operate over a low-level TCP socket connection. This communication involves a stateful protocol with complex data formatting and sequencing rules.

  For developers, this presents a significant barrier.Building applications that interface with VistA requires deep, specialized knowledge of this protocol, rpc sequencing and formatting for complex workflow or functionality making development slow, error-prone, and difficult to maintain.

  The Solution:

  This project solves the problem by creating a Python application that has a "broker" just like CPRS's broker.  The broker forms the communication bridge between a modern Python application and the VistA server just like the broker included in the CPRS client. The broker and vista rpc client encapsulate the low-level complexities of RPC communication and expose VistA's functionality through a clean, higher-level abstraction.

  This allows developers to build out and perform complex EHR tasks—such as looking up patients, reading clinical notes, or placing orders—by writing simple, idiomatic Python code, without needing to understand the underlying TCP sockets or data packing protocols.

  ---

  Architectural Breakdown

  The project follows a layered architecture, separating concerns to maximize modularity and ease of development.

  Key Components:

   1. Low-Level RPC Library (`vavista/`)
       * Files: vavista/rpc.py
       * Purpose: This is the foundational layer. It provides the primitive tools necessary to communicate with VistA
         RPC Broker. Its sole responsibility is to handle the raw mechanics of the TCP connection and the specific
         formatting of RPC packets (e.g., packing strings, handling delimiters, and interpreting the VistA M-language
         data structures). This layer is the only part of the application that "speaks" the native VistA protocol.

   2. VistA RPC Client (`src/vista_rpc_client.py`)
       * Purpose: This component acts as a client handler. It uses the low-level vavista library to establish and manage
         a persistent connection to the VistA server. It handles the crucial steps of authentication (sending the Access
         and Verify codes) and session management. It exposes a single, critical method, invoke_rpc, which takes an RPC
         name and its parameters, sends them to VistA, and returns the raw response.
 