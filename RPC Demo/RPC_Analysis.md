
# CPRS RPC Analysis

This document details the analysis of Remote Procedure Calls (RPCs) used by the CPRS application to interact with the VistA backend. The analysis is based on the log files found in the `RPC CALL SEQUENCES` directory and an examination of the `ORNet.pas` source file.

## RPC Calling Conventions

All RPCs are executed via a set of wrapper functions defined in `CPRS-Lib\ORNet.pas`.

### Core Functions

*   `function sCallV(const RPCName: string; const AParam: array of const): string;`
    *   **Use:** For RPCs that return a single (scalar) string value.
    *   **Example:** Getting a specific value, creating a record and returning its new ID.

*   `procedure tCallV(ReturnData: TStrings; const RPCName: string; const AParam: array of const);`
    *   **Use:** For RPCs that return a list of strings (a table).
    *   **Example:** Fetching a list of notes, getting a list of available titles.

*   `procedure CallV(const RPCName: string; const AParam: array of const);`
    *   **Use:** For RPCs that do not return any data.
    *   **Example:** Locking/unlocking a record, procedures that only confirm an action.

### Parameter Types

The `AParam` argument is an `array of const`, which can hold various data types. The most important for RPCs are:
*   **Literals:** Strings, Integers, and Booleans are passed directly.
*   **Lists/Multi-line Text:** To pass a list of values or multi-line text (like a note body), a `TStringList` object is used.
*   **By Reference:** To pass a parameter by reference (as a Mumps global), the value is prefixed with ASCII character `#1`. The `MRef` function in `ORNet.pas` is a helper for this.

---

## Workflow Analysis

### 1. Patient Selection Context

The context for a patient is required for almost all clinical data RPCs.

1.  **Set Patient Context**
    *   **RPC:** `ORWPT SELECT`
    *   **Function:** `sCallV` (likely, to return patient context info)
    *   **Purpose:** Establishes the patient for the session.
    *   **Parameters:** The patient's DFN (unique ID).
    *   **Notes:** This is the foundational call. After it succeeds, the application runs numerous other RPCs to populate the UI with patient-specific alerts, flags, and data lists.

### 2. Reading Patient Notes

This is a two-step process.

1.  **Get Note List**
    *   **RPC:** `TIU DOCUMENTS BY CONTEXT`
    *   **Function:** `tCallV`
    *   **Purpose:** Retrieves a list of a patient's documents.
    *   **Parameters:** Includes the patient DFN and likely several flags to filter by status (e.g., unsigned, completed), service, author, or date range. This is called multiple times to build the different views on the Notes tab.
    *   **Returns:** A list of strings, where each string contains information about a single note (ID, Title, Date, Author, etc.).

2.  **Get Note Content**
    *   **RPC:** `TIU GET RECORD TEXT`
    *   **Function:** `tCallV`
    *   **Purpose:** Retrieves the full text of a specific note.
    *   **Parameters:** The IEN (unique ID) of the note selected from the list.
    *   **Returns:** A `TStringList` containing the lines of the note text.

### 3. Writing and Saving an Unsigned Note

This is the most complex workflow.

1.  **Get Title List (User clicks "New Note")**
    *   **RPC:** `TIU LONG LIST OF TITLES`
    *   **Function:** `tCallV`
    *   **Purpose:** Fetches the master list of note titles the user can select.

2.  **Create the Note Record (User selects a Title)**
    *   **RPC:** **`TIU CREATE RECORD`**
    *   **Function:** `sCallV`
    *   **Purpose:** Creates the official, but empty, note record in VistA.
    *   **Parameters:** An array containing the Patient DFN, the IEN of the selected Note Title, encounter information (location, datetime, service), and other context.
    *   **Returns:** The IEN (unique ID) of the newly created note record. This IEN is essential for all subsequent steps.

3.  **Lock the Record**
    *   **RPC:** `TIU LOCK RECORD`
    *   **Function:** `CallV` or `sCallV` (to check for success)
    *   **Purpose:** Locks the new note to the current user to prevent concurrent editing.
    *   **Parameters:** The Note IEN obtained from the previous step.

4.  **Load Boilerplate (Optional)**
    *   **RPC:** `TIU LOAD BOILERPLATE TEXT`
    *   **Function:** `tCallV`
    *   **Purpose:** If the note title has a template, this loads the default text.
    *   **Parameters:** The Note IEN.
    *   **Returns:** A `TStringList` with the boilerplate text, which the application then loads into the editor.

5.  **Save the Note Content (Unsigned)**
    *   **RPC:** **`TIU SET DOCUMENT TEXT`**
    *   **NOTE:** The RPC name for setting document text is `TIU SET DOCUMENT TEXT`. Previous analysis incorrectly noted a common misspelling in some VistA patches as `TIU SET DOCUEMENT TEXT`.
    *   **Function:** `CallV`
    *   **Purpose:** Saves the user-written text to the note record.
    *   **Parameters:**
        1.  The Note IEN.
        2.  A `TStringList` object containing the lines of text from the editor.
        3.  A flag indicating if the text should append or overwrite.
    *   **Notes:** This action saves the note in its current status (e.g., "unsigned"). It does **not** sign the note.

6.  **Unlock the Record**
    *   **RPC:** `TIU UNLOCK RECORD` (inferred, but standard practice)
    *   **Function:** `CallV`
    *   **Purpose:** Releases the lock on the note after the user is finished editing.
    *   **Parameters:** The Note IEN.
