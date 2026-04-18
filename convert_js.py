
import re

def convert_template_literals(content):
    # This is a basic converter for `${var}` in backticks
    # It doesn't handle nested backticks or complex expressions well,
    # but for this project it should be enough.
    
    def replace_backtick(match):
        s = match.group(1)
        # Replace ${...} with ' + ... + '
        # We need to be careful with quotes inside the expression
        s = re.sub(r'\$\{(.*?)\}', r"' + (\1) + '", s)
        # Convert the backtick string to a single-quoted string
        # and clean up empty strings like '' + 
        res = f"'{s}'"
        res = res.replace("'' + ", "").replace(" + ''", "")
        return res

    # Match anything between backticks that doesn't contain a literal backtick
    return re.sub(r'`([^`\\]*(?:\\.[^`\\]*)*)`', replace_backtick, content, flags=re.DOTALL)

with open('static/js/app.js', 'r') as f:
    js = f.read()

new_js = convert_template_literals(js)

with open('static/js/app.js', 'w') as f:
    f.write(new_js)

print("Converted template literals to regular strings.")
