import pyjsparser
import ast
import io
import sys
import subprocess
import tempfile
import os
import re
from lib.config_manager import get_config
from lib.custom_logger import *

logger = CustomLogger(get_config("log_folder",""))

class Linter:
    def __init__(self, code, language):
        self.code = code
        self.language = language
        self.errors = []

    def lint(self):
        if self.language == "python":
            return self._lint_python()
        elif self.language == "javascript":
            return self._lint_javascript()
        elif self.language == "csharp":
            return self._lint_csharp()
        else:
            return "Unsupported language"

    def _lint_python(self):
        class LintOutput(io.StringIO):
            def __init__(self):
                super().__init__()

        old_stdout = sys.stdout
        lint_output = LintOutput()
        sys.stdout = lint_output
        try:
            ast.parse(self.code)
        except SyntaxError as e:
            self.errors.append(f"Error at line {e.lineno}, offset {e.offset}: {e.msg}")
        sys.stdout = old_stdout
        logger.log(self.errors)
        return self.errors

    def _lint_javascript(self):
        try:
            ast = pyjsparser.parse(self.code)
            return []
        except Exception as e:
            error_message = str(e)
            file_line_error = error_message.split("\n")[0].split(":")[1:]
            self.errors.append(error_message)
            logger.log(self.errors)
            return self.errors

    def _lint_csharp(self):
        try:
            # Create a temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Define the path to the temporary C# file
                temp_file_path = os.path.join(temp_dir, "temp.cs")
                # Define the path to the temporary project file
                temp_project_file = os.path.join(temp_dir, "temp.csproj")

                # Write code to the temporary file
                with open(temp_file_path, "w") as file:
                    file.write(self.code)

                # Write minimal .csproj file
                with open(temp_project_file, "w") as proj_file:
                    proj_file.write("<Project Sdk=\"Microsoft.NET.Sdk\">\n")
                    proj_file.write("  <PropertyGroup>\n")
                    proj_file.write("  <OutputType>Exe</OutputType>\n")
                    proj_file.write("  <TargetFramework>net6.0</TargetFramework>\n")
                    proj_file.write("  </PropertyGroup>\n")
                    proj_file.write("</Project>\n")

                # Execute dotnet build within the temporary directory
                compiler_output = ""
                try:
                    compiler_output = subprocess.check_output(["dotnet", "build", temp_project_file], cwd=temp_dir, stderr=subprocess.STDOUT, text=True)
                except subprocess.CalledProcessError as e:
                    # If the build fails, the compiler_output will be an instance of subprocess.CalledProcessError
                    # In that case, we'll extract the error message from the error attribute
                    compiler_output = e.output

                if compiler_output:
                    match = re.search(r"(\([0-9]*,[0-9]*\): error CS[0-9]+\s*:.*?)\s*\[.*?\]", compiler_output)
                    if match:
                        error_message = match.group(1)    
                    else:
                        error_message = compiler_output
                    self.errors.append(error_message)
                logger.log(self.errors)
                return self.errors
        except Exception as e:
            error_message = str(e)
            self.errors.append(("", error_message))
            logger.log(self.errors)
            return self.errors