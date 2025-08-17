# CPRS TIU and Template System Documentation

This document provides a detailed technical explanation of the CPRS Text Integration Utilities (TIU) and the integrated Template system. The information is derived from analysis of the CPRS Delphi source code and is intended to guide the development of a Python client capable of correctly interacting with these VistA backend services.

## 1. Core Concepts

The TIU system is the foundation for all clinical documents in CPRS. Templates are a powerful, user-facing feature for creating and managing reusable text with dynamic components that integrates directly with the TIU system.

### 1.1. TIU Document Hierarchy

All text-based clinical documents in CPRS (Progress Notes, Discharge Summaries, Consults, etc.) are TIU documents. These documents are not stored as simple text but as records in VistA's TIU package (files in the 8925 range). They are organized in a hierarchical structure, often referred to as an "inheritance tree."

-   **Document Classes:** The tree is organized by document classes. For example, "Progress Notes" is a high-level class, which can contain more specific sub-classes of notes.
-   **Parent-Child Relationships:** Documents can have parent-child relationships. A common example is an addendum, which is a child document attached to an original parent note.
-   **Client-Side Representation:** In CPRS, this hierarchy is visually represented in the "Notes" and other tabs using a tree view control. The `uDocTree.pas` unit contains the client-side logic for building and managing this tree.
-   **Key RPC:** The primary RPC for fetching the document list for this tree is `TIU DOCUMENTS BY CONTEXT`. It's a flexible RPC that can retrieve documents based on patient, date range, document class, and other context-specific filters.

### 1.2. Templates (`TTemplate`)

Templates are the primary mechanism for code and text reuse in CPRS documents. They are far more advanced than simple text snippets. In the Delphi code, they are represented by the powerful `TTemplate` class (`uTemplates.pas`).

-   **Hierarchical Structure:** Like TIU documents, templates are also organized in a tree structure with groups (folders) and individual templates. Users can have personal templates (`My Templates`) and access a shared, system-wide repository (`Shared Templates`).
-   **Boilerplate Text:** The core content of a template is its "boilerplate" text. This text can be static or contain dynamic elements.
-   **Linked Templates:** Templates can be directly linked to specific document types, such as a Progress Note Title or a Consult Service. When a user selects that title/service, the linked template is automatically suggested or loaded.

### 1.3. Boilerplate and Dynamic Content

"Boilerplate" is the term for a template's content. It can contain three types of dynamic elements:

1.  **TIU Objects:** These are special VistA objects that are resolved on the server side. They are enclosed in `|` pipes (e.g., `|PATIENT NAME|`). The client sends the text with these objects, and the VistA RPC resolves them into the correct data. The RPC `TIU TEMPLATE GETTEXT` is often used for this.
2.  **Template Fields:** These are client-side dynamic fields that prompt the user for input.
3.  **Grouped Items:** A template of type "Group" can be configured to automatically include the boilerplate text of all its child items.

### 1.4. Template Fields (`TTemplateField`)

Template Fields are the most complex part of the template system. They allow for the creation of interactive dialogs to gather data from the user.

-   **Syntax:** Fields are embedded in boilerplate text using the syntax `{FLD:FIELD_NAME}` or `{FLD:FIELD_NAME|ID}`.
-   **`uTemplateFields.pas`:** This unit defines the `TTemplateField` class and all the logic for parsing and managing these fields.
-   **`fTemplateDialog.pas`:** This form is responsible for dynamically building the user-facing dialog box based on the template fields found in a boilerplate. It creates controls (edit boxes, checkboxes, etc.) on the fly.
-   **Field Types:** The system supports numerous field types, including:
    -   Edit Box (`dftEditBox`)
    -   Combo Box (`dftComboBox`)
    -   Checkbox (`dftCheckBoxes`)
    -   Date/Time (`dftDate`)
    -   Button (`dftButton`) for more complex interactions.

## 2. Developer's Workflow for Handling Templates

To correctly implement template handling in a Python client, the following workflow must be followed. This mirrors the process in the Delphi application.

1.  **User Selects a Template:** The user chooses a template from the template tree.
2.  **Fetch Boilerplate:** The client retrieves the template's raw boilerplate text using the `TIU TEMPLATE GETBOIL` RPC, passing the template's IEN.
3.  **Scan for Template Fields:** The client must parse the boilerplate text for any occurrences of the `{FLD:...}` syntax. The `BoilerplateTemplateFieldsOK` and `ListTemplateFields` functions in `uTemplateFields.pas` are the reference for this logic.
4.  **Build and Show Dialog (if fields exist):**
    -   If fields are found, the client needs to dynamically build a dialog to capture user input for each field.
    -   For each field name, the client must call `TIU FIELD LOAD` or `TIU FIELD LOAD BY IEN` to get the field's definition (type, default value, list items for a combo box, etc.).
    -   The `fTemplateDialog.pas` unit is the reference for how this dialog is constructed and behaves.
5.  **Resolve Fields:** After the user completes the dialog, the client substitutes the `{FLD:...}` placeholders in the boilerplate with the user's input.
6.  **Resolve TIU Objects:** The now field-resolved text is sent to the server using the `TIU TEMPLATE GETTEXT` RPC. The server processes this text, resolving all the `|OBJECT|` placeholders, and returns the final, complete text.
7.  **Insert into Document:** This final text is inserted into the main text editor for the TIU document.
8.  **Save Document:** The entire document is saved using `TIU CREATE RECORD` (for a new note) or `TIU UPDATE RECORD` (for an existing note).

## 3. Key Delphi Source Code Files

For developers wishing to understand the original implementation, the following files are critical:

-   **`uTemplates.pas`**: Defines the `TTemplate` class. The heart of the template object model.
-   **`uTemplateFields.pas`**: Defines the `TTemplateField` class and logic for parsing/managing dynamic fields.
-   **`fTemplateDialog.pas`**: The form that creates the dynamic dialog for filling in template fields.
-   **`rTemplates.pas`**: Contains the client-side wrappers for all RPCs related to templates and template fields.
-   **`uTIU.pas`**: Defines core TIU data structures like `TTIUContext`.
-   **`rTIU.pas`**: Contains the client-side wrappers for all core TIU document RPCs.
-   **`dShared.pas`**: A shared data module with helper functions like `BoilerplateOK` used across the application.
-   **`fNotes.pas`, `fDCSumm.pas`, `fSurgery.pas`, `fConsults.pas`**: The main UI forms for different document types. They contain the logic for integrating and calling the template system.

## 4. Key RPCs for TIU and Templates

A Python client will need to implement calls to the following RPCs to fully support this system.

### Template Management RPCs (from `rTemplates.pas`)

| RPC Name                      | Description                                                                 | Parameters (from Delphi)                               | Returns                                                               |
| ----------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------ | --------------------------------------------------------------------- |
| **`TIU TEMPLATE GETROOTS`**     | Gets the top-level template folders (My Templates, Shared Templates, etc.). | `User.DUZ`                                             | A list of root template definitions.                                  |
| **`TIU TEMPLATE GETITEMS`**     | Gets the children (sub-folders or templates) of a given template group.     | `ID` (IEN of the parent template)                      | A list of child template definitions.                                 |
| **`TIU TEMPLATE GETBOIL`**      | Retrieves the raw, unresolved boilerplate text for a template.              | `ID` (IEN of the template)                             | The boilerplate text as a multi-line string.                          |
| **`TIU TEMPLATE GETTEXT`**      | Resolves server-side TIU objects (`|...|`) in a given block of text.         | `BoilerPlate` (The text to process)                    | The processed text with objects resolved.                             |
| **`TIU TEMPLATE CREATE/MODIFY`**| Creates a new template or saves changes to an existing one.                 | `ID` (IEN, or 0 for new), `Fields` (list of properties)| The IEN of the saved template.                                        |
| **`TIU TEMPLATE LOCK/UNLOCK`**  | Locks or unlocks a template for editing to prevent concurrent modification.  | `ID` (IEN of the template)                             | `1` for success, `0` for failure.                                     |
| **`TIU TEMPLATE DELETE`**       | Deletes one or more templates.                                              | `DelList` (A list of template IENs to delete)          | -                                                                     |

### Template Field RPCs (from `rTemplates.pas`)

| RPC Name                      | Description                                                                 | Parameters (from Delphi)                               | Returns                                                               |
| ----------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------ | --------------------------------------------------------------------- |
| **`TIU FIELD LIST`**            | Gets a list of all available template fields.                               | `StartFrom`, `Direction`                               | A list of template fields.                                            |
| **`TIU FIELD LOAD`**            | Loads the full definition of a template field by its name.                  | `DlgFld` (Name of the field)                           | A list of strings containing the field's properties.                  |
| **`TIU FIELD LOAD BY IEN`**     | Loads the full definition of a template field by its IEN.                   | `DlgFld` (IEN of the field)                            | A list of strings containing the field's properties.                  |
| **`TIU FIELD SAVE`**            | Creates or updates a template field definition.                             | `ID` (IEN, or 0 for new), `Fields` (list of properties)| The IEN of the saved field.                                           |
| **`TIU FIELD LOCK/UNLOCK`**     | Locks or unlocks a template field for editing.                              | `ID` (IEN of the field)                                | `1` for success, `0` for failure.                                     |
| **`TIU FIELD CAN EDIT`**        | Checks if the current user has permission to edit template fields.          | -                                                      | `1` if user can edit, `0` otherwise.                                  |

### Core TIU Document RPCs (from `rTIU.pas`)

| RPC Name                      | Description                                                                 | Parameters (from Delphi)                               | Returns                                                               |
| ----------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------ | --------------------------------------------------------------------- |
| **`TIU DOCUMENTS BY CONTEXT`**  | Retrieves a list of TIU documents based on various criteria.                | `Class`, `Context`, `DFN`, `Dates`, `Person`, `Limit`  | A list of `^`-delimited strings, each representing a document.        |
| **`TIU GET RECORD TEXT`**       | Retrieves the full, saved text content of a specific TIU document.          | `IEN` (of the document)                                | The document text as a multi-line string.                             |
| **`TIU CREATE RECORD`**         | Creates a new TIU document on the VistA server.                             | `RecordData` (A list of properties for the new note)   | The IEN of the newly created document.                                |
| **`TIU UPDATE RECORD`**         | Updates an existing TIU document (e.g., to add text, change status).        | `IEN`, `RecordData` (list of fields to update)         | `1` for success, `0` for failure.                                     |
| **`TIU SIGN RECORD`**           | Applies an electronic signature to a document.                              | `IEN`, `ESCode` (Electronic Signature Code)            | `1` for success, `0` for failure.                                     |
| **`TIU DELETE RECORD`**         | Deletes a TIU document.                                                     | `IEN`, `Reason`                                        | `1` for success, `0` for failure.                                     |
| **`TIU LOCK RECORD`**           | Locks a TIU document for editing.                                           | `IEN`                                                  | `1` for success, `0` for failure.                                     |
| **`TIU UNLOCK RECORD`**         | Unlocks a previously locked TIU document.                                   | `IEN`                                                  | -                                                                     |
| **`TIU LOAD BOILERPLATE TEXT`** | Retrieves the boilerplate text associated with a specific document *title*. | `TitleIEN`, `Patient.DFN`, `Encounter.VisitStr`        | The boilerplate text.                                                 |

---
