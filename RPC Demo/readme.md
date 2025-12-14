# VistA RPC Client: Technical overview

This document provides a technical overview of the VistA RPC Client application, focusing on core VistA identifiers (DFN, IEN), key Remote Procedure Calls (RPCs), and how these RPCs are orchestrated to perform essential business operations within the healthcare system.

## 1. Core VistA Identifiers: DFN and IEN

In the VistA ecosystem, two fundamental identifiers are crucial for managing patient data and system entries:

*   **DFN (Division File Number / Patient Internal Entry Number)**:
    *   **Definition**: DFN is the unique internal identifier for a patient within VistA. It's akin to a primary key for patient records.
    *   **Significance**: Almost all patient-centric operations in VistA (e.g., retrieving notes, ordering labs, selecting a patient) require the patient's DFN to identify the specific individual. It links various clinical data points back to a single patient.

*   **IEN (Internal Entry Number)**:
    *   **Definition**: IEN is a generic unique internal identifier used throughout VistA for almost every entry in its FileMan database. This includes IENs for specific lab tests, note titles, locations, providers, orderable items, and more.
    *   **Significance**: IENs allow precise referencing of discrete data elements. For example, when ordering a lab, you refer to the lab test by its IEN; when creating a note, you specify the note title by its IEN.

*   **IMPLICATIONS for DEVELOPMENT**:
*   **Significance**: DFNs and IENs are fundamental for pulling and pushing VistA data through RPCs, by serving
    as unique identifiers DFN for patients and IEN for other system entities. RPC workflows vary greatly, from simple
    calls like ORWU USERINFO with no parameters, to complex multi-step sequences like create_note and
    order_lab_test_full_sequence which leverage numerous RPCs and IENs to perform high-level functions, mirroring the
    detailed interactions of CPRS.  

## 2. RPC Communication Process via the Broker

This application interacts with the VistA server using a Python library that acts as a client for the VistA RPC Broker. This broker facilitates secure and structured communication between client applications (like ours) and the Mumps backend of VistA.
    
### Connection and Login Flow:
1.  **`VistaRpcClient.connect_to_vista(host, port, access, verify, context)`**:
    *   This method initializes the connection parameters (IP, Port, Access Code, Verify Code, Application Context).
    *   It then calls `VistaRpcClient.login()`.
2.  **`VistaRpcClient.login()`**:
    *   Attempts to establish a TCP/IP connection to the VistA server using the `vavista.rpc.connect` function.
    *   Performs authentication using the provided Access Code and Verify Code.
    *   Sets the application context (e.g., "OR CPRS GUI CHART") which determines available RPCs and permissions.
    *   If successful, a persistent `connection` object is stored.

### RPC Invocation (`VistaRpcClient.invoke_rpc`):
*   This is the central method for executing any RPC on the VistA server.
*   **Automatic Login Check**: Before invoking an RPC, it first checks if a valid connection exists by calling `self.login()`. If not connected, it attempts to log in automatically.
*   **Parameter Handling**: It intelligently processes RPC parameters:
    *   If a single string parameter is provided (e.g., "literal:VALUE1;VALUE2"), it parses it into `PLiteral` objects or other `vavista.rpc` parameter types.
    *   If parameters are already provided as `PLiteral`, `PList`, or `PWordProcess` objects, they are passed directly.
*   **Communication Logging**: If a `comm_logger` is configured, it logs the RPC name and its parameters *before* sending, and the raw reply *after* receiving, which is invaluable for debugging and understanding VistA's response format.
*   **Execution**: It uses the `self.connection.invoke(rpc_name, *processed_params)` call from the `vavista` library to send the RPC request and receive the raw string reply from VistA.
*   **Raw Reply**: All RPCs return a raw string from VistA, which then needs to be parsed by the client application.

## 3. Core RPCs and Business Operation Sequences

The application utilizes various RPCs to fulfill common CPRS functionalities. These are often executed in specific sequences to achieve a business operation.

### 3.1. User and Patient Context Setup

*   **`ORWU USERINFO` (via `VistaRpcClient.get_user_info`)**:
    *   **Purpose**: Retrieves the currently logged-in user's DUZ (internal ID), Name, and User Class. Essential for identifying the acting user for audit trails and permissions.
    *   **Sequence**: Typically called immediately after a successful login to establish the user's identity within the session.
*   **`ORWPT SELECT` (via `VistaRpcClient.select_patient` and `order_entry.get_patient_info`)**:
    *   **Purpose**: Sets the context to a specific patient and retrieves basic demographic information (Name, Sex, DOB).
    *   **Sequence**: Called after a patient is identified, often following a search or selection from a list.
*   **`ORWPT LIST ALL` (via `VistaRpcClient.search_patient`)**:
    *   **Purpose**: Searches for patients based on a partial name match.
    *   **Sequence**: Initiates patient selection; results are typically presented to the user for a definitive choice, which then leads to `ORWPT SELECT`.
*   **`ORQPT PROVIDER PATIENTS` (via `VistaRpcClient.get_doctor_patients`)**:
    *   **Purpose**: Retrieves a list of patients associated with a specific provider.
    *   **Sequence**: Used when a provider wants to quickly access their panel of patients.

### 3.2. Note Management

TIU (Text Integration Utility) RPCs are used for managing clinical notes.

*   **`TIU DOCUMENTS BY CONTEXT` (via `VistaRpcClient.fetch_patient_notes`)**:
    *   **Purpose**: Retrieves a list of notes for a patient, filtered by document class (e.g., Progress Notes), context (e.g., signed, unsigned, all), and maximum number of documents.
    *   **Sequence**: Used to populate the patient's note history.
*   **`TIU GET RECORD TEXT` (via `VistaRpcClient.read_note_content`)**:
    *   **Purpose**: Fetches the full text content of a specific TIU document.
    *   **Sequence**: Called when a user selects a note to view its details.
*   **Note Creation Sequence (via `VistaRpcClient.create_note`)**: A multi-step process to ensure data integrity and proper VistA workflow:
    1.  **`TIU CREATE RECORD`**: Creates an initial placeholder record for the note, returning its IEN. Parameters include patient DFN, title IEN, author DUZ, encounter details.
    2.  **`TIU LOCK RECORD`**: Locks the newly created record to prevent concurrent modifications during editing.
    3.  **`TIU UPDATE RECORD`**: Updates metadata like the note's subject line.
    4.  **`TIU AUTHORIZATION`**: Checks if the user is authorized to edit the record.
    5.  **`TIU SET DOCUMENT TEXT`**: Sets the actual content of the note. This RPC handles text in pages (chunks of ~300 lines) and can either commit the text immediately or suppress the commit until signing.
    6.  **(Optional) `TIU SIGN RECORD`**: If the note is to be signed, the electronic signature code (ES Code) is sent.
    7.  **`TIU UNLOCK RECORD`**: Releases the lock on the record, making it available again.
*   **Addendum Creation Sequence (via `VistaRpcClient.create_addendum`)**: Similar to note creation, but links to an existing parent note.
    1.  **`TIU CREATE ADDENDUM RECORD`**: Creates an addendum record linked to a `parent_ien`.
    2.  **`TIU LOCK RECORD`**: Locks the addendum.
    3.  **`TIU SET DOCUMENT TEXT`**: Sets the addendum text.
    4.  **(Optional) `TIU SIGN RECORD`**: Signs the addendum.
    5.  **`TIU UNLOCK RECORD`**: Unlocks the addendum.
*   **`TIU DELETE RECORD` (via `VistaRpcClient.delete_note`)**: Deletes a specified TIU record with a reason.

### 3.3. Order Entry

Orchestrated by the `OrderEntry` and `LabOrderController` classes.

*   **General Order Menu Retrieval**:
    *   `get_main_order_menu` (in `OrderEntry`): Currently loads from a local `order_menu.json` file, providing a cached list of top-level order categories (e.g., Labs, Medications, Consults). This mimics a static menu in CPRS.
    *   `get_order_group_items` (in `OrderEntry`):
        *   For "LAB" type: Uses `ORWLRR ALLTESTS` (via `VistaRpcClient.get_all_lab_tests`) to fetch a comprehensive, cached list of lab tests.
        *   For other types (e.g., Radiology, Consults): Employs a sequence of RPCs (`ORWDXM3 ISUDQO`, `ORIMO ISIVQO`, `OREVNTX1 ODPTEVID`, `OREVNTX1 GTEVT`, `ORWDPS2 QOGRP`) to set context and retrieve orderable items relevant to the selected category.
*   **Order Creation/Modification Core RPCs**:
    *   **`ORWDXC ACCEPT` (via `OrderEntry.accept_order`)**: Performs server-side validation of proposed order parameters. This is a crucial pre-save step to check for clinical alerts, missing information, or invalid combinations. It does *not* save the order.
    *   **`ORWDX SAVE` (via `OrderEntry.save_order`)**: Saves the order to VistA after it has passed validation checks. It takes the patient, provider, location, order dialog name, display group, orderable item IEN, and a list of user responses (in a `PList` format) as parameters.
*   **Lab Order Specific Sequence (`OrderEntry.order_lab_test_full_sequence`)**: A complex sequence mimicking CPRS's detailed steps for lab ordering:
    1.  **UI Context RPCs**: `ORWDX WRLST`, `OREVNTX PAT`, `ORWORDG IEN`, `ORWOR VWGET`, `ORWORR AGET`, `ORWORR GET4LST` (for "Orders" tab).
    2.  **Lab Menu Context RPCs**: `ORWU NPHASKEY` (multiple times), `ORPWDX LOCK`, `ORWDX DISMSG`, `ORWDXM MSTYLE`, `ORWDXM MENU` (for "Lab Ordering" menu).
    3.  **Lab Test Details/Validation RPCs**: Numerous RPCs like `ORWDXM3 ISUDQO`, `ORIMO ISIVQD`, `ORWDRA32 LOCTYPE`, `ORWDX DLGDEF`, `ORWDLR32 DEF`, `ORWDLR33 LASTTIME`, `ORWDX ORDITM`, `ORWDLR32 MAXDAYS`, `ORWDXRO1 ISSPLY`, `ORWDX LOADRSP` are called to prepare the lab order dialog, fetch defaults, and perform real-time checks.
    4.  **`ORWDXC ACCEPT`**: Performs validation for the specific lab order.
    5.  **`ORWDX SAVE`**: Saves the lab order.
    6.  **Post-Save RPCs**: `ORWDDBA1 BASTATUS`, `ORWCOM ORDEROBJ`, `ORTO DGROUP`, `ORWPT CWAD`, `ORWDX AGAIN`, `ORWDXM2 CLRRCL` are executed for UI updates and clearing contexts.
*   **`ORWDLR32 DEF` (via `VistaRpcClient.get_lab_order_defaults` and `LabOrderController.handle_lab_order_selection`)**:
    *   **Purpose**: Retrieves default values and pick-lists (e.g., collection types, urgencies, schedules) for the lab order dialog.
    *   **Sequence**: Called when initiating a lab order to populate the input form.
*   **`ORWDLR32 LOAD` (via `VistaRpcClient.get_lab_test_details` and `OrderEntry.get_and_parse_lab_details`)**:
    *   **Purpose**: Fetches detailed information for a specific lab test (e.g., associated specimens, collection samples).
    *   **Sequence**: Called after a specific lab test is selected to tailor the order dialog.

## 4. How to Use GUI Functions to Support a Developer

The GUI application (`main.py`) provides a powerful interface for developers to understand and reverse-engineer VistA RPC interactions, which is crucial for building new applications or extending existing ones.

### 4.1. Connection Setup
*   **Developer Action**: On the "VistA Connection" section, enter the `Host`, `Port`, `Access Code`, `Verify Code`, and `App Context` for your VistA instance. These are the credentials and network details required to connect to VistA.
*   **Developer Insight**: This directly corresponds to the `VistaRpcClient.connect_to_vista` method. Understanding these parameters is the first step in any VistA integration.

### 4.2. Observing RPC Communication
*   **Key Tool: "Open RPC Comm Log" Button**:
    *   **Developer Action**: Click this button in the "VistA Connection" section. A separate "RPC Communication Log" window will appear.
    *   **Developer Insight**: This log is a tool helpful for reverse-engineering VistA. Every RPC request sent to VistA and its corresponding raw reply will be displayed here. By observing this log while interacting with the GUI, a developer can:
        *   **Identify RPC Names**: See exactly which RPCs CPRS (or our client) is calling for a given action.
        *   **Understand Parameters**: Examine the `Parameters` section of each log entry to see what arguments (and in what format, e.g., `PLiteral`, `PList`) are being sent for a specific RPC.
        *   **Analyze Raw Replies**: Study the `Raw Reply` section to understand the exact string format VistA returns. This is critical for parsing logic in their own applications.
        *   **Debug Issues**: If an operation fails, the RPC Comm Log will show the problematic RPC call and VistA's direct error message, helping pinpoint the problem.

### 4.3. Patient Selection and Context
*   **Developer Action**:
    1.  Use the "Search Name" field on the "Patient Selection" tab and click "Search" to find a patient.
    2.  Select a patient from the results.
    3.  Observe the `RPC Communication Log` and the main `Log` window.
*   **Developer Insight**: This will show the RPC `ORWPT LIST ALL` for search and `ORWPT SELECT` for selection. You'll see how the `patient_dfn` is used to establish context and how initial patient data is retrieved.

### 4.4. Note Management (Viewing and Creating)
*   **Developer Action**:
    1.  On the "Patient Selection" tab, click "Get Recent Notes" or "Get Unsigned Notes".
    2.  Double-click a note in the "Patient Notes" treeview to view its content.
    3.  Navigate to the "Add Note" tab, select a "Note Title", an "Encounter", enter "Note Content", and click "Save Note" (or "Save Unsigned").
    4.  Closely monitor the `RPC Communication Log` during all these actions.
*   **Developer Insight**: This demonstrates the `TIU DOCUMENTS BY CONTEXT` for listing notes, `TIU GET RECORD TEXT` for reading content, and the complex sequence of `TIU CREATE RECORD`, `TIU LOCK RECORD`, `TIU SET DOCUMENT TEXT`, `TIU SIGN RECORD`, `TIU UNLOCK RECORD` for note creation. Pay attention to how `title_ien`, `patient_dfn`, `encounter_location_ien`, and `es_code` are passed.

### 4.5. Order Entry (General and Lab Specific)
*   **Developer Action**:
    1.  On the "Order Entry" tab, double-click a top-level category (e.g., "Labs").
    2.  Double-click a specific orderable item (e.g., a lab test).
    3.  If a dialog appears (e.g., for lab orders), make selections and click "Accept Order".
    4.  Review the `RPC Communication Log` during each step.
*   **Developer Insight**:
    *   For general categories, observe if the `ORWDPS2 QOGRP` RPC is called and how its parameters (`order_type`) change.
    *   For "Labs", you'll see calls to `ORWLRR ALLTESTS` for the full list, `ORWDLR32 DEF` for dialog defaults, and `ORWDLR32 LOAD` for specific test details.
    *   The complex RPC sequence of `order_lab_test_full_sequence` is broken down in the log, showing many context-setting and validation RPCs leading up to `ORWDXC ACCEPT` and `ORWDX SAVE`. This is invaluable for understanding the detailed client-side RPC orchestration required for ordering.

Using the GUI and correlating UI actions with the RPC Communication Log can help gain an understanding of the VistA RPCs necessary to implement similar functionalities in their own applications. The structured parsing logic within `VistaRpcClient` and `OrderEntry` also serves as a direct reference for how to interpret VistA's often cryptic string-based replies.