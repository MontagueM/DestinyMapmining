import numpy as np

def fill_hex_with_zeros(s, desired_length):
    return ("0"*desired_length + s)[-desired_length:]


def hash_pkg(hsh):
    print(hsh)
    first_int = int(hsh, 16)
    one = first_int - 2155872256
    first_hex = hex(int(np.floor(one/8192)))
    second_hex = hex(first_int % 8192)
    print(first_hex, second_hex)
    return f'{fill_hex_with_zeros(first_hex[2:], 4)}-{fill_hex_with_zeros(second_hex[2:], 8)}'.upper()


file_name = hash_pkg('80ED2383')
print(file_name)
