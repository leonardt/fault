def get_renamed_port(circuit, name):
    if hasattr(circuit, "renamed_ports"):
        for key, value in circuit.renamed_ports.items():
            if value == name:
                return key
    return name
