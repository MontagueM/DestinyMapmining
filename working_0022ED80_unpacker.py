import struct
import pkg_db
from dataclasses import dataclass, fields
import numpy as np
import binascii


@dataclass
class Stride12Header:
    EntrySize: np.uint32 = np.uint32(0)
    StrideLength: np.uint32 = np.uint32(0)
    DeadBeef: np.uint32 = np.uint32(0)


def get_hex_data(direc):
    t = open(direc, 'rb')
    h = t.read().hex().upper()
    return h


def get_flipped_hex(h, length):
    if length % 2 != 0:
        print("Flipped hex length is not even.")
        return None
    return "".join(reversed([h[:length][i:i + 2] for i in range(0, length, 2)]))


test_dir = 'D:/D2_Datamining/Package Unpacker/2_9_0_1/output_all/'


def get_header(file_hex, header):
    # The header data is 0x16F bytes long, so we need to x2 as python reads each nibble not each byte

    for f in fields(header):
        if f.type == np.uint32:
            flipped = "".join(get_flipped_hex(file_hex, 8))
            value = np.uint32(int(flipped, 16))
            setattr(header, f.name, value)
            file_hex = file_hex[8:]
    return header


pkg_name = 'globals_01fe'
stride_header_12_file = '01FE-000012E0'
hex_data_split = []

pkg_db.start_db_connection('2_9_0_1')
entries_refid = {x: y for x, y in pkg_db.get_entries_from_table(pkg_name, 'FileName, RefID')}
entries_filetype = {x: y for x, y in pkg_db.get_entries_from_table(pkg_name, 'FileName, FileType')}
ref_file_name = f'{pkg_name.split("_")[-1].upper()}-0000' + entries_refid[stride_header_12_file][2:]
if entries_filetype[ref_file_name] == "Stride Header":  # Stride Header I think is the actual data
    header_hex = get_hex_data(test_dir + '/' + pkg_name + '/' + stride_header_12_file + '.bin')
    stride_header = get_header(header_hex, Stride12Header())
    print(stride_header)

    stride_hex = get_hex_data(test_dir + '/' + pkg_name + '/' + ref_file_name + '.bin')

    hex_data_split = [stride_hex[i:i + stride_header.StrideLength * 2] for i in
                      range(0, len(stride_hex), stride_header.StrideLength * 2)]
else:
    quit()

coords = []
for hex_data in hex_data_split:
    coord = []
    for j in range(3):
        selection = get_flipped_hex(hex_data[j*4:j*4+4], 4)
        exp_bitdepth = 0
        mantissa_bitdepth = 15
        bias = 2 ** (exp_bitdepth - 1) - 1
        mantissa_division = 2 ** mantissa_bitdepth
        int_fs = int(selection, 16)
        mantissa = int_fs & 2**mantissa_bitdepth - 1
        mantissa_abs = mantissa / mantissa_division
        exponent = (int_fs >> mantissa_bitdepth) & 2**exp_bitdepth - 1
        negative = int_fs >> 15
        print(mantissa, negative)
        if exponent == 0:
            flt = mantissa_abs * 2 ** (bias - 1)
        else:
            print('Error!!')
            quit()
        if negative:
            flt += -0.35
        coord.append(flt)
    print(coord)
    coords.append(coord)
with open(f'test_obj/testing_exp0_flipped_limit392.obj', 'w') as f:
    f.write(f'o exp0 negative limiting\n')
    for k, coord in enumerate(coords):
        if k > 391:  # We only want the 392 first vertices to check
            break
        line = f'v {coord[0]} {coord[1]} {coord[2]}\n'  # Coords
        print(f'{k+1}/{len(coords)}: v {round(coord[0], 3)} {round(coord[1], 3)} {round(coord[2], 3)}\n')
        # if np.float('nan') not in line and np.float('inf') not in line:
        f.write(line)
