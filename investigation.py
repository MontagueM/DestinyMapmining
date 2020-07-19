import os
import pkg_db
import struct
from dataclasses import dataclass, fields, field
from typing import List
import numpy as np
import binascii


@dataclass
class Stride12Header:
    EntrySize: np.uint32 = np.uint32(0)
    StrideLength: np.uint32 = np.uint32(0)
    DeadBeef: np.uint32 = np.uint32(0)


@dataclass
class Unk16Header:
    EntrySize: np.uint32 = np.uint32(0)
    Field4: np.uint32 = np.uint32(0)
    Field8: np.uint32 = np.uint32(0)
    FieldC: np.uint32 = np.uint32(0)


@dataclass
class Faces24Header:
    Field0: np.uint32 = np.uint32(0)
    Field4: np.uint32 = np.uint32(0)
    EntrySize: np.uint32 = np.uint32(0)
    FieldC: np.uint32 = np.uint32(0)
    DeadBeef: np.uint32 = np.uint32(0)
    Field14: np.uint32 = np.uint32(0)


def get_hex_data(direc):
    t = open(direc, 'rb')
    h = t.read().hex().upper()
    return h


def get_flipped_hex(h, length):
    """
    Flips the hex around so the data is read correctly eg 00 80 00 00 = 00 00 80 00. Takes every pair of bytes and
    flips them so AC 18 = 18 AC.
    :param h: the hex string to flip around
    :param length: how long this hex string is (len(h) doesn't work)
    :return: the flipped hex
    """
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


faces_array = []
faces_data_array = []


def get_faces_data(pkg_name, faces_header_24_file):
    pkg_db.start_db_connection('2_9_0_1')
    entries_refid = {x: y for x, y in pkg_db.get_entries_from_table(pkg_name, 'FileName, RefID')}
    entries_filetype = {x: y for x, y in pkg_db.get_entries_from_table(pkg_name, 'FileName, FileType')}

    ref_file_name = f'{pkg_name.split("_")[-1].upper()}-0000' + entries_refid[faces_header_24_file][2:]
    if entries_filetype[ref_file_name] == "Faces Header":  # Faces Header I think is the actual data
        faces_hex = get_hex_data(test_dir + '/' + pkg_name + '/' + ref_file_name + '.bin')
        int_faces_data = [int(get_flipped_hex(faces_hex[i:i+4], 4), 16)+1 for i in range(0, len(faces_hex), 4)]

        # int_faces_data.sort(key=lambda x: x[1])
        for i in range(0, len(int_faces_data), 3):
            faces_data = 'f'
            for j in range(3):
                faces_data += f' {int_faces_data[i+j]}//'
            faces_data_array.append(faces_data)
        print(faces_data_array)
        print(f'Number of faces: {len(faces_data_array)}')
        return faces_data_array


def get_stride_data(pkg_name, stride_header_12_file):
    pkg_db.start_db_connection('2_9_0_1')
    entries_refid = {x: y for x, y in pkg_db.get_entries_from_table(pkg_name, 'FileName, RefID')}
    entries_filetype = {x: y for x, y in pkg_db.get_entries_from_table(pkg_name, 'FileName, FileType')}
    ref_file_name = f'{pkg_name.split("_")[-1].upper()}-0000' + entries_refid[stride_header_12_file][2:]
    if entries_filetype[ref_file_name] == "Stride Header":  # Stride Header I think is the actual data
        header_hex = get_hex_data(test_dir + '/' + pkg_name + '/' + stride_header_12_file + '.bin')
        stride_header = get_header(header_hex, Stride12Header())
        print(stride_header)
        print(f'Number of vertices: {stride_header.EntrySize/stride_header.StrideLength}')
        # return
        stride_hex = get_hex_data(test_dir + '/' + pkg_name + '/' + ref_file_name + '.bin')
        hex_data_split = [stride_hex[i:i + stride_header.StrideLength*2] for i in range(0, len(stride_hex), stride_header.StrideLength*2)]
        coords = []
        for hex_data in hex_data_split:
            coord = []
            for i in range(3):
                selection = hex_data[4 * i:4 * (i + 1)]
                # print(selection)
                # Swapping 16 bit endianness
                flipped_selection = get_flipped_hex(selection, 4)
                int_fs = int(selection, 16)
                # coord.append(float_from_unsigned16(int_fs))
                coord.append(np.frombuffer(binascii.unhexlify(flipped_selection), dtype=np.float16)[0])
            # print(coord)
            coords.append(coord)
        return coords
        # processed = [f'{int(get_flipped_hex(faces_data[i:i+4], 4), 16)+1}//{int(get_flipped_hex(faces_data[i+4:i+8], 4), 16)+1}' for i in range(0, len(faces_data), 8)]
    else:
        print(entries_filetype[ref_file_name])


def get_all_faces_data():
    pkg_db.start_db_connection('2_9_0_1')
    entries_filetype = {x: y for x, y in pkg_db.get_entries_from_table('city_tower_d2_0369', 'FileName, FileType')}
    for file_name, file_type in entries_filetype.items():
        # print(entries_refid[faces_header_name])
        if file_type == "Faces Header":  # Faces Header I think is the actual data
            get_faces_data(file_name)


def get_all_stride_data():
    pkg_db.start_db_connection('2_9_0_1')
    entries_filetype = {x: y for x, y in pkg_db.get_entries_from_table('city_tower_d2_0369', 'FileName, FileType')}
    for file_name, file_type in entries_filetype.items():
        # print(entries_refid[faces_header_name])
        if file_type == "Faces Header":  # Faces Header I think is the actual data
            get_faces_data(file_name)


# faces_header_name = '0369-00000017'
# stride_header_name = '0369-0000001A'
#
#
# for file in os.listdir(test_dir)[:100]:
#     faces_header_name = file.split('.bin')[0]
#     get_faces_data(faces_header_name)
# print(faces_array)
# print(sorted(faces_array))
# get_stride_data()

# get_all_faces_data()
# print(faces_array)
# print(sorted(faces_array))

# get_stride_data('0369-0000001A')
# get_stride_data('0369-00000E05')
# get_stride_data('0369-00001088')
# get_stride_data('0369-000014B9')
# get_stride_data('0369-00000C87')
# get_stride_data('0369-00001C49')
# get_stride_data('0369-00000BED')
faces_12da_array = get_faces_data('globals_01fe', '01FE-000012DA')
with open('faces_12da.txt', 'w') as f:
    for row in faces_12da_array:
        f.write(row + '\n')
get_stride_data('globals_01fe', '01FE-000012E0')
get_stride_data('globals_01fe', '01FE-000012E1')
print('\n')
print('\n')
faces_734_array = get_faces_data('city_tower_d2_0369', '0369-00000734')
with open('faces_734.txt', 'w') as f:
    for row in faces_734_array:
        f.write(row + '\n')
get_stride_data('city_tower_d2_0369', '0369-000008AF')
get_stride_data('city_tower_d2_0369', '0369-00000A1E')
print('\n')
print('\n')
get_faces_data('city_tower_d2_0369', '0369-00000383')
get_stride_data('city_tower_d2_0369', '0369-00000388')

get_stride_data('city_tower_d2_0369', '0369-0000038A')
print('\n')
faces_38c_array = get_faces_data('city_tower_d2_0369', '0369-0000038C')
with open('faces_38c.txt', 'w') as f:
    for row in faces_38c_array:
        f.write(row + '\n')
stride_390_array = get_stride_data('city_tower_d2_0369', '0369-00000390')
with open('verts_390.txt', 'w') as f:
    for coord in stride_390_array:
        line = f'v {coord[0]} {coord[1]} {coord[2]}\n'
        f.write(line)
get_stride_data('city_tower_d2_0369', '0369-00000391')
print('\n')
get_faces_data('city_tower_d2_0369', '0369-00000394')
get_stride_data('city_tower_d2_0369', '0369-00000397')
get_stride_data('city_tower_d2_0369', '0369-0000039D')
