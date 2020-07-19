# Just messing around with stride stuff. Figuring out what strides mean and if they do anything
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


def get_stride_data(stride_header_12_file):
    pkg_db.start_db_connection('2_9_0_1')
    entries_refid = {x: y for x, y in pkg_db.get_entries_from_table('city_tower_d2_0369', 'FileName, RefID')}
    entries_filetype = {x: y for x, y in pkg_db.get_entries_from_table('city_tower_d2_0369', 'FileName, FileType')}
    ref_file_name = f'0369-0000' + entries_refid[stride_header_12_file][2:]
    if entries_filetype[ref_file_name] == "Stride Header":  # Stride Header I think is the actual data
        header_hex = get_hex_data(test_dir + '/' + stride_header_12_file + '.bin')
        stride_header = get_header(header_hex, Stride12Header())
        print(stride_header)

        stride_hex = get_hex_data(test_dir + '/' + ref_file_name + '.bin')

        hex_data_split = [stride_hex[i:i + stride_header.StrideLength*2] for i in range(0, len(stride_hex), stride_header.StrideLength*2)]
        floats = []
        for hex_data in hex_data_split:
            for i in range(3):
                selection = hex_data[(8*i):8*(i+1)]
                print(selection)
                float_value = struct.unpack('f', bytes.fromhex(selection))[0]
                floats.append(str(float_value))
        coords = [floats[i:i + 3] for i in range(0, len(floats), 3)]
        coords = [x for x in coords if len(x) == 3]
        print(len(coords))
        print(coords)
        # processed = [f'{int(get_flipped_hex(faces_data[i:i+4], 4), 16)+1}//{int(get_flipped_hex(faces_data[i+4:i+8], 4), 16)+1}' for i in range(0, len(faces_data), 8)]
    else:
        print(entries_filetype[ref_file_name])


def float_from_unsigned16(n):
    assert 0 <= n < 2**16
    sign = n >> 15
    exp = (n >> 10) & 0b011111
    fraction = n & (2**10 - 1)
    if exp == 0:
        if fraction == 0:
            return -0.0 if sign else 0.0
        else:
            return (-1)**sign * fraction / 2**10 * 2**(-14)  # subnormal
    elif exp == 0b11111:
        if fraction == 0:
            return float('-inf') if sign else float('inf')
        else:
            return float('nan')
    print('f', exp, fraction, (-1)**sign * (1 + fraction / 2**10) * 2**(exp - 15))
    return (-1)**sign * (1 + fraction / 2**10) * 2**(exp - 15)


def half_float_stride8(hex_data_split):
    """
    A half float is defined in OpenGL in this case as a 16 bit float with a sign bitdepth of 1, mantissa bitdepth 10,
    exponent bitdepth 5.
    Bias is calculated as 2^(exp bitdepth) - 1 = 31
    Mantissa division is by 2^(mantissa bitdepth) = 1024
    """
    exp_bitdepth = 5
    mantissa_bitdepth = 10
    bias = 2**(exp_bitdepth - 1) - 1
    mantissa_division = 2**(mantissa_bitdepth)
    coords = []
    for hex_data in hex_data_split:
        coord = []
        scale_hex = get_flipped_hex(hex_data[-4:], 4)
        # scale = np.frombuffer(binascii.unhexlify(get_flipped_hex(scale_hex, 4)), dtype=np.float16)[0]
        scale = int(scale_hex, 16)
        for i in range(3):
            selection = hex_data[4 * i:4 * (i + 1)]
            # print(selection)
            # Swapping 16 bit endianness
            flipped_selection = get_flipped_hex(selection, 4)
            coord.append(np.frombuffer(binascii.unhexlify(flipped_selection), dtype=np.float16)[0]/scale)
        print(coord, f'scale: {scale_hex} {scale}')
        coords.append(coord)
    with open('half_float_12e0_flipped_8.obj', 'w') as f:
        f.write(f'o test\n')
        for coord in coords:
            line = f'v {coord[0]} {coord[1]} {coord[2]}\n'  # Coords
            if 'NaN' not in line and 'INF' not in line:
                f.write(line)
        print('Wrote half float')


def half_float_stride20(hex_data_split):
    """
    A half float is defined in OpenGL in this case as a 16 bit float with a sign bitdepth of 1, mantissa bitdepth 10,
    exponent bitdepth 5.
    Bias is calculated as 2^(exp bitdepth) - 1 = 31
    Mantissa division is by 2^(mantissa bitdepth) = 1024
    """
    coords = []
    for hex_data in hex_data_split:
        print(hex_data)
        coord = []
        scale_hex = get_flipped_hex(hex_data[-4:], 4)
        # scale = np.frombuffer(binascii.unhexlify(get_flipped_hex(scale_hex, 4)), dtype=np.float16)[0]
        scale = int(scale_hex, 16)
        for i in range(3):
            selection = hex_data[4 * i:4 * (i + 1)]
            flipped_selection = get_flipped_hex(selection, 4)
            coord.append(np.frombuffer(binascii.unhexlify(flipped_selection), dtype=np.float16)[0]/scale)
        print(coord, f'scale: {scale_hex} {scale}')
        coords.append(coord)
    with open('half_float_12e0_flipped_20.obj', 'w') as f:
        f.write(f'o test\n')
        for coord in coords:
            line = f'v {coord[0]} {coord[1]} {coord[2]}\n'  # Coords
            if 'NaN' not in line and 'INF' not in line:
                f.write(line)
        print('Wrote half float')


def bfloat16(hex_data_split):
    """
    A bfloat16 is defined as being a signed float with exponent 8 bitdepth and mantissa 7 bitdepth.
    Bias is calculated as 2^(exp bitdepth - 1) - 1 = 127
    Mantissa division is by 2^(mantissa bitdepth) = 127
    """
    exp_bitdepth = 8
    mantissa_bitdepth = 7
    bias = 2**(exp_bitdepth - 1) - 1
    mantissa_division = 2**(mantissa_bitdepth)
    coords = []
    for hex_data in hex_data_split:
        coord = []
        for i in range(3):
            selection = hex_data[4 * i:4 * (i + 1)]
            # print(selection)
            # Swapping 16 bit endianness
            flipped_selection = get_flipped_hex(selection, 4)
            int_fs = int(flipped_selection, 16)
            mantissa = int_fs & 0x3F
            mantissa_abs = mantissa / mantissa_division
            exponent = (int_fs >> 0x7) & 0xFF
            negative = (int_fs >> 0xF) & 0x01
            print(mantissa, exponent, negative)
            if exponent == 0:
                flt = mantissa_abs * 2 ** (bias - 1)
            elif 0 < exponent < 2 ** exp_bitdepth - 1:
                # TODO check if should be abs mantissa or just mantissa
                flt = (1 + mantissa) * 2 ** (exponent - bias)
            elif exponent == 2 ** exp_bitdepth - 1:
                if mantissa == 0:
                    flt = 'INF'
                else:
                    flt = 'NaN'
            if negative == 1 and isinstance(flt, float):
                flt = -flt
            coord.append(flt)
        print(coord)
        coords.append(coord)
    with open('bfloat16_12e0.obj', 'w') as f:
        f.write(f'o test\n')
        for coord in coords:
            line = f'v {coord[0]} {coord[1]} {coord[2]}\n'  # Coords
            if 'NaN' not in line and 'INF' not in line:
                f.write(line)
        print('Wrote bfloat16')


def float_tests(pkg_name, stride_header_12_file):
    pkg_db.start_db_connection('2_9_0_1')
    entries_refid = {x: y for x, y in pkg_db.get_entries_from_table(pkg_name, 'FileName, RefID')}
    entries_filetype = {x: y for x, y in pkg_db.get_entries_from_table(pkg_name, 'FileName, FileType')}
    ref_file_name = f'{pkg_name.split("_")[-1].upper()}-0000' + entries_refid[stride_header_12_file][2:]
    if entries_filetype[ref_file_name] == "Stride Header":  # Stride Header I think is the actual data
        header_hex = get_hex_data(test_dir + '/' + pkg_name + '/' + stride_header_12_file + '.bin')
        stride_header = get_header(header_hex, Stride12Header())
        print(stride_header)

        stride_hex = get_hex_data(test_dir + '/' + pkg_name + '/' + ref_file_name + '.bin')

        hex_data_split = [stride_hex[i:i + stride_header.StrideLength*2] for i in range(0, len(stride_hex), stride_header.StrideLength*2)]
        if stride_header.StrideLength == 8:
            half_float_stride8(hex_data_split)
        elif stride_header.StrideLength == 20:
            half_float_stride20(hex_data_split)
        # bfloat16(hex_data_split)


# remember to only check 12 byte stride files not the data itself
# get_stride_data('0369-000014B9')
# get_stride_data('0369-00000C87')
# half_float_test('city_tower_d2_0369', '0369-00001088')
float_tests('globals_01fe', '01FE-000012E0')
float_tests('globals_01fe', '01FE-000012E1')

a = struct.pack("H", int('9983', 16))
print(np.frombuffer(a, dtype =np.float16)[0])