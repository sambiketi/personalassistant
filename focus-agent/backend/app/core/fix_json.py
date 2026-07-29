import re

# Read the file
with open('agent.py', 'r') as f:
    content = f.read()

# Find the JSON parsing section
if 'json.loads(json_match.group())' in content:
    # Replace with better error handling
    new_content = content.replace(
        'data = json.loads(json_match.group())',
        '''try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    # Try to fix common JSON issues
                    import re
                    fixed_json = json_match.group()
                    # Remove trailing commas
                    fixed_json = re.sub(r',\\s*}', '}', fixed_json)
                    fixed_json = re.sub(r',\\s*]', ']', fixed_json)
                    # Fix unescaped quotes
                    fixed_json = re.sub(r'([^\\\\])"([^"]*)"([^\\\\])', r'\\1\\"\\2\\"\\3', fixed_json)
                    data = json.loads(fixed_json)'''
    )
    
    with open('agent.py', 'w') as f:
        f.write(new_content)
    
    print('✅ JSON parsing updated!')
else:
    print('❌ Could not find json.loads')
