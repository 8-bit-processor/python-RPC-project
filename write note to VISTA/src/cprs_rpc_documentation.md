# CPRS RPC Documentation

This document outlines the various Remote Procedure Calls (RPCs) used within the CPRS client and the lightweight Python client, along with their expected parameters and return values.

---

## User Management RPCs

*   **`ORWU USERINFO`**
    *   **Description**: Retrieves comprehensive information about the currently logged-in user.
    *   **Parameters**: None
    *   **Returns**: A string containing user details (DUZ, Name, UserClass, etc.) separated by `^`.

*   **`TIU GET PERSONAL PREFERENCES`**
    *   **Description**: Retrieves the current user's preferences for the TIU (Text Integration Utility) module.
    *   **Parameters**:
        *   `user_duz`: (Literal) The DUZ (internal entry number) of the user.
    *   **Returns**: A string containing TIU preferences (Default Location, Sort Order, Ask Subject, etc.) separated by `^`.

*   **`ORWTIU SAVE TIU CONTEXT`**
    *   **Description**: Saves the current user's TIU context/preferences.
    *   **Parameters**:
        *   `context_string`: (Literal) A semicolon-separated string containing various TIU context parameters (BeginDate;EndDate;Status;Author;MaxDocs;ShowSubject;SortBy;ListAscending;TreeAscending;GroupBy;SearchField;KeyWord).
    *   **Returns**: Confirmation of save operation.

*   **`TIU USER CLASS LONG LIST`**
    *   **Description**: Returns a long list of user classes.
    *   **Parameters**:
        *   `StartFrom`: (Literal) String to start the list from.
        *   `Direction`: (Literal) Direction of the search (e.g., 1 for forward).
    *   **Returns**: A list of user classes.

*   **`TIU DIV AND CLASS INFO`**
    *   **Description**: Retrieves division and class information for a specified user.
    *   **Parameters**:
        *   `User`: (Literal) The DUZ of the user.
    *   **Returns**: A list of strings containing division and class information.

*   **`TIU USER INACTIVE?`**
    *   **Description**: Checks if a user is marked as inactive.
    *   **Parameters**:
        *   `EIN`: (Literal) The Employee Identification Number (or DUZ) of the user.
    *   **Returns**: `1` if inactive, `0` if active.

---

## Patient Management RPCs

*   **`ORQPT PROVIDER PATIENTS`**
    *   **Description**: Retrieves a list of patients associated with a given provider.
    *   **Parameters**:
        *   `provider_ien`: (Literal) The IEN (internal entry number) of the provider.
    *   **Returns**: A list of strings, each representing a patient (DFN^PatientName^...).

*   **`ORWPT LIST ALL`**
    *   **Description**: Searches for patients based on a search term.
    *   **Parameters**:
        *   `search_term`: (Literal) The patient name or part of it to search for.
        *   `flag`: (Literal) A flag, typically "1".
    *   **Returns**: A list of strings, each representing a matching patient (DFN^PatientName^...).

*   **`ORWPT SELECT`**
    *   **Description**: Selects a patient, setting the patient context for subsequent operations.
    *   **Parameters**:
        *   `dfn`: (Literal) The DFN (internal entry number) of the patient to select.
    *   **Returns**: A string containing patient details (NAME^SEX^DOB^SSN^...).

---

## Note Management (TIU) RPCs

*   **`TIU DOCUMENTS BY CONTEXT`**
    *   **Description**: Retrieves a list of progress notes for a patient based on various criteria.
    *   **Parameters**:
        *   `DocClassIEN`: (Literal) The IEN of the document class (e.g., `3` for Progress Notes).
        *   `Context`: (Literal) The context for the search (e.g., `1` for all signed notes).
        *   `PatientDFN`: (Literal) The DFN of the patient.
        *   `EarlyDate`: (Literal) Start date for the search (FM format or empty).
        *   `LateDate`: (Literal) End date for the search (FM format or empty).
        *   `Person`: (Literal) IEN of the author (0 for all authors).
        *   `OccLim`: (Literal) Maximum number of documents to return (e.g., `100`).
        *   `SortSeq`: (Literal) Sort sequence (`A` for ascending, `D` for descending).
        *   `SHOW_ADDENDA`: (Literal) `1` to show addenda, `0` otherwise.
    *   **Returns**: A list of strings, each representing a note (IEN^Title^FMDateOfNote^Patient^Author^Location^Status^Visit).

*   **`TIU GET RECORD TEXT`**
    *   **Description**: Retrieves the full text content of a specific TIU document (note).
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
    *   **Returns**: The complete text content of the note.

*   **`TIU DETAILED DISPLAY`**
    *   **Description**: Retrieves detailed information and text for a specific TIU document.
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
    *   **Returns**: Detailed information and text content of the note.

*   **`TIU LONG LIST OF TITLES`**
    *   **Description**: Returns a comprehensive list of TIU document titles.
    *   **Parameters**:
        *   `DocClassIEN`: (Literal) The IEN of the document class.
        *   `StartFrom`: (Literal) String to start the list from.
        *   `Direction`: (Literal) Direction of the search.
        *   `IDNotesOnly`: (Literal) `1` for interdisciplinary notes only, `0` otherwise.
    *   **Returns**: A list of strings, each representing a title (IEN^Title).

*   **`TIU PERSONAL TITLE LIST`**
    *   **Description**: Returns a list of personal TIU document titles for a user.
    *   **Parameters**:
        *   `User.DUZ`: (Literal) The DUZ of the user.
        *   `CLS_PROGRESS_NOTES`: (Literal) The class of notes (e.g., `3` for progress notes).
    *   **Returns**: A list of strings, each representing a title.

*   **`TIU GET DOCUMENT TITLE`**
    *   **Description**: Retrieves the title of a specific TIU document.
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
    *   **Returns**: The title of the document.

*   **`TIU IS THIS A CONSULT?`**
    *   **Description**: Checks if a given title IEN corresponds to a consult title.
    *   **Parameters**:
        *   `TitleIEN`: (Literal) The IEN of the document title.
    *   **Returns**: `1` if it's a consult title, `0` otherwise.

*   **`TIU ISPRF`**
    *   **Description**: Checks if a given title IEN corresponds to a Patient Record Flag (PRF) title.
    *   **Parameters**:
        *   `TitleIEN`: (Literal) The IEN of the document title.
    *   **Returns**: `1` if it's a PRF title, `0` otherwise.

*   **`TIU IS THIS A CLINPROC?`**
    *   **Description**: Checks if a given title IEN corresponds to a clinical procedure title.
    *   **Parameters**:
        *   `TitleIEN`: (Literal) The IEN of the document title.
    *   **Returns**: `1` if it's a clinical procedure title, `0` otherwise.

*   **`TIU LOAD BOILERPLATE TEXT`**
    *   **Description**: Loads boilerplate text associated with a specific document title.
    *   **Parameters**:
        *   `Title`: (Literal) The IEN of the document title.
        *   `Patient.DFN`: (Literal) The DFN of the patient.
        *   `Encounter.VisitStr`: (Literal) The visit string for the encounter.
    *   **Returns**: The boilerplate text.

*   **`TIU GET PRINT NAME`**
    *   **Description**: Retrieves the print name for a given document title.
    *   **Parameters**:
        *   `TitleIEN`: (Literal) The IEN of the document title.
    *   **Returns**: The print name as a string.

*   **`ORWTIU WINPRINT NOTE`**
    *   **Description**: Retrieves a formatted version of a note, typically for printing.
    *   **Parameters**:
        *   `ANote`: (Literal) The IEN of the note.
        *   `ChartCopy`: (Literal) Boolean flag (`1` or `0`) indicating if it's a chart copy.
    *   **Returns**: Formatted note text.

*   **`ORWTIU CHKTXT`**
    *   **Description**: Checks if a TIU document contains any text.
    *   **Parameters**:
        *   `NoteIEN`: (Literal) The IEN of the note.
    *   **Returns**: `1` if text exists, `0` otherwise.

*   **`TIU GET DOCUMENT PARAMETERS`**
    *   **Description**: Retrieves various parameters associated with a TIU document.
    *   **Parameters**:
        *   `ANote`: (Literal) The IEN of the note.
    *   **Returns**: A string containing document parameters.

*   **`TIU GET REQUEST`**
    *   **Description**: Retrieves request information associated with a note.
    *   **Parameters**:
        *   `NoteIEN`: (Literal) The IEN of the note.
    *   **Returns**: A string containing request details.

*   **`TIU GET ADDITIONAL SIGNERS`**
    *   **Description**: Retrieves a list of additional signers for a TIU document.
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
    *   **Returns**: A list of additional signers.

*   **`TIU UPDATE ADDITIONAL SIGNERS`**
    *   **Description**: Updates the list of additional signers for a TIU document.
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
        *   `Signers`: (List) A list of signers to update.
    *   **Returns**: Confirmation of the update.

*   **`TIU CAN CHANGE COSIGNER?`**
    *   **Description**: Checks if the cosigner of a TIU document can be changed.
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
    *   **Returns**: `1` if changeable, `0` otherwise.

*   **`TIU UPDATE RECORD`**
    *   **Description**: Updates various fields of a TIU record.
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
        *   `Mult`: (List) A list of field-value pairs to update (e.g., `1208=COSIGNER_IEN`).
    *   **Returns**: Status of the update operation.

*   **`TIU ONE VISIT NOTE?`**
    *   **Description**: Determines if only one note of a specific type is allowed per visit.
    *   **Parameters**:
        *   `NoteEIN`: (Literal) The IEN of the note title.
        *   `DFN`: (Literal) The DFN of the patient.
        *   `VisitStr`: (Literal) The visit string.
    *   **Returns**: `1` if only one note is allowed, `0` otherwise.

*   **`TIU REQUIRES COSIGNATURE`**
    *   **Description**: Checks if a cosignature is required for a document based on title, document, author, and date.
    *   **Parameters**:
        *   `ATitle`: (Literal) The IEN of the document title (0 if `ADocument` is used).
        *   `ADocument`: (Literal) The IEN of the document (0 if `ATitle` is used).
        *   `AnAuthor`: (Literal) The IEN of the author.
        *   `ADate`: (Literal) The date of the document (FM format).
    *   **Returns**: `1` if cosignature is required, `0` otherwise, along with a reason if applicable.

*   **`TIU GET LISTBOX ITEM`**
    *   **Description**: Retrieves a formatted string for a listbox item representing a TIU document.
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
    *   **Returns**: A formatted string.

---

## Interdisciplinary Notes RPCs

*   **`IDNotesInstalled`**
    *   **Description**: Checks if Interdisciplinary Notes functionality is installed. (Note: In Delphi client, this always returns True).
    *   **Parameters**: None
    *   **Returns**: `True` or `False`.

*   **`ORWTIU CANLINK`**
    *   **Description**: Checks if a document title can be linked as an interdisciplinary child.
    *   **Parameters**:
        *   `Title`: (Literal) The IEN of the document title.
    *   **Returns**: `1` if linkable, `0` otherwise, with a reason if not.

*   **`TIU ID CAN ATTACH`**
    *   **Description**: Checks if a specific document can be attached as an interdisciplinary child.
    *   **Parameters**:
        *   `DocID`: (Literal) The IEN of the document.
    *   **Returns**: `1` if attachable, `0` otherwise, with a reason if not.

*   **`TIU ID CAN RECEIVE`**
    *   **Description**: Checks if a specific document can receive an interdisciplinary child attachment.
    *   **Parameters**:
        *   `DocID`: (Literal) The IEN of the document.
    *   **Returns**: `1` if it can receive, `0` otherwise, with a reason if not.

*   **`TIU ID ATTACH ENTRY`**
    *   **Description**: Attaches an interdisciplinary child document to a parent document.
    *   **Parameters**:
        *   `DocID`: (Literal) The IEN of the child document.
        *   `ParentDocID`: (Literal) The IEN of the parent document.
    *   **Returns**: `1` on success, `0` on failure, with a reason if applicable.

*   **`TIU ID DETACH ENTRY`**
    *   **Description**: Detaches an interdisciplinary child document from its parent.
    *   **Parameters**:
        *   `DocID`: (Literal) The IEN of the child document.
    *   **Returns**: `1` on success, `0` on failure, with a reason if applicable.

---

## Document Actions RPCs

*   **`TIU AUTHORIZATION`**
    *   **Description**: Checks user authorization for a specific action on a TIU document.
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
        *   `ActionName`: (Literal) The name of the action (e.g., "PRINT RECORD", "EDIT RECORD", "DELETE RECORD").
    *   **Returns**: `1` if authorized, `0` otherwise, along with a reason.

*   **`TIU LOCK RECORD`**
    *   **Description**: Locks a TIU document for editing.
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
    *   **Returns**: `0` on success, `1` on failure, along with an error message.

*   **`TIU UNLOCK RECORD`**
    *   **Description**: Unlocks a TIU document after editing.
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
    *   **Returns**: Confirmation of unlock.

*   **`TIU WAS THIS SAVED?`**
    *   **Description**: Checks if a TIU document was successfully saved.
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
    *   **Returns**: `1` if saved, `0` otherwise.

*   **`TIU DELETE RECORD`**
    *   **Description**: Deletes a TIU document.
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
        *   `Reason`: (Literal) The reason for deletion.
    *   **Returns**: `0` on success, `1` on failure, along with a reason.

*   **`TIU JUSTIFY DELETE?`**
    *   **Description**: Checks if deletion of a TIU document requires justification.
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
    *   **Returns**: `1` if justification is required, `0` otherwise.

*   **`TIU SIGN RECORD`**
    *   **Description**: Signs a TIU document.
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
        *   `ESCode`: (Literal) The electronic signature code.
    *   **Returns**: `0` on success, `1` on failure, along with a reason.

*   **`TIU HAS AUTHOR SIGNED?`**
    *   **Description**: Checks if the author has signed a specific TIU document.
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
        *   `User.DUZ`: (Literal) The DUZ of the author.
    *   **Returns**: `1` if signed, `0` otherwise.

*   **`TIU WHICH SIGNATURE ACTION`**
    *   **Description**: Determines the required signature action for a TIU document (e.g., "COSIGNATURE").
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the TIU document.
    *   **Returns**: The required signature action as a string.

*   **`TIU CREATE RECORD`**
    *   **Description**: Creates a new progress note.
    *   **Parameters**:
        *   `Patient.DFN`: (Literal) The DFN of the patient.
        *   `NoteRec.Title`: (Literal) The IEN of the note title.
        *   `Encounter.DateTime`: (Literal) The date/time of the encounter (FM format).
        *   `Encounter.Location`: (Literal) The IEN of the encounter location.
        *   `Mult`: (List) A list of field-value pairs for the note (e.g., `1202=AUTHOR_IEN`, `1301=DATE_TIME`, `1701=SUBJECT`).
        *   `Encounter.VisitStr`: (Literal) The visit string.
        *   `SuppressCommit`: (Literal) `1` to suppress commit logic.
    *   **Returns**: IEN of the created document and any error messages.

*   **`TIU CREATE ADDENDUM RECORD`**
    *   **Description**: Creates an addendum to an existing note.
    *   **Parameters**:
        *   `AddendumTo`: (Literal) The IEN of the note to addend to.
        *   `Mult`: (List) A list of field-value pairs for the addendum (e.g., `1202=AUTHOR_IEN`, `1301=DATE_TIME`).
        *   `SuppressCommit`: (Literal) `1` to suppress commit logic.
    *   **Returns**: IEN of the created addendum and any error messages.

*   **`TIU SET DOCUMENT TEXT`**
    *   **Description**: Sets the text content of a TIU document.
    *   **Parameters**:
        *   `NoteIEN`: (Literal) The IEN of the note.
        *   `Mult`: (List) A list of text lines (e.g., `"TEXT",1,0=Line 1`, `"TEXT",2,0=Line 2`).
        *   `Suppress`: (Literal) `1` to suppress commit logic.
    *   **Returns**: Status of the text update.

*   **`TIU LOAD RECORD FOR EDIT`**
    *   **Description**: Retrieves internal/external values for progress note fields for editing.
    *   **Parameters**:
        *   `IEN`: (Literal) The IEN of the note.
        *   `Fields`: (Literal) A semicolon-separated string of field numbers to retrieve (e.g., `.01;1301;1204`).
    *   **Returns**: A list of field-value pairs.

---

## Alert Management RPCs

*   **`ORWORB FASTUSER`**
    *   **Description**: Retrieves a list of alerts for the current user.
    *   **Parameters**:
        *   `dfn`: (Literal) The DFN of the patient (context).
    *   **Returns**: A list of strings representing the user's alerts.

*   **`ORWORB TEXT FOLLOWUP`**
    *   **Description**: Retrieves detailed text for a specific alert/notification.
    *   **Parameters**:
        *   `patient_dfn`: (Literal) The DFN of the patient.
        *   `notification`: (Literal) The notification ID.
        *   `xqaid`: (Literal) The XQAD ID.
    *   **Returns**: The detailed text of the alert.

---

## Miscellaneous RPCs

*   **`TIU GET SITE PARAMETERS`**
    *   **Description**: Retrieves site-specific parameters for the TIU module.
    *   **Parameters**: None
    *   **Returns**: A string containing site parameters.

*   **`ORWU HOSPLOC`**
    *   **Description**: Retrieves a list of hospital locations.
    *   **Parameters**: None
    *   **Returns**: A list of strings, each representing a location (IEN^Name).

*   **`ORWU NEWPERS`**
    *   **Description**: Retrieves a list of new persons (users/providers).
    *   **Parameters**: None
    *   **Returns**: A list of strings, each representing a person (IEN^Name).

*   **`TIUPatch175Installed`**
    *   **Description**: Checks if TIU patch 175 is installed.
    *   **Parameters**: None
    *   **Returns**: `True` or `False`.
