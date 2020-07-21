from dataclasses import dataclass, fields
import numpy as np
import binascii
import struct
import model_unpacker


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
    !Split into coords/rots, model refs, copy counts hex
    !Get arrays of coords and rots for every copy
    !Get model reference array
    !Get array of copy counts
    !Combine copy counts and model references into a dictionary
    Loop through each model reference
        Loop through each copy count
            Make a dict of {model_ref: [coords0, rots0], [coords1, rots1], [coords2, rots2], ...} called model transform data where the transforms are for each copy
    For each model transform data
        Pull the model verts and faces ONCE
        For each copy (len of the transforms)
            Adjust the verts positions by the amount in the model coords by addition?
            Adjust the verts positions for rotation
                Multiply vector of positions by 3d rotation matrix for yaw, pitch roll (see onenote for reference)
            Add the object naming and referencing (eg o 0022ED80_x) for each one and the copy number for now
    Write the single .obj and view it!!
    """
    # Need to add scale
    transform_hex = hex_data[192 * 2:216912 * 2]
    coords, rotations = get_transform_data(transform_hex)
    model_refs_hex = hex_data[216944*2:219076*2]
    model_refs = get_model_refs(model_refs_hex)
    copy_count_hex = hex_data[219104*2:]
    copy_counts = get_copy_counts(copy_count_hex)
    transforms_array = get_transforms_array(model_refs, copy_counts, coords, rotations)
    obj_strs = get_model_obj_strings(transforms_array)


def get_transform_data(transform_hex):
    entries_hex = [transform_hex[i:i + 48 * 2] for i in range(0, len(transform_hex), 48 * 2)]
    model_entries = []
    for entry_hex in entries_hex:
        entry_header = ModelEntry()
        model_entries.append(get_header(entry_hex, entry_header))

    coords = []
    rotations = []
    for e in entries_hex:
        hexes = [e[:12 * 2], e[16 * 2:28 * 2]]
        for k, h in enumerate(hexes):
            hex_floats = [h[i:i + 8] for i in range(0, len(h), 8)]
            floats = []
            for hex_float in hex_floats:
                float_value = struct.unpack('f', bytes.fromhex(hex_float))[0]
                floats.append(round(float_value, 3))
            coord = [floats[i:i + 3] for i in range(0, len(floats), 3)][0]
            if k == 0:
                rotations.append(coord)
            else:
                coords.append(coord)
    return coords, rotations


def get_model_refs(model_refs_hex):
    entries_hex = [model_refs_hex[i:i + 4 * 2] for i in range(0, len(model_refs_hex), 4 * 2)]
    return entries_hex


def get_copy_counts(copy_count_hex):
    entries_hex = [copy_count_hex[i:i + 8 * 2] for i in range(0, len(copy_count_hex), 8 * 2)]
    entries = []
    for e in entries_hex:
        entries.append(get_header(e, CountEntry()))
    return [e.Field0 for e in entries]


def get_transforms_array(model_refs, copy_counts, coords, rotations):
    transforms_array = []
    model_dict = dict(zip(model_refs, copy_counts))
    last_index = 0
    for model, copies in model_dict:
        transforms = []
        for copy_id in range(copies):
            transforms.append([coords[last_index + copy_id], rotations[last_index + copy_id]])
        last_index = copies
        transform_array = [model, transforms]
        transforms_array.append(transform_array)
    return transforms_array


def get_model_obj_strings(transforms_array):
    for transform_array in transforms_array:
        verts_data, faces_data = model_unpacker.get_verts_faces_data(transform_array[0])
        

unpack_map()
