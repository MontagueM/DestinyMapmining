from dataclasses import dataclass, fields
import numpy as np
import binascii
import struct


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
    return header


a_166d_file = '0369-00000B77'
hex_data = get_hex_data(test_dir + a_166d_file + '.bin')


def unpack_map():
    """
    Split into coords/rots, model refs, copy counts hex
    Get arrays of coords and rots for every copy
    Get model reference array
    Get array of copy counts
    Combine copy counts and model references into a dictionary
    Loop through each model reference
        Loop through each copy count
            Make a dict of {model_ref: [coords, rots]} called model transform data
    For each model transform data
        Pull the model verts and faces
        Adjust the verts positions by the amount in the model coords by addition?
        Adjust the verts positions for rotation
            Multiply vector of positions by 3d rotation matrix for yaw, pitch roll (see onenote for reference)
        Add the object naming and referencing (eg o 0022ED80_x) for each one and the copy number for now
    Write the single .obj and view it!!
    """
    