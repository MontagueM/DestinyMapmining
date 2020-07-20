import struct
import pkg_db
from dataclasses import dataclass, fields
import numpy as np
import binascii
import os


@dataclass
class Stride12Header:
    EntrySize: np.uint32 = np.uint32(0)
    StrideLength: np.uint32 = np.uint32(0)
    DeadBeef: np.uint32 = np.uint32(0)


def fill_hex_with_zeros(s, desired_length):
    return ("0"*desired_length + s)[-desired_length:]


def get_hex_data(direc):
    t = open(direc, 'rb')
    h = t.read().hex().upper()
    return h


def get_flipped_hex(h, length):
    if length % 2 != 0:
        print("Flipped hex length is not even.")
        return None
    return "".join(reversed([h[:length][i:i + 2] for i in range(0, length, 2)]))


def get_file_from_hash(hsh):
    first_int = int(hsh.upper(), 16)
    one = first_int - 2155872256
    first_hex = hex(int(np.floor(one/8192)))
    second_hex = hex(first_int % 8192)
    return f'{fill_hex_with_zeros(first_hex[2:], 4)}-{fill_hex_with_zeros(second_hex[2:], 8)}'.upper()


def get_hash_from_file(file):
    pkg = file.replace(".bin", "").upper()

    firsthex_int = int(pkg[:4], 16)
    secondhex_int = int(pkg[5:], 16)

    one = firsthex_int*8192
    two = hex(one + secondhex_int + 2155872256)
    return two[2:]

#
#
# test_dir = 'D:/D2_Datamining/Package Unpacker/2_9_0_1/output_all/'
#
#
def get_header(file_hex, header):
    # The header data is 0x16F bytes long, so we need to x2 as python reads each nibble not each byte

    for f in fields(header):
        if f.type == np.uint32:
            flipped = "".join(get_flipped_hex(file_hex, 8))
            value = np.uint32(int(flipped, 16))
            setattr(header, f.name, value)
            file_hex = file_hex[8:]
    return header
#
#
# pkg_name = 'globals_0238'
# stride_header_12_file = '0238-000017B2'
# hex_data_split = []
#
# pkg_db.start_db_connection('2_9_0_1')
# entries_refid = {x: y for x, y in pkg_db.get_entries_from_table(pkg_name, 'FileName, RefID')}
# entries_filetype = {x: y for x, y in pkg_db.get_entries_from_table(pkg_name, 'FileName, FileType')}
# ref_file_name = f'{pkg_name.split("_")[-1].upper()}-0000' + entries_refid[stride_header_12_file][2:]
# if entries_filetype[ref_file_name] == "Stride Header":  # Stride Header I think is the actual data
#     header_hex = get_hex_data(test_dir + '/' + pkg_name + '/' + stride_header_12_file + '.bin')
#     stride_header = get_header(header_hex, Stride12Header())
#     print(stride_header)
#
#     stride_hex = get_hex_data(test_dir + '/' + pkg_name + '/' + ref_file_name + '.bin')
#
#     hex_data_split = [stride_hex[i:i + stride_header.StrideLength * 2] for i in
#                       range(0, len(stride_hex), stride_header.StrideLength * 2)]
# else:
#     quit()
#
# coords = []
# for hex_data in hex_data_split:
#     coord = []
#     for j in range(3):
#         selection = get_flipped_hex(hex_data[j*4:j*4+4], 4)
#         exp_bitdepth = 0
#         mantissa_bitdepth = 15
#         bias = 2 ** (exp_bitdepth - 1) - 1
#         mantissa_division = 2 ** mantissa_bitdepth
#         int_fs = int(selection, 16)
#         mantissa = int_fs & 2**mantissa_bitdepth - 1
#         mantissa_abs = mantissa / mantissa_division
#         exponent = (int_fs >> mantissa_bitdepth) & 2**exp_bitdepth - 1
#         negative = int_fs >> 15
#         print(mantissa, negative)
#         if exponent == 0:
#             flt = mantissa_abs * 2 ** (bias - 1)
#         else:
#             print('Error!!')
#             quit()
#         if negative:
#             flt += -0.35
#         coord.append(flt)
#     print(coord)
#     coords.append(coord)
# with open(f'unpacked_objects/{ref_file_name}.obj', 'w') as f:
#     f.write(f'o testing_a117c780\n')
#     for k, coord in enumerate(coords):
#         line = f'v {coord[0]} {coord[1]} {coord[2]}\n'  # Coords
#         print(f'{k+1}/{len(coords)}: v {round(coord[0], 3)} {round(coord[1], 3)} {round(coord[2], 3)}\n')
#         f.write(line)

test_dir = 'D:/D2_Datamining/Package Unpacker/2_9_0_1/output_all'


def get_pkg_name(file):
    pkg_id = file.split('-')[0]
    for folder in os.listdir(test_dir):
        if pkg_id.lower() in folder.lower():
            pkg_name = folder
            break
    else:
        print('Could not find folder.')
        return
    return pkg_name


def get_referenced_file(file):
    pkg_name = get_pkg_name(file)

    entries_refid = {x: y for x, y in pkg_db.get_entries_from_table(pkg_name, 'FileName, RefID')}
    entries_filetype = {x: y for x, y in pkg_db.get_entries_from_table(pkg_name, 'FileName, FileType')}

    ref_file_name = f'{pkg_name.split("_")[-1].upper()}-0000' + entries_refid[file][2:]
    return ref_file_name, entries_filetype[ref_file_name]


def get_model(model_file):
    """
    Given a model file:
    - open the model file and identify the model data file
    - open the model data file
    - identify the faces and 8verts files
    - get all faces data
    - get all 8verts data
    - slim down faces data to fit the number of verts as otherwise it will crash
    - combine the faces and vert data into the obj
    - write obj
    """
    pkg_db.start_db_connection('2_9_0_1')
    model_data_file = get_model_data_file(model_file)
    print(model_data_file)
    faces_file, verts_file = get_faces_verts_files(model_data_file)
    print(faces_file, verts_file)
    faces_data = get_faces_data(faces_file)
    print(f'Num faces: {len(faces_data)}')
    # print(faces_data)
    verts_data = get_verts_data(verts_file)
    print(f'Num faces: {len(verts_data)}')
    # print(verts_data)
    faces_data = trim_faces_data(faces_data, len(verts_data))
    print(f'Num trimmed faces: {len(faces_data)}')
    # print(faces_data)
    obj_str = get_obj_str(faces_data, verts_data)
    write_obj(obj_str, model_file)


def get_model_data_file(model_file):
    pkg_name = get_pkg_name(model_file)
    model_hex = get_hex_data(f'{test_dir}/{pkg_name}/{model_file}.bin')
    model_data_hash = get_flipped_hex(model_hex[16:24], 8)
    return get_file_from_hash(model_data_hash)


def get_faces_verts_files(model_data_file):
    pkg_name = get_pkg_name(model_data_file)
    model_data_hex = get_hex_data(f'{test_dir}/{pkg_name}/{model_data_file}.bin')
    faces_hash = get_flipped_hex(model_data_hex[-32:-24], 8)
    verts_hash = get_flipped_hex(model_data_hex[-24:-16], 8)
    return get_file_from_hash(faces_hash), get_file_from_hash(verts_hash)


def get_faces_data(faces_file):
    pkg_name = get_pkg_name(faces_file)
    ref_file, ref_file_type = get_referenced_file(faces_file)
    faces = []
    if ref_file_type == "Faces Header":
        faces_hex = get_hex_data(f'{test_dir}/{pkg_name}/{ref_file}.bin')
        int_faces_data = [int(get_flipped_hex(faces_hex[i:i+4], 4), 16)+1 for i in range(0, len(faces_hex), 4)]
        for i in range(0, len(int_faces_data), 3):
            face = []
            for j in range(3):
                face.append(int_faces_data[i+j])
            faces.append(face)
        return faces
    else:
        print('Incorrect type of file.')
        return


def get_verts_data(verts_file):
    pkg_name = get_pkg_name(verts_file)
    ref_file, ref_file_type = get_referenced_file(verts_file)
    if ref_file_type == "Stride Header":
        header_hex = get_hex_data(f'{test_dir}/{pkg_name}/{verts_file}.bin')
        stride_header = get_header(header_hex, Stride12Header())

        stride_hex = get_hex_data(f'{test_dir}/{pkg_name}/{ref_file}.bin')

        hex_data_split = [stride_hex[i:i + stride_header.StrideLength * 2] for i in
                          range(0, len(stride_hex), stride_header.StrideLength * 2)]
    else:
        print('Incorrect type of file.')
        return

    coords = []
    for hex_data in hex_data_split:
        coord = []
        for j in range(3):
            selection = get_flipped_hex(hex_data[j * 4:j * 4 + 4], 4)
            exp_bitdepth = 0
            mantissa_bitdepth = 15
            bias = 2 ** (exp_bitdepth - 1) - 1
            mantissa_division = 2 ** mantissa_bitdepth
            int_fs = int(selection, 16)
            mantissa = int_fs & 2 ** mantissa_bitdepth - 1
            mantissa_abs = mantissa / mantissa_division
            exponent = (int_fs >> mantissa_bitdepth) & 2 ** exp_bitdepth - 1
            negative = int_fs >> 15
            if exponent == 0:
                flt = mantissa_abs * 2 ** (bias - 1)
            else:
                print('Incorrect file given.')
                return
            if negative:
                flt += -0.35
            coord.append(flt)
        coords.append(coord)
    return coords


# A terrible method that should be replaced by a deterministic system
def trim_faces_data(faces_data, num_verts):
    reset = True
    for i, face in enumerate(faces_data):
        if face[0] == 1 and reset:
            start = i
            reset = False
        for v in face:
            # If we're travelling along a set of faces that isn't for this obj
            if v > num_verts:
                reset = True
            if num_verts in face:
                if i == len(faces_data)-1:
                    end = i+1
                elif 1 in faces_data[i+1]:
                    end = i
    return faces_data[start:end]


def get_obj_str(faces_data, verts_data):
    verts_str = ''
    for coord in verts_data:
        verts_str += f'v {coord[0]} {coord[1]} {coord[2]}\n'
    faces_str = ''
    for face in faces_data:
        faces_str += f'f {face[0]}// {face[1]}// {face[2]}//\n'
    return verts_str + faces_str


def write_obj(obj_str, file_name):
    model_hash = get_hash_from_file(file_name)
    with open(f'unpacked_objects/{model_hash}.obj', 'w') as f:
        f.write(f'o {model_hash}\n')
        for line in obj_str:
            f.write(line)


get_model('0369-00000200')
