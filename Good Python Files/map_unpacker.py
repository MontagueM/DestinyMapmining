from dataclasses import dataclass, fields
import numpy as np
import struct
import model_unpacker
import scipy.spatial
import copy


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


def unpack_map(main_file):
    scale_hex, transform_hex, model_refs_hex, copy_count_hex = get_hex_from_pkg(main_file)

    rotations, scales = get_transform_data(transform_hex, scale_hex)
    model_refs = get_model_refs(model_refs_hex)
    copy_counts = get_copy_counts(copy_count_hex)
    transforms_array = get_transforms_array(model_refs, copy_counts, rotations, scales)
    obj_strings = get_model_obj_strings(transforms_array)
    write_obj_strings(obj_strings)


def get_hex_from_pkg(file):
    pkgs_dir = 'D:/D2_Datamining/Package Unpacker/2_9_0_1/output_all'

    main_pkg = model_unpacker.get_pkg_name(file)
    main_hex = get_hex_data(f'{pkgs_dir}/{main_pkg}/{file}.bin')
    scales_file = get_scales_file(main_hex)
    scales_pkg = model_unpacker.get_pkg_name(scales_file)
    scale_hex = get_hex_data(f'{pkgs_dir}/{scales_pkg}/{scales_file}.bin')[48 * 2:]

    transform_count = int(get_flipped_hex(main_hex[64*2:64*2+4], 4), 16)
    transform_offset = 192
    transform_length = transform_count*48
    transform_hex = main_hex[transform_offset*2:transform_offset*2 + transform_length*2]

    entry_count = int(get_flipped_hex(main_hex[88*2:88*2+4], 4), 16)
    model_offset = transform_offset + transform_length + 32
    model_length = entry_count * 4
    model_refs_hex = main_hex[model_offset*2:model_offset*2 + model_length*2]

    copy_offset = model_offset + model_length + int(main_hex[model_offset*2+model_length*2:].find('90718080')/2) + 8
    copy_count_hex = main_hex[copy_offset*2:]

    return scale_hex, transform_hex, model_refs_hex, copy_count_hex


def get_scales_file(main_hex):
    file_hash = main_hex[24*2:24*2+8]
    file_name = model_unpacker.get_file_from_hash(get_flipped_hex(file_hash, 8))
    return file_name


def get_transform_data(transform_hex, scale_hex):
    rotation_entries_hex = [transform_hex[i:i + 48 * 2] for i in range(0, len(transform_hex), 48 * 2)]

    rotations = []
    for e in rotation_entries_hex:
        h = e[:16 * 2]
        hex_floats = [h[i:i + 8] for i in range(0, len(h), 8)]
        floats = []
        for hex_float in hex_floats:
            float_value = struct.unpack('f', bytes.fromhex(hex_float))[0]
            floats.append(round(float_value, 3))
        rotations.append(floats)

    # Scale
    scale_entries_hex = [scale_hex[i:i + 48 * 2] for i in range(0, len(scale_hex), 48 * 2)]

    min_scale_coords = []
    max_scale_coords = []
    for e in scale_entries_hex:
        hexes = [e[:12 * 2], e[16 * 2:28 * 2]]
        for k, h in enumerate(hexes):
            hex_floats = [h[i:i + 8] for i in range(0, len(h), 8)]
            floats = []
            for hex_float in hex_floats:
                float_value = struct.unpack('f', bytes.fromhex(hex_float))[0]
                floats.append(float_value)
            if len(floats) == 3:
                coord = [floats[i:i + 3] for i in range(0, len(floats), 3)][0]
            else:
                coord = floats[0]
            if k == 0:
                min_scale_coords.append(coord)
            elif k == 1:
                max_scale_coords.append(coord)

    scale_coords = [[min_scale_coords[i], max_scale_coords[i]] for i in range(len(min_scale_coords))]
    return rotations, scale_coords


def get_model_refs(model_refs_hex):
    entries_hex = [model_refs_hex[i:i + 4 * 2] for i in range(0, len(model_refs_hex), 4 * 2)]
    return entries_hex


def get_copy_counts(copy_count_hex):
    entries_hex = [copy_count_hex[i:i + 8 * 2] for i in range(0, len(copy_count_hex), 8 * 2)]
    entries = []
    for e in entries_hex:
        entries.append(get_header(e, CountEntry()))
    return [e.Field0 for e in entries]


def get_transforms_array(model_refs, copy_counts, rotations, scales):
    transforms_array = []
    last_index = 0
    for i, model in enumerate(model_refs):
        copies = copy_counts[i]
        transforms = []
        for copy_id in range(copies):
            transforms.append([rotations[last_index + copy_id], scales[last_index + copy_id]])
        last_index += copies
        transform_array = [model, transforms]
        transforms_array.append(transform_array)
    return transforms_array


def get_model_obj_strings(transforms_array):
    obj_strings = []
    max_vert_used = 0
    nums = 0
    manual_scale_modifications = {
        # '2E24ED80': [0.536, 0.457, 0.391],
    }
    for i, transform_array in enumerate(transforms_array):
        if i > 440:
            return obj_strings
        elif i < 435:
            continue
        model_file = model_unpacker.get_file_from_hash(get_flipped_hex(transform_array[0], 8))
        model_data_file = model_unpacker.get_model_data_file(model_file)
        submeshes_verts, submeshes_faces = model_unpacker.get_verts_faces_data(model_data_file)
        if not submeshes_verts or not submeshes_faces:
            print('Skipping current model')
            continue
        print(f'Getting obj {i + 1}/{len(transforms_array)} {transform_array[0]} {nums}')
        if transform_array[0] in manual_scale_modifications.keys():
            manual_scale_mod = manual_scale_modifications[transform_array[0]]
        else:
            manual_scale_mod = [1, 1, 1]

        for copy_id, transform in enumerate(transform_array[1]):
            nums += 1
            for index_2 in submeshes_verts.keys():
                index_2_verts = []
                [[index_2_verts.append(y) for y in x] for x in submeshes_verts[index_2]]
                r_verts_data = rotate_verts(index_2_verts, transform[0])
                loc_verts = set_vert_locations(r_verts_data, transform[1], manual_scale_mod)

                offset = 0
                for index_3 in range(len(submeshes_verts[index_2])):
                    new_verts = loc_verts[offset:offset + len(submeshes_verts[index_2][index_3])]
                    offset += len(new_verts)
                    adjusted_faces_data, max_vert_used = model_unpacker.adjust_faces_data(submeshes_faces[index_2][index_3],
                                                                                          max_vert_used)
                    obj_str = model_unpacker.get_obj_str(adjusted_faces_data, new_verts)
                    obj_str = f'o {transform_array[0]}_{copy_id}_{index_2}_{index_3}\n' + obj_str
                    obj_strings.append(obj_str)
    return obj_strings


def set_vert_locations(verts, scale_info, manual_scale_mod):
    coords1 = scale_info[0]
    coords2 = scale_info[1]
    x = [x[0] for x in verts]
    y = [x[1] for x in verts]
    z = [x[2] for x in verts]
    output = [[], [], []]
    loop = [x, y, z]
    for i, t in enumerate(loop):
        t_max = max(t)
        t_min = min(t)
        c_min = coords1[i]
        c_max = coords2[i]
        t_range = t_max - t_min
        for point in t:
            if t_range == 0:
                interp = c_min
            else:
                c_range = c_max - c_min
                interp = (((point - t_min) / t_range) * c_range + c_min) * manual_scale_mod[i]
            output[i].append(interp)
    return [[-output[0][i], output[2][i], output[1][i]] for i in range(len(x))]


def rotate_verts(verts_data, rotation_transform):
    r = scipy.spatial.transform.Rotation.from_quat(rotation_transform)
    quat_rots = scipy.spatial.transform.Rotation.apply(r, [[x[0], x[1], x[2]] for x in verts_data], inverse=False)
    return quat_rots.tolist()


def write_obj_strings(obj_strings):
    with open('unpacked_objects/city_tower_d2_0369_new.obj', 'w') as f:
        for string in obj_strings:
            f.write(string)
    print('Written to file.')


if __name__ == '__main__':
    unpack_map('0369-00000B77')
