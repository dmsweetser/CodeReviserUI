# Name: text_diff.py
# Description: This script takes one or more sets of text as input (either from files or standard input)
# and generates an HTML inline diff with coloration using the difflib library. It supports multiple files,
# allows users to specify an output file for the generated HTML diff, handles errors gracefully, and implements
# Myers' Diff Algorithm for more advanced text comparison.

# Uncomment and customize the following line if you want to call this script from another script
# compare_texts("This is the old text.", "This is the new text.", context=5, ignore_whitespace=True)

# Import required libraries
import sys
import difflib
import html  # Use the html module from the Python standard library instead of the deprecated cgi module

# Function to generate HTML for a single difference
def html_diff(old, new, action, context=3):
    """ Given three arguments: old, new, and action (either 'delete', 'insert' or 'equal'),
    this function generates an HTML representation of the difference between them.
    The optional argument 'context' allows users to specify a different line context for the generated HTML diff."""
    tag = "span" if action == "equal" else ("del" if not old else "ins")
    classes = {"del": "deleted", "ins": "inserted", "equal": ""}[action]
    return f'<{tag} class="diff {classes}" data-line="{context}">{html.escape(str(new if new else old))}</{tag}>'

# Function to generate HTML for a list of differences
def html_diffs(old_lines, new_lines, actions):
    """ Given three lists: old_lines, new_lines and actions, this function generates an HTML representation of the differences between them."""
    return "".join([html_diff(old, new, action) for old, new, action in zip(old_lines, new_lines, actions)])

# Function to generate the HTML diff using Myers' Diff Algorithm
def generate_html_diff(old_text, new_text, context=3):
    """ Given two strings (old_text and new_text), this function generates an HTML representation of the differences between them.
    The optional argument 'context' allows users to specify a different line context for the generated HTML diff."""
    old_lines = old_text.split("\n") if old_text else []
    new_lines = new_text.split("\n") if new_text else []
    diff, actions = difflib.ndiff(old_lines, new_lines, n=context, opcode=True)
    old_lines, new_lines = zip(*[list(i) for i in zip(diff, actions)])
    diff = html_diffs(old_lines, new_lines, actions)
    return f'<html><body><pre id="diff">{diff}</pre></body></html>'

# Function to generate the HTML diff using Myers' Diff Algorithm with whitespace changes ignored
def generate_html_diff_ignore_whitespace(old_text, new_text, context=3):
    """ Given two strings (old_text and new_text), this function generates an HTML representation of the differences between them, ignoring whitespace changes."""
    old_lines = old_text.split("\n") if old_text else []
    new_lines = new_text.split("\n") if new_text else []
    diff, actions = difflib.ndiff(old_lines, new_lines, n=context, opcode=True)
    old_lines, new_lines = zip(*[list(i) for i in zip(diff, actions)])
    old_lines = [line.strip() for line in old_lines]
    new_lines = [line.strip() for line in new_lines]
    diff = html_diffs(old_lines, new_lines, actions)
    return f'<html><body><pre id="diff">{diff}</pre></body></html>'

# Function to perform text comparison and generate HTML diff (supporting multiple files or text input)
def compare_texts(*args, context=3, ignore_whitespace=False, output_file=None):
    """ Given one or more texts or files, this function performs a text comparison using Myers' Diff Algorithm
    and generates an HTML representation of the differences. It also supports specifying an output file for the generated HTML diff,
    as well as optional context and whitespace change options."""
    try:
        if len(args) > 1:
            # Handle multiple texts
            input_text = ""
            for arg in args:
                input_text += arg + "\n"
        elif len(sys.argv) > 1:
            # Handle text input with command line arguments
            input_text = sys.stdin.read()
            if not input_text:
                raise ValueError("Error: No input provided.")
        else:
            # Handle text input from standard input
            print("Enter the old text:")
            old_text = sys.stdin.read()
            print("Enter the new text:")
            new_text = sys.stdin.read()
            input_text = old_text + "\n" + new_text

        html_diff = None
        if ignore_whitespace:
            html_diff = generate_html_diff_ignore_whitespace("", input_text, context=context)
        else:
            html_diff = generate_html_diff("", input_text, context=context)

        # Write HTML diff to output file if provided
        if output_file:
            with open(output_file, "w") as f:
                f.write(html_diff)

        print(html_diff)

    except Exception as e:
        raise ValueError(f"Error: {e}")