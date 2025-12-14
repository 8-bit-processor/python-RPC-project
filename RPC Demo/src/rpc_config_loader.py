import os
import re

class RPCConfigLoader:
    """
    Loads VistA RPC (Remote Procedure Call) configurations from a plain text list
    and detailed documentation from a Markdown file. It parses this information
    to provide a structured overview of available RPCs, their descriptions,
    parameters, and return values.
    """
    def __init__(self, rpc_list_file, rpc_doc_file, important_rpcs_filter=None):
        """
        Initializes the RPCConfigLoader with paths to RPC definition files.
        Args:
            rpc_list_file (str): Path to a file listing RPC names (one per line).
            rpc_doc_file (str): Path to a Markdown file containing detailed RPC documentation.
            important_rpcs_filter (list, optional): A list of RPC names to filter for.
                                                     If provided, only these RPCs will be actively used.
        """
        self.rpc_list_file = rpc_list_file
        self.rpc_doc_file = rpc_doc_file
        self.important_rpcs_filter = important_rpcs_filter
        
        # Internal storage for RPC names and detailed information
        self.all_rpc_names = []  # List of all RPC names found in the rpc_list_file
        self.all_rpc_info = {}   # Dictionary to store parsed RPC details from Markdown
        
        # Filtered/final RPC data to be exposed
        self.rpc_names = []      # List of RPC names after applying any filters
        self.rpc_info = {}       # Dictionary of RPC details after applying any filters

    def load_rpc_list(self):
        """
        Loads RPC names from the specified plain text file (self.rpc_list_file).
        Each line in the file is expected to be a single RPC name.
        Populates self.all_rpc_names.
        Raises:
            FileNotFoundError: If the RPC list file does not exist.
        """
        try:
            with open(self.rpc_list_file, 'r') as f:
                self.all_rpc_names = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            raise FileNotFoundError(f"RPC list file not found: {self.rpc_list_file}")

    def load_from_markdown(self):
        """
        Loads detailed RPC documentation from the specified Markdown file (self.rpc_doc_file).
        It parses the file to extract RPC categories, RPC names, descriptions, parameters,
        and return values using regular expressions.
        Populates self.all_rpc_info.
        Raises:
            FileNotFoundError: If the RPC documentation file does not exist.
        """
        print("DEBUG: Entering load_from_markdown")
        try:
            with open(self.rpc_doc_file, 'r') as f:
                content = f.read()
            print(f"DEBUG: Read content from {self.rpc_doc_file}, length: {len(content)}")
        except FileNotFoundError:
            raise FileNotFoundError(f"RPC documentation file not found: {self.rpc_doc_file}")

        # Regex to find categories and their RPCs
        # This pattern captures the category heading (e.g., "### Patient Selection")
        # and all content until the next category heading or end of file.
        category_pattern = re.compile(r"### (.*?)\n(.*?)(?=\n### |\Z)", re.S)
        
        # Regex to extract individual RPC details within a category
        # It looks for a specific Markdown format:
        # * **`RPC NAME`**
        #   * **Description**: ...
        #   * **Parameters**: ...
        #   * **Returns**: ...
        rpc_pattern = re.compile(
            r"^\*\s+\*\*`([^`]+)`\*\*\n"  # Group 1: RPC name (e.g., `ORWPT LIST ALL`)
            r"\s+\*\s+\*\*Description\*\*:\s*(.*?)\n" # Group 2: Description
            r"\s+\*\s+\*\*Parameters\*\*:\s*(.*?)\n" # Group 3: Parameters
            r"\s+\*\s+\*\*Returns\*\*:\s*(.*?)" # Group 4: Returns
            r"(?=\n^\*\s+\*\*`|\n### |\Z)", # Lookahead for next RPC or category or end of file
            re.M | re.S # M: multiline mode (for ^ to match start of line), S: dotall mode (. matches newline)
        )

        for cat_match in category_pattern.finditer(content):
            category = cat_match.group(1).strip()
            rpc_content = cat_match.group(2)
            print(f"DEBUG: Found category: {category}")
            print(f"DEBUG: RPC content for {category}, length: {len(rpc_content)}")
            self.all_rpc_info[category] = {}

            for rpc_match in rpc_pattern.finditer(rpc_content):
                rpc_name = rpc_match.group(1).strip()
                description = rpc_match.group(2).strip()
                parameters = rpc_match.group(3).strip()
                returns = rpc_match.group(4).strip()

                print(f"DEBUG:   Found RPC: {rpc_name}")
                print(f"DEBUG:     Description: {description[:50]}...")
                print(f"DEBUG:     Parameters: {parameters[:50]}...")
                print(f"DEBUG:     Returns: {returns[:50]}...")

                self.all_rpc_info[category][rpc_name] = {
                    "description": description,
                    "parameters": parameters,
                    "returns": returns
                }
        print("DEBUG: Exiting load_from_markdown")

    def filter_rpcs(self):
        """
        Applies filtering based on `important_rpcs_filter` if provided.
        If a filter is set, `self.rpc_names` will contain only RPCs present in the filter list.
        `self.rpc_info` remains `self.all_rpc_info` for now, assuming RPC details are always useful
        and downstream logic will use `rpc_names` to access relevant info.
        """
        if self.important_rpcs_filter:
            # Filter self.all_rpc_names to include only those present in the important_rpcs_filter
            self.rpc_names = [rpc for rpc in self.all_rpc_names if rpc in self.important_rpcs_filter]
            # This part might need adjustment based on how you want to handle important RPCs
            # For now, we just filter the names, and the info will be available if loaded
        else:
            # If no filter is specified, all RPC names are considered "important"
            self.rpc_names = self.all_rpc_names
        # The rpc_info is set to all_rpc_info; further filtering might be needed if categories
        # also need to be filtered based on the important_rpcs_filter.
        self.rpc_info = self.all_rpc_info

    def load_all(self):
        """
        Executes the full loading process:
        1. Loads RPC names from the list file.
        2. Loads detailed RPC information from the Markdown documentation.
        3. Filters the loaded RPC information based on any specified `important_rpcs_filter`.
        4. Filters out any empty categories from `self.rpc_info`.
        Returns:
            tuple: A tuple containing:
                - list: The list of filtered RPC names (self.rpc_names).
                - dict: The dictionary of RPC information (self.rpc_info), organized by category.
        """
        self.load_rpc_list()     # Load RPC names
        self.load_from_markdown() # Load detailed RPC docs

        # Filter out empty categories that might result from parsing or if no RPCs were found for a category.
        self.rpc_info = {k: v for k, v in self.all_rpc_info.items() if v} 
        
        self.filter_rpcs()       # Apply any RPC name filters

        return self.rpc_names, self.rpc_info
