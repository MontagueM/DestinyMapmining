from dataclasses import dataclass, fields
import numpy as np
import binascii
import struct
import model_unpacker
import scipy.spatial


test_dir = 'D:/D2_Datamining/Package Unpacker/2_9_0_1/output_all/city_tower_d2_0369/'


@dataclass
class ModelEntry:
    Field0: np.uint32 = np.uint32(0)
    Field4: np.uint32 = np.uint32(0)
    Field8: np.uint32 = np.uint32(0)
    FieldC: np.uint32 = np.uint32(0)
    Field10: np.uint32 = np.uint32(0)
    Field14: np.uint32 = np.uint32(0)
    Field18: np.uint32 = np.uint32(0)
    Field1C: np.uint32 = np.uint32(0)
    Field20: np.uint32 = np.uint32(0)
    Field24: np.uint32 = np.uint32(0)
    Field28: np.uint32 = np.uint32(0)


@dataclass
class CountEntry:
    Field0: np.uint16 = np.uint32(0)
    Field2: np.uint32 = np.uint32(0)
    Field6: np.uint16 = np.uint32(0)


def get_hex_data(direc):
    t = open(direc, 'rb')
    h = t.read().hex().upper()
    return h


def get_flipped_hex(h, length):
    if length % 2 != 0:
        print("Flipped hex length is not even.")
        return None
    return "".join(reversed([h[:length][i:i + 2] for i in range(0, length, 2)]))


def get_header(file_hex, header):
    # The header data is 0x16F bytes long, so we need to x2 as python reads each nibble not each byte

    for f in fields(header):
        if f.type == np.uint32:
            flipped = "".join(get_flipped_hex(file_hex, 8))
            value = np.uint32(int(flipped, 16))
            setattr(header, f.name, value)
            file_hex = file_hex[8:]
        elif f.type == np.uint16:
            flipped = "".join(get_flipped_hex(file_hex, 4))
            value = np.uint16(int(flipped, 16))
            setattr(header, f.name, value)
            file_hex = file_hex[4:]
    return header


a_166d_file = '0369-00000B77'
hex_data = get_hex_data(test_dir + a_166d_file + '.bin')


def unpack_map():
    """
    Need to add scale?
    In order to put all .obj into a single file I need to change the numbers to account for the number of vertices already in file.
    eg 1// 2// 3// needs to change to 1+number of verts before this// 2+number of verts before this// etc etc
    """
    # Need to add scale
    transform_hex = hex_data[192 * 2:216912 * 2]
    coords, rotations, scales = get_transform_data(transform_hex)
    model_refs_hex = hex_data[216944*2:219076*2]
    model_refs = get_model_refs(model_refs_hex)
    copy_count_hex = hex_data[219104*2:]
    copy_counts = get_copy_counts(copy_count_hex)
    transforms_array = get_transforms_array(model_refs, copy_counts, coords, rotations, scales)
    obj_strings = get_model_obj_strings(transforms_array)
    write_obj_strings(obj_strings)


def get_transform_data(transform_hex):
    entries_hex = [transform_hex[i:i + 48 * 2] for i in range(0, len(transform_hex), 48 * 2)]
    model_entries = []
    for entry_hex in entries_hex:
        entry_header = ModelEntry()
        model_entries.append(get_header(entry_hex, entry_header))

    coords = []
    rotations = []
    for e in entries_hex:
        hexes = [e[:16 * 2], e[16 * 2:28 * 2]]
        for k, h in enumerate(hexes):
            hex_floats = [h[i:i + 8] for i in range(0, len(h), 8)]
            floats = []
            for hex_float in hex_floats:
                float_value = struct.unpack('f', bytes.fromhex(hex_float))[0]
                floats.append(round(float_value, 3))
            if k == 0:
                rotations.append(floats)
            else:
                coords.append(floats)

    # Scale
    hex_data_3a7 = get_hex_data(test_dir + '0369-000003A7.bin')[48 * 2:]
    entries_hex = [hex_data_3a7[i:i + 48 * 2] for i in range(0, len(hex_data_3a7), 48 * 2)]

    coords1 = []
    coords2 = []
    for e in entries_hex:
        hexes = [e[:12 * 2], e[16 * 2:28 * 2]]
        for k, h in enumerate(hexes):
            hex_floats = [h[i:i + 8] for i in range(0, len(h), 8)]
            floats = []
            for hex_float in hex_floats:
                # We don't need to worry about flipping hex as this unpack is:
                # 1. Little Endian 2. DCBA (so reverses the direction)
                float_value = struct.unpack('f', bytes.fromhex(hex_float))[0]
                floats.append(float_value)
            # Formatting for x,y,z
            if len(floats) == 3:
                coord = [floats[i:i + 3] for i in range(0, len(floats), 3)][0]
            else:
                coord = floats[0]
            # print(coord)
            if k == 0:
                coords1.append(coord)
            elif k == 1:
                coords2.append(coord)

    # Getting modifier number from b77
    hex_data_b77 = hex_data[192*2:216912*2]
    entries_hex = [hex_data_b77[i:i + 48 * 2] for i in range(0, len(hex_data_b77), 48 * 2)]
    modifiers = []
    for e in entries_hex:
        hex = e[28 * 2:32 * 2]
        hex_floats = [hex[i:i + 8] for i in range(0, len(hex), 8)]
        floats = []
        for hex_float in hex_floats:
            float_value = struct.unpack('f', bytes.fromhex(hex_float))[0]
            floats.append(float_value)
        modifier = floats
        modifiers.append(modifier)
    ###
    sub = np.array(coords2) - np.array(coords1)
    scale_factors = [[round(x, 4) for x in sub[i] / np.array(modifiers[i])] for i in range(len(sub))]

    return coords, rotations, scale_factors


def get_model_refs(model_refs_hex):
    entries_hex = [model_refs_hex[i:i + 4 * 2] for i in range(0, len(model_refs_hex), 4 * 2)]
    return entries_hex


def get_copy_counts(copy_count_hex):
    entries_hex = [copy_count_hex[i:i + 8 * 2] for i in range(0, len(copy_count_hex), 8 * 2)]
    entries = []
    for e in entries_hex:
        entries.append(get_header(e, CountEntry()))
    return [e.Field0 for e in entries]


def get_transforms_array(model_refs, copy_counts, coords, rotations, scales):
    # print(coords[-1])
    transforms_array = []
    last_index = 0
    for i, model in enumerate(model_refs):
        copies = copy_counts[i]
        transforms = []
        # print(last_index, len(coords))
        # print(copies)
        for copy_id in range(copies):
            transforms.append([coords[last_index + copy_id], rotations[last_index + copy_id], scales[last_index + copy_id]])
        last_index += copies
        transform_array = [model, transforms]
        transforms_array.append(transform_array)
    # print(last_index, len(coords))
    return transforms_array


def get_model_obj_strings(transforms_array):
    obj_strings = []
    max_vert_used = 0
    for i, transform_array in enumerate(transforms_array):
        # if i > 100:
        #     return obj_strings
        print(f'Getting obj {i+1}/{len(transforms_array)} {transform_array[0]}')
        verts_data, faces_data = model_unpacker.get_verts_faces_data(transform_array[0])
        if not verts_data or not faces_data:
            print('Skipping current model')
            continue
        for copy_id, transform in enumerate(transform_array[1]):
            # print(f'{transform_array[0]}_{copy_id}')
            s_verts_data = scale_verts(verts_data, transform[2])
            # Just testing
            # r_verts_data = rotate_verts(verts_data, [1, 0, 0, 1])
            sm_verts_data = move_verts(s_verts_data, transform[0])
            smr_verts_data = rotate_verts(sm_verts_data, transform[1])
            adjusted_faces_data, max_vert_used = adjust_faces_data(faces_data, max_vert_used)
            obj_str = model_unpacker.get_obj_str(adjusted_faces_data, smr_verts_data)
            obj_str = f'o {transform_array[0]}_{copy_id}\n' + obj_str
            obj_strings.append(obj_str)
    return obj_strings


def adjust_faces_data(faces_data, max_vert_used):
    new_faces_data = []
    all_v = []
    for face in faces_data:
        new_face = []
        for v in face:
            new_face.append(v + max_vert_used)
            all_v.append(v + max_vert_used)
        new_faces_data.append(new_face)
    return new_faces_data, max(all_v)


def rotate_verts(verts_data, rotation_transform):
    w = rotation_transform[0]
    x = rotation_transform[1]
    y = rotation_transform[2]
    z = rotation_transform[3]
    r = scipy.spatial.transform.Rotation.from_quat([x, y, z, w])
    quat_rots = scipy.spatial.transform.Rotation.apply(r, verts_data, inverse=False)
    return quat_rots


def move_verts(verts_data, move_transform):
    moved_verts = []
    for coord in verts_data:
        moved_vert = np.array(coord) + np.array(move_transform)
        moved_verts.append([round(x, 6) for x in moved_vert.tolist()])
    return moved_verts


def scale_verts(verts_data, scale_transform):
    return np.multiply(scale_transform, verts_data)


def write_obj_strings(obj_strings):
    with open('unpacked_objects/city_tower_d2_0369.obj', 'w') as f:
        for string in obj_strings:
            f.write(string)
    print('Written to file.')


if __name__ == '__main__':
    unpack_map()
