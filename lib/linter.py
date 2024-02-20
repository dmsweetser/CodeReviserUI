import pyjsparser
import ast
import io
import sys
import subprocess
import tempfile
import os

class Linter:
    def __init__(self, code, language):
        self.code = code
        self.language = language

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
                self.contents = ""

            def write(self, message):
                if message.strip():
                    self.contents += message

        old_stdout = sys.stdout
        lint_output = LintOutput()
        sys.stdout = lint_output
        try:
            ast.parse(self.code)
        except SyntaxError as e:
            print(str(e))
        sys.stdout = old_stdout
        if lint_output.contents.strip():
            return lint_output.contents.strip()
        else:
            return "No linting issues found."

    def _lint_javascript(self):
        try:
            pyjsparser.parse(self.code)
            return "No linting issues found."
        except Exception as e:
            return str(e)

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
                    proj_file.write("    <OutputType>Exe</OutputType>\n")
                    proj_file.write("    <TargetFramework>net6.0</TargetFramework>\n")
                    proj_file.write("  </PropertyGroup>\n")
                    proj_file.write("</Project>\n")

                # Execute dotnet build within the temporary directory
                compiler_output = subprocess.check_output(["dotnet", "build", temp_project_file], cwd=temp_dir, stderr=subprocess.STDOUT, text=True)

                # Return compiler output (may include errors)
                return compiler_output.strip()
        except subprocess.CalledProcessError as e:
            # Return compiler error message
            return e.output.strip()
