from dataclasses import dataclass, fields
import numpy as np
import binascii
import struct
import model_unpacker
import scipy.spatial


test_dir = 'D:/D2_Datamining/Package Unpacker/2_9_0_1/output_all/city_tower_d2_0369/'


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


def unpack_map(pkg_folder_name):
    main_hex, scale_hex = get_hex_from_pkg(pkg_folder_name)
    transform_hex = main_hex[192 * 2:216912 * 2]
    rotations, scales = get_transform_data(transform_hex, scale_hex)
    model_refs_hex = main_hex[216944*2:219076*2]
    model_refs = get_model_refs(model_refs_hex)
    copy_count_hex = main_hex[219104*2:]
    copy_counts = get_copy_counts(copy_count_hex)
    transforms_array = get_transforms_array(model_refs, copy_counts, rotations, scales)
    obj_strings = get_model_obj_strings(transforms_array)
    write_obj_strings(obj_strings)


def get_hex_from_pkg(folder):
    a_166d_file = '0369-00000B77'
    main_hex = get_hex_data(test_dir + a_166d_file + '.bin')
    scale_hex = get_hex_data(test_dir + '0369-000003A7.bin')[48 * 2:]
    return main_hex, scale_hex


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
            # Formatting for x,y,z
            if len(floats) == 3:
                coord = [floats[i:i + 3] for i in range(0, len(floats), 3)][0]
            else:
                coord = floats[0]
            if k == 0:
                min_scale_coords.append(coord)
            elif k == 1:
                max_scale_coords.append(coord)

    # # Getting modifier number from b77
    # hex_data_b77 = hex_data[192*2:216912*2]
    # entries_hex = [hex_data_b77[i:i + 48 * 2] for i in range(0, len(hex_data_b77), 48 * 2)]
    # modifiers = []
    # for e in entries_hex:
    #     hex = e[28 * 2:32 * 2]
    #     hex_floats = [hex[i:i + 8] for i in range(0, len(hex), 8)]
    #     floats = []
    #     for hex_float in hex_floats:
    #         float_value = struct.unpack('f', bytes.fromhex(hex_float))[0]
    #         floats.append(float_value)
    #     modifier = floats
    #     modifiers.append(modifier)

    # TODO figure out what to do with modifier stuff
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
    for i, transform_array in enumerate(transforms_array):
        # if i > 100:
        #     return obj_strings
        # elif i < 350:
        #     continue
        verts_data, faces_data = model_unpacker.get_verts_faces_data(transform_array[0])
        if not verts_data or not faces_data:
            print('Skipping current model')
            continue
        max_hash_index = len(verts_data)
        print(f'Getting obj {i + 1}/{len(transforms_array)} {transform_array[0]} {max_hash_index-1}')
        for copy_id, transform in enumerate(transform_array[1]):
            for hsh_index in range(max_hash_index):
                sr_verts_data = rotate_verts(verts_data[hsh_index], transform[0], b_local=True)
                test_loc_verts = set_vert_locations(sr_verts_data, transform[1])
                adjusted_faces_data, max_vert_used = adjust_faces_data(faces_data[hsh_index], max_vert_used)
                obj_str = model_unpacker.get_obj_str(adjusted_faces_data, test_loc_verts)
                obj_str = f'o {transform_array[0]}_{copy_id}_{hsh_index}\n' + obj_str
                obj_strings.append(obj_str)
    return obj_strings


def set_vert_locations(verts, scale_info):
    # It could be an option to swap the X values and make positive for coords1 and coords2 in case I think it needs to be swapped
    coords1 = scale_info[0]
    coords2 = scale_info[1]
    # coords1_ = coords1
    # coords1 = [-coords2[0], coords1[1], coords1[2]]
    # coords2 = [-coords1_[0], coords1_[1], coords1_[2]]
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
            c_range = c_max - c_min
            interp = ((point - t_min) / t_range) * c_range + c_min
            # print(interp)
            output[i].append(interp)
    # print()
    return [[-output[0][i], output[2][i], output[1][i]] for i in range(len(x))]


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


def rotate_verts(verts_data, rotation_transform, b_local):
    if b_local:
        # if rotation_transform[3] < 0 or rotation_transform[3] == -0.0:
        #     rotation_transform = [-x for x in rotation_transform]
        # w = rotation_transform[0]
        # x = rotation_transform[1]
        # y = rotation_transform[2]
        # z = rotation_transform[3]

        x = rotation_transform[0]
        y = rotation_transform[1]
        z = rotation_transform[2]
        w = rotation_transform[3]

        # if w < 0 or w == -0.0:
        #     w = -w

        r = scipy.spatial.transform.Rotation.from_quat([x, y, z, w])
        # print(f'Actually rot with {[x, y, z, w]}')
        quat_rots = scipy.spatial.transform.Rotation.apply(r, [[x[0], x[1], x[2]] for x in verts_data], inverse=False)
    else:
        quat_rots = [-verts_data[0], verts_data[2], verts_data[1]]
    return quat_rots


def move_verts(verts_data, move_transform):
    moved_verts = []
    for coord in verts_data:
        moved_vert = np.array(coord) + np.array(move_transform)
        moved_verts.append([round(x, 6) for x in moved_vert.tolist()])
    return moved_verts


def scale_verts(verts_data, scale_transform):
    print(verts_data, scale_transform)
    return np.multiply([scale_transform[0], scale_transform[2], scale_transform[1]], verts_data)


def write_obj_strings(obj_strings):
    with open('unpacked_objects/city_tower_d2_0369.obj', 'w') as f:
        for string in obj_strings:
            f.write(string)
    print('Written to file.')


if __name__ == '__main__':
    unpack_map('')
