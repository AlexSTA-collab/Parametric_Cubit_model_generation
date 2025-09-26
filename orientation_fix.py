input_file = "elements.txt"   # Replace with your file name
output_file = "reordered_elements.txt"  # Optional: set to None if you don't want output file

# Read the lines from the file
with open(input_file, 'r') as f:
    lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('*')]

reordered_elements = []

for line in lines:
    # Split on commas and strip whitespace
    parts = [int(x.strip()) for x in line.split(',') if x.strip()]
    if len(parts) != 9:
        continue  # skip malformed lines

    ID, n0, n1, n2, n3, n4, n5, n6, n7 = parts
    reordered = [ID, n7, n4, n0, n3, n6, n5, n1, n2]
    reordered_elements.append(reordered)

# Print to console
for elem in reordered_elements:
    print(", ".join(map(str, elem)))

# Optional: Write to a file
if output_file:
    with open(output_file, 'w') as f:
        for elem in reordered_elements:
            f.write(", ".join(map(str, elem)) + "\n")
