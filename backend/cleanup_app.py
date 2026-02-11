with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the index of the first app.run
first_run_idx = -1
for i, line in enumerate(lines):
    if 'app.run(debug=False, port=5000, use_reloader=False)' in line:
        first_run_idx = i
        break

if first_run_idx != -1:
    # Keep lines up to and including the first app.run
    new_lines = lines[:first_run_idx+1]
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"Truncated app.py at line {first_run_idx+1}")
else:
    print("Could not find app.run line")
