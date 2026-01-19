import ast
import re
from pathlib import Path
from typing import Dict, List, Optional
import hashlib


class CodeChunker:
    """Break code into logical chunks (functions, classes, methods)."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def chunk_file(self, file_path: str, language: str) -> List[Dict]:
        """Chunk a file based on its language."""
        full_path = self.project_path / file_path

        if not full_path.exists():
            return []

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return []

        # Route to appropriate chunker
        if language == 'python':
            return self._chunk_python(file_path, content)
        elif language in ['javascript', 'typescript']:
            return self._chunk_javascript(file_path, content)
        else:
            return self._chunk_generic(file_path, content)

    def _chunk_python(self, file_path: str, content: str) -> List[Dict]:
        """Chunk Python code using AST."""
        chunks = []

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                # Extract functions
                if isinstance(node, ast.FunctionDef):
                    chunk = self._extract_python_function(node, file_path, content)
                    if chunk:
                        chunks.append(chunk)

                # Extract classes
                elif isinstance(node, ast.ClassDef):
                    chunk = self._extract_python_class(node, file_path, content)
                    if chunk:
                        chunks.append(chunk)

                    # Extract methods within class
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_chunk = self._extract_python_method(
                                item, node.name, file_path, content
                            )
                            if method_chunk:
                                chunks.append(method_chunk)

        except SyntaxError:
            # If AST parsing fails, fall back to generic chunking
            return self._chunk_generic(file_path, content)

        return chunks

    def _extract_python_function(self, node: ast.FunctionDef, file_path: str,
                                 content: str) -> Optional[Dict]:
        """Extract Python function details."""
        # Get source code
        try:
            start_line = node.lineno
            end_line = node.end_lineno or start_line
            code_lines = content.split('\n')[start_line - 1:end_line]
            code = '\n'.join(code_lines)
        except:
            return None

        # Extract parameters
        params = []
        for arg in node.args.args:
            param_info = {"name": arg.arg}
            if arg.annotation:
                try:
                    param_info["type"] = ast.unparse(arg.annotation)
                except:
                    param_info["type"] = "Any"
            params.append(param_info)

        # Extract return type
        return_type = "None"
        if node.returns:
            try:
                return_type = ast.unparse(node.returns)
            except:
                pass

        # Extract docstring
        docstring = ast.get_docstring(node) or ""

        # Generate signature
        param_strs = [p["name"] for p in params]
        signature = f"def {node.name}({', '.join(param_strs)})"

        # Extract function calls
        calls = self._extract_function_calls(node)

        # Generate chunk ID
        chunk_id = self._generate_chunk_id(file_path, node.name, start_line)

        return {
            "id": chunk_id,
            "file_path": file_path,
            "chunk_type": "function",
            "name": node.name,
            "signature": signature,
            "start_line": start_line,
            "end_line": end_line,
            "code": code,
            "docstring": docstring,
            "parameters": params,
            "return_type": return_type,
            "calls_functions": calls,
            "complexity": self._calculate_ast_complexity(node),
            "token_count": len(code.split()),
            "keywords": self._extract_keywords(code, docstring)
        }

    def _extract_python_class(self, node: ast.ClassDef, file_path: str,
                              content: str) -> Optional[Dict]:
        """Extract Python class details."""
        try:
            start_line = node.lineno
            end_line = node.end_lineno or start_line
            code_lines = content.split('\n')[start_line - 1:end_line]
            code = '\n'.join(code_lines)
        except:
            return None

        # Extract base classes
        bases = []
        for base in node.bases:
            try:
                bases.append(ast.unparse(base))
            except:
                pass

        # Extract docstring
        docstring = ast.get_docstring(node) or ""

        # Count methods
        methods = [item.name for item in node.body if isinstance(item, ast.FunctionDef)]

        # Generate chunk ID
        chunk_id = self._generate_chunk_id(file_path, node.name, start_line)

        return {
            "id": chunk_id,
            "file_path": file_path,
            "chunk_type": "class",
            "name": node.name,
            "signature": f"class {node.name}",
            "start_line": start_line,
            "end_line": end_line,
            "code": code,
            "docstring": docstring,
            "base_classes": bases,
            "methods": methods,
            "complexity": self._calculate_ast_complexity(node),
            "token_count": len(code.split()),
            "keywords": self._extract_keywords(code, docstring)
        }

    def _extract_python_method(self, node: ast.FunctionDef, class_name: str,
                               file_path: str, content: str) -> Optional[Dict]:
        """Extract Python method details."""
        chunk = self._extract_python_function(node, file_path, content)
        if chunk:
            chunk["chunk_type"] = "method"
            chunk["parent_class"] = class_name
            chunk["id"] = self._generate_chunk_id(
                file_path, f"{class_name}.{node.name}", node.lineno
            )
        return chunk

    def _extract_function_calls(self, node: ast.AST) -> List[str]:
        """Extract function calls from AST node."""
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)
        return list(set(calls))

    def _calculate_ast_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity from AST."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Decision points
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try,
                                  ast.ExceptHandler, ast.With)):
                complexity += 1
            # Boolean operators
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _chunk_javascript(self, file_path: str, content: str) -> List[Dict]:
        """Chunk JavaScript/TypeScript code using regex patterns."""
        chunks = []

        # Function pattern
        func_pattern = re.compile(
            r'(async\s+)?function\s+(\w+)\s*{{{{\((.*?)\)}}}}\s*{',
            re.MULTILINE
        )

        # Arrow function pattern
        arrow_pattern = re.compile(
            r'(const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?{{{{\((.*?)\)}}}}\s*=>\s*{',
            re.MULTILINE
        )

        # Class pattern
        class_pattern = re.compile(
            r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*{',
            re.MULTILINE
        )

        lines = content.split('\n')

        # Extract functions
        for match in func_pattern.finditer(content):
            chunk = self._extract_js_function(match, lines, file_path, content)
            if chunk:
                chunks.append(chunk)

        # Extract arrow functions
        for match in arrow_pattern.finditer(content):
            chunk = self._extract_js_arrow_function(match, lines, file_path, content)
            if chunk:
                chunks.append(chunk)

        # Extract classes
        for match in class_pattern.finditer(content):
            chunk = self._extract_js_class(match, lines, file_path, content)
            if chunk:
                chunks.append(chunk)

        return chunks

    def _extract_js_function(self, match: re.Match, lines: List[str],
                             file_path: str, content: str) -> Optional[Dict]:
        """Extract JavaScript function."""
        is_async = match.group(1) is not None
        name = match.group(2)
        params = match.group(3)

        start_pos = match.start()
        start_line = content[:start_pos].count('\n') + 1

        # Find end of function (simple brace matching)
        end_line = self._find_closing_brace(lines, start_line - 1)

        code = '\n'.join(lines[start_line - 1:end_line + 1])

        # Extract JSDoc if present
        docstring = self._extract_jsdoc(lines, start_line - 1)

        chunk_id = self._generate_chunk_id(file_path, name, start_line)

        return {
            "id": chunk_id,
            "file_path": file_path,
            "chunk_type": "function",
            "name": name,
            "signature": f"function {name}({params})",
            "start_line": start_line,
            "end_line": end_line,
            "code": code,
            "docstring": docstring,
            "is_async": is_async,
            "complexity": self._calculate_simple_complexity(code),
            "token_count": len(code.split()),
            "keywords": self._extract_keywords(code, docstring)
        }

    def _extract_js_arrow_function(self, match: re.Match, lines: List[str],
                                   file_path: str, content: str) -> Optional[Dict]:
        """Extract JavaScript arrow function."""
        name = match.group(2)
        params = match.group(3)

        start_pos = match.start()
        start_line = content[:start_pos].count('\n') + 1

        end_line = self._find_closing_brace(lines, start_line - 1)
        code = '\n'.join(lines[start_line - 1:end_line + 1])

        docstring = self._extract_jsdoc(lines, start_line - 1)
        chunk_id = self._generate_chunk_id(file_path, name, start_line)

        return {
            "id": chunk_id,
            "file_path": file_path,
            "chunk_type": "function",
            "name": name,
            "signature": f"const {name} = ({params}) =>",
            "start_line": start_line,
            "end_line": end_line,
            "code": code,
            "docstring": docstring,
            "complexity": self._calculate_simple_complexity(code),
            "token_count": len(code.split()),
            "keywords": self._extract_keywords(code, docstring)
        }

    def _extract_js_class(self, match: re.Match, lines: List[str],
                          file_path: str, content: str) -> Optional[Dict]:
        """Extract JavaScript class."""
        name = match.group(1)
        extends = match.group(2)

        start_pos = match.start()
        start_line = content[:start_pos].count('\n') + 1

        end_line = self._find_closing_brace(lines, start_line - 1)
        code = '\n'.join(lines[start_line - 1:end_line + 1])

        docstring = self._extract_jsdoc(lines, start_line - 1)
        chunk_id = self._generate_chunk_id(file_path, name, start_line)

        return {
            "id": chunk_id,
            "file_path": file_path,
            "chunk_type": "class",
            "name": name,
            "signature": f"class {name}",
            "start_line": start_line,
            "end_line": end_line,
            "code": code,
            "docstring": docstring,
            "extends": extends,
            "complexity": self._calculate_simple_complexity(code),
            "token_count": len(code.split()),
            "keywords": self._extract_keywords(code, docstring)
        }

    def _find_closing_brace(self, lines: List[str], start_line: int) -> int:
        """Find closing brace using simple counting."""
        brace_count = 0
        started = False

        for i in range(start_line, len(lines)):
            line = lines[i]
            for char in line:
                if char == '{':
                    brace_count += 1
                    started = True
                elif char == '}':
                    brace_count -= 1
                    if started and brace_count == 0:
                        return i

        return min(start_line + 50, len(lines) - 1)  # Fallback

    def _extract_jsdoc(self, lines: List[str], line_num: int) -> str:
        """Extract JSDoc comment before function."""
        doc_lines = []
        i = line_num - 1

        while i >= 0:
            line = lines[i].strip()
            if line.startswith('*/'):
                # Found end of JSDoc, collect backwards
                while i >= 0:
                    line = lines[i].strip()
                    doc_lines.insert(0, line)
                    if line.startswith('/**'):
                        break
                    i -= 1
                break
            elif not line or line.startswith('//'):
                i -= 1
            else:
                break

        return '\n'.join(doc_lines)

    def _chunk_generic(self, file_path: str, content: str) -> List[Dict]:
        """Generic chunking for unsupported languages."""
        # Split into logical blocks (separated by blank lines)
        blocks = re.split(r'\n\s*\n', content)
        chunks = []

        current_line = 1
        for block in blocks:
            if len(block.strip()) < 20:  # Skip tiny blocks
                current_line += block.count('\n') + 2
                continue

            lines_in_block = block.count('\n') + 1
            chunk_id = self._generate_chunk_id(file_path, "block", current_line)

            chunks.append({
                "id": chunk_id,
                "file_path": file_path,
                "chunk_type": "block",
                "name": f"block_{current_line}",
                "signature": f"Code block at line {current_line}",
                "start_line": current_line,
                "end_line": current_line + lines_in_block - 1,
                "code": block,
                "complexity": self._calculate_simple_complexity(block),
                "token_count": len(block.split()),
                "keywords": self._extract_keywords(block, "")
            })

            current_line += lines_in_block + 2

        return chunks

    def _calculate_simple_complexity(self, code: str) -> int:
        """Calculate simple complexity for non-Python code."""
        keywords = ['if', 'else', 'for', 'while', 'switch', 'case',
                    'try', 'catch', 'finally', '&&', '||']
        return sum(code.count(kw) for kw in keywords) + 1

    def _extract_keywords(self, code: str, docstring: str) -> List[str]:
        """Extract keywords from code and docstring."""
        # Combine code and docstring
        text = f"{code} {docstring}".lower()

        # Remove special characters
        text = re.sub(r'[^\w\s]', ' ', text)

        # Common programming keywords to include
        keywords = set()
        words = text.split()

        # Filter meaningful words (length > 3, not too common)
        common_words = {'the', 'and', 'for', 'that', 'this', 'with', 'from',
                        'have', 'been', 'are', 'was', 'were', 'will', 'can'}

        for word in words:
            if len(word) > 3 and word not in common_words:
                keywords.add(word)

        return list(keywords)[:20]  # Top 20 keywords

    def _generate_chunk_id(self, file_path: str, name: str, line: int) -> str:
        """Generate unique chunk ID."""
        unique_str = f"{file_path}:{name}:{line}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:16]
