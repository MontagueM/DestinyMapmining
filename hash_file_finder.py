import numpy as np


def fill_hex_with_zeros(s, desired_length):
    return ("0"*desired_length + s)[-desired_length:]


def get_flipped_hex(h, length):
    if length % 2 != 0:
        print("Flipped hex length is not even.")
        return None
    return "".join(reversed([h[:length][i:i + 2] for i in range(0, length, 2)]))


def hash_pkg(hsh):
    # print(hsh)
    first_int = int(hsh.upper(), 16)
    one = first_int - 2155872256
    first_hex = hex(int(np.floor(one/8192)))
    second_hex = hex(first_int % 8192)
    # print(first_hex, second_hex)
    return f'{fill_hex_with_zeros(first_hex[2:], 4)}-{fill_hex_with_zeros(second_hex[2:], 8)}'.upper()


hashes = ['6C23ED80',
          'C82CED80',
          '9824ED80',
          '9C24ED80',
          '7BDDBF80',
          '422DED80',
          '6725ED80',
          '6825ED80',
          '6B25ED80',
          'AC54C780',
          '472DED80',
          '8625ED80',
          '8925ED80',
          '8A25ED80',
          '8C25ED80',
          ]

# hashes = ['4124ED80']

for h in hashes:
    file_name = hash_pkg(get_flipped_hex(h, 8))
    print(file_name)
