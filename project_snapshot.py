
#!/usr/bin/env python
"""
Project snapshot generator for AI-assisted development.
This script scans Python files in the project and extracts function/class definitions
along with their docstrings to create a concise snapshot of available functionality.
"""
import os
import ast
import json
import re
from typing import Dict, List, Any, Optional, Set, Tuple

def get_docstring(node: ast.AST) -> Optional[str]:
    """Extract docstring from an AST node if it exists"""
    if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)) and node.body:
        first_node = node.body[0]
        if isinstance(first_node, ast.Expr) and isinstance(first_node.value, ast.Str):
            return first_node.value.s.strip()
    return None

def extract_arg_info(args: ast.arguments) -> List[str]:
    """Extract function argument information"""
    arg_list = []
    for arg in args.args:
        arg_list.append(arg.arg)
    if args.vararg:
        arg_list.append(f"*{args.vararg.arg}")
    if args.kwarg:
        arg_list.append(f"**{args.kwarg.arg}")
    return arg_list

def extract_class_info(node: ast.ClassDef) -> Dict[str, Any]:
    """Extract information from a class definition"""
    methods = {}
    class_vars = {}
    
    for item in node.body:
        if isinstance(item, ast.FunctionDef):
            methods[item.name] = {
                "args": extract_arg_info(item.args),
                "docstring": get_docstring(item)
            }
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    # This is a simplification, actual class variables might be more complex
                    class_vars[target.id] = None
    
    return {
        "methods": methods,
        "class_vars": list(class_vars.keys()),
        "bases": [base.id if isinstance(base, ast.Name) else None for base in node.bases],
        "docstring": get_docstring(node)
    }

def extract_function_info(node: ast.FunctionDef) -> Dict[str, Any]:
    """Extract information from a function definition"""
    return {
        "args": extract_arg_info(node.args),
        "docstring": get_docstring(node),
        "returns": None  # We could extract return annotation if needed
    }

def extract_imports(node: ast.Module) -> List[str]:
    """Extract import statements from a module"""
    imports = []
    for item in node.body:
        if isinstance(item, ast.Import):
            for name in item.names:
                imports.append(f"import {name.name}")
        elif isinstance(item, ast.ImportFrom):
            module = item.module or ""
            for name in item.names:
                imports.append(f"from {module} import {name.name}")
    return imports

def analyze_file(file_path: str) -> Dict[str, Any]:
    """Analyze a Python file and extract its structure"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return {"error": "Syntax error in file"}
    
    functions = {}
    classes = {}
    imports = extract_imports(tree)
    module_docstring = get_docstring(tree)
    
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef):
            functions[node.name] = extract_function_info(node)
        elif isinstance(node, ast.ClassDef):
            classes[node.name] = extract_class_info(node)
    
    return {
        "docstring": module_docstring,
        "imports": imports,
        "functions": functions,
        "classes": classes
    }

def scan_directory(directory: str, exclude_dirs: Set[str]) -> Dict[str, Any]:
    """Recursively scan a directory for Python files"""
    result = {}
    
    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
        
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, directory)
                result[rel_path] = analyze_file(file_path)
    
    return result

def extract_model_structure(model_code: Dict[str, Any]) -> Dict[str, Any]:
    """Extract essential model structure information"""
    model_info = {}
    
    for file_path, file_data in model_code.items():
        if "classes" in file_data:
            for class_name, class_info in file_data["classes"].items():
                # Only include database models with primary keys or relationships
                is_model = (
                    "sqlmodel" in str(file_data.get("imports", [])) or 
                    "BaseModel" in str(class_info.get("bases", [])) or
                    "table=True" in str(file_data)
                )
                
                if is_model:
                    # Extract field types and constraints from the file content
                    attributes = []
                    relationships = []
                    
                    # Extract attributes from class body and annotations
                    for var in class_info.get("class_vars", []):
                        attributes.append(var)
                    
                    # Look for relationships in the file content
                    file_content = str(file_data)
                    if "Relationship" in file_content or "relationship" in file_content:
                        # Extract potential relationship fields
                        for var in class_info.get("class_vars", []):
                            if "List[" in file_content and var in file_content:
                                relationships.append(var)
                            elif "Relationship" in file_content and var in file_content:
                                relationships.append(var)
                    
                    model_info[f"{file_path}:{class_name}"] = {
                        "docstring": class_info.get("docstring"),
                        "attributes": attributes,
                        "methods": list(class_info.get("methods", {}).keys()),
                        "relationships": relationships
                    }
    
    return model_info

def extract_db_utils(utils_code: Dict[str, Any]) -> Dict[str, Any]:
    """Extract database utility functions"""
    db_utils = {}
    
    for file_path, file_data in utils_code.items():
        # Look specifically for database-related files
        if "database" in file_path.lower():
            # Extract functions from this file
            for func_name, func_info in file_data.get("functions", {}).items():
                db_utils[f"{file_path}:{func_name}"] = {
                    "signature": f"{func_name}({', '.join(func_info.get('args', []))})",
                    "docstring": func_info.get("docstring", "")[:100] + "..." if func_info.get("docstring") else None
                }
    
    return db_utils

def create_snapshot() -> Dict[str, Any]:
    """Create a snapshot of the entire project"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Directories to exclude from scanning
    exclude_dirs = {
        "venv", "env", "__pycache__", "node_modules", 
        ".git", ".pytest_cache", "attached_assets"
    }
    
    # Scan each main directory separately for better organization
    etl_code = scan_directory(os.path.join(project_root, "app", "etl"), exclude_dirs)
    model_code = scan_directory(os.path.join(project_root, "app", "models"), exclude_dirs)
    ui_code = scan_directory(os.path.join(project_root, "app", "ui"), exclude_dirs)
    utils_code = scan_directory(os.path.join(project_root, "app", "utils"), exclude_dirs)
    migrations_code = scan_directory(os.path.join(project_root, "migrations"), exclude_dirs)
    visualization_code = scan_directory(os.path.join(project_root, "app", "visualization"), exclude_dirs)
    
    # Extract the most important functions and classes for a concise overview
    important_etl_functions = {}
    for file_path, file_data in etl_code.items():
        for func_name, func_info in file_data.get("functions", {}).items():
            important_etl_functions[f"{file_path}:{func_name}"] = {
                "signature": f"{func_name}({', '.join(func_info.get('args', []))})",
                "docstring": func_info.get("docstring", "")[:100] + "..." if func_info.get("docstring") else None
            }
    
    # Create a simplified model structure
    model_structure = extract_model_structure(model_code)
    
    # Extract database utility functions
    db_utils = extract_db_utils(utils_code)
    
    # Extract migration functions
    migration_functions = {}
    for file_path, file_data in migrations_code.items():
        for func_name, func_info in file_data.get("functions", {}).items():
            migration_functions[f"{file_path}:{func_name}"] = {
                "signature": f"{func_name}({', '.join(func_info.get('args', []))})",
                "docstring": func_info.get("docstring", "")[:100] + "..." if func_info.get("docstring") else None
            }
    
    # Create a concise snapshot with the most important information
    snapshot = {
        "models": model_structure,
        "etl_functions": important_etl_functions,
        "db_utils": db_utils,
        "migration_functions": migration_functions,
        "ui_components": list(ui_code.keys()),
        "utils": list(utils_code.keys()),
        "visualization": list(visualization_code.keys())
    }
    
    return snapshot

if __name__ == "__main__":
    snapshot = create_snapshot()
    
    # Save snapshot to file
    with open("project_snapshot.json", "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)
    
    print(f"Project snapshot created: project_snapshot.json")
    print(f"Total ETL functions cataloged: {len(snapshot.get('etl_functions', {}))}")
    print(f"Total models cataloged: {len(snapshot.get('models', {}))}")
    print(f"Total database utility functions: {len(snapshot.get('db_utils', {}))}")
    print(f"Total migration functions: {len(snapshot.get('migration_functions', {}))}")
    print(f"Total UI components: {len(snapshot.get('ui_components', []))}")
