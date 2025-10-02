def reorder_elements(input_file, output_file=None):
    with open(input_file, 'r') as f:
        lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('*')]

    reordered_elements = []
    for line in lines:
        parts = [int(x.strip()) for x in line.split(',') if x.strip()]
        if len(parts) != 9:
            continue
        ID, n0, n1, n2, n3, n4, n5, n6, n7 = parts
        reordered = [ID, n7, n4, n0, n3, n6, n5, n1, n2]
        reordered_elements.append(reordered)

    if output_file:
        with open(output_file, 'w') as f:
            for elem in reordered_elements:
                f.write(", ".join(map(str, elem)) + "\n")

    return reordered_elements


