import os
import re

class RPCConfigLoader:
    def __init__(self, rpc_list_file, rpc_doc_file, important_rpcs_filter=None):
        self.rpc_list_file = rpc_list_file
        self.rpc_doc_file = rpc_doc_file
        self.important_rpcs_filter = important_rpcs_filter
        self.all_rpc_names = []
        self.all_rpc_info = {}
        self.rpc_names = []
        self.rpc_info = {}

    def load_rpc_list(self):
        try:
            with open(self.rpc_list_file, 'r') as f:
                self.all_rpc_names = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            raise FileNotFoundError(f"RPC list file not found: {self.rpc_list_file}")

    def load_from_markdown(self):
        try:
            with open(self.rpc_doc_file, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"RPC documentation file not found: {self.rpc_doc_file}")

        # Regex to find categories and their RPCs
        category_pattern = re.compile(r"### (.*?)\n(.*?)(?=\n### |\Z)", re.S)
        rpc_pattern = re.compile(
            r"^\*\s+\*\*`([^`]+)`\*\*:\s*(.*?)\n"  # RPC name and description
            r"^\s+\*\s+\*\*Parameters\*\*:\s*(.*?)\n" # Parameters
            r"^\s+\*\s+\*\*Returns\*\*:\s*(.*?)" # Returns
            r"(?=\n^\*\s+\*\*`|\n### |\Z)", # Lookahead for next RPC or category or end of file
            re.M | re.S
        )

        for cat_match in category_pattern.finditer(content):
            category = cat_match.group(1).strip()
            rpc_content = cat_match.group(2)
            self.all_rpc_info[category] = {}

            for rpc_match in rpc_pattern.finditer(rpc_content):
                rpc_name = rpc_match.group(1).strip()
                description = rpc_match.group(2).strip()
                parameters = rpc_match.group(3).strip()
                returns = rpc_match.group(4).strip()

                self.all_rpc_info[category][rpc_name] = {
                    "description": description,
                    "parameters": parameters,
                    "returns": returns
                }

    def filter_rpcs(self):
        if self.important_rpcs_filter:
            self.rpc_names = [rpc for rpc in self.all_rpc_names if rpc in self.important_rpcs_filter]
            # This part might need adjustment based on how you want to handle important RPCs
            # For now, we just filter the names, and the info will be available if loaded
        else:
            self.rpc_names = self.all_rpc_names
        self.rpc_info = self.all_rpc_info

    def load_all(self):
        self.load_rpc_list()
        self.load_from_markdown()
        self.rpc_info = {k: v for k, v in self.rpc_info.items() if v} # Filter out empty categories
        self.filter_rpcs()
        return self.rpc_names, self.rpc_info
